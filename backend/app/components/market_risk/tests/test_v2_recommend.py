"""Recommendations (FR4 rules, FR5 retrieval + optional LLM summary, FR7 decisions).

Synthetic households only. The LLM is always mocked (no API calls) and decisions go to a
temporary SQLite file. Knowledge tests skip when artifacts_v2/knowledge/ is not installed.
"""

import inspect
import json
import logging
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.components.market_risk.v2 import artifacts, decisions, knowledge, recommend, service, summary
from app.components.market_risk.v2.knowledge import Rule
from app.main import app

BASE = "/api/risk/v2"
client = TestClient(app)
KEY = "SIM-HH-001"
GRANT_GUARDRAIL = "NO second livelihood grant"


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    """No LLM key, no real API, decisions in a temporary SQLite file, fresh caches."""
    monkeypatch.setattr(summary, "api_key", lambda: None)

    def no_network(prompt, key):
        raise AssertionError("the LLM must be mocked in tests")

    monkeypatch.setattr(summary, "call_llm", no_network)
    decisions.set_store(decisions.SQLiteStore(tmp_path / "decisions.sqlite3"))
    summary.clear_cache()
    yield
    decisions.set_store(None)
    summary.clear_cache()


@pytest.fixture
def needs_knowledge():
    if artifacts.missing_files():
        pytest.skip("v2 artifacts are not on this machine (they are git-ignored)")
    try:
        knowledge.load()
    except knowledge.KnowledgeUnavailable:
        pytest.skip("knowledge base is not installed (artifacts_v2/knowledge/ is git-ignored)")


def rule(rule_id="T1", level="B", priority=1, trigger="profit == 0", fields=("profit",), **extra) -> Rule:
    values = dict(rule_id=rule_id, level=level, priority=priority, trigger=trigger, trigger_fields=tuple(fields),
                  reason_label=f"reason {rule_id}", action_category="Test", action_en=f"action {rule_id}",
                  doc_filter=(), citation="", guardrail="", research_basis="", timing_days=None,
                  validated_by="", status="draft")
    return Rule(**{**values, **extra})


def engine(*rules) -> recommend.Engine:
    return recommend.Engine(SimpleNamespace(rules=tuple(rules), retrieve=lambda query, doc_filter: []))


# --- safe evaluator -------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "profit.__class__ == 1",                 # attribute access
    "__import__('os') == 1",                 # call / import
    "len(profit) == 1",                      # call
    'RISK_ORD["High"] == 2',                 # subscript
    "(lambda: 1)() == 1",                    # lambda
    "_secret == 1",                          # private name
    "profit + 1 == 2",                       # arithmetic
    "[profit] == [1]",                       # list
    "profit == 1; x",                        # not an expression
])
def test_safe_evaluator_rejects_unsafe_syntax(text):
    with pytest.raises(recommend.UnsafeExpression):
        recommend.compile_trigger(text)


def test_safe_evaluator_values_and_nulls():
    check = lambda text, **ctx: recommend.evaluate(recommend.compile_trigger(text), ctx)
    assert check('risk_class_t == "Low" and alert_3m == False', risk_class_t="Low", alert_3m=False)
    assert check('level in ("Moderate", "High")', level="High")
    assert not check('level in ("Moderate", "High")', level=None)
    assert check("not (risk_change > 0)", risk_change=None)  # unanswered never satisfies >
    assert not check("risk_change <= 0", risk_change=None)
    assert check("profit == 0 or saved == 0", profit=None, saved=0.0)
    assert not check('x < 1', x="text")                    # type mismatch -> false, not an error
    with pytest.raises(recommend.UnknownField):
        check("missing_field == 1", profit=0)


def test_unknown_field_skips_rule_and_logs(caplog):
    with caplog.at_level(logging.WARNING):
        result = engine(rule("T9", trigger="no_such_field == 1")).matches(rule("T9", trigger="no_such_field == 1"),
                                                                          {"profit": 0})
    assert result is False
    assert "T9" in caplog.text and "no_such_field" in caplog.text


# --- rule selection (synthetic contexts) ----------------------------------------------------

def test_level_a_picks_one_lowest_priority_and_b_orders_by_shap():
    rules = [
        rule("A1", "A", 4, 'risk_class_t == "High"', ["risk_class_t"]),
        rule("A2", "A", 1, 'risk_class_t == "High"', ["risk_class_t"]),
        rule("B1", "B", 1, "profit == 0", ["profit"]),
        rule("B2", "B", 2, "saved_money == 0", ["saved_money"]),
        rule("B3", "B", 3, "problem_sales_low == 1", ["problem_sales_low"]),
        rule("Z1", "B", 9, "no rule matched", [recommend.FALLBACK_FIELD]),
    ]
    context = {"risk_class_t": "High", "profit": 0, "saved_money": 0, "problem_sales_low": 1, "hours_band": 1}
    shap = [
        {"feature": "problem_sales_low", "label": "Sales low", "group": "Household shock", "contribution": 0.04},
        {"feature": "saved_money", "label": "Saved", "group": "Business", "contribution": 0.03},
        {"feature": "profit", "label": "Profit", "group": "Business", "contribution": -0.02},
        {"feature": "hours_band", "label": "Hours", "group": "Business", "contribution": 0.01},
        {"feature": "high_count_6m", "label": "History", "group": "History", "contribution": 0.05},
    ]
    follow_up, actions = engine(*rules).select(context, shap)
    assert follow_up[0].rule_id == "A2"
    assert [r.rule_id for r, _ in actions] == ["B3", "B2", "B1", "Z1"]  # SHAP-linked first, then priority
    assert actions[0][1] == ["Sales low"]
    assert actions[-1][1] == ["Hours"]  # History factors never call for Z1


def test_unassigned_gets_a0_and_no_actions():
    rules = [rule("A0", "A", 0, 'risk_class_t == "Unassigned"', ["risk_class_t"]),
             rule("A3", "A", 2, "alert_3m == True", ["alert_3m"]),
             rule("B1", "B", 1, "profit == 0", ["profit"])]
    follow_up, actions = engine(*rules).select({"risk_class_t": "Unassigned", "alert_3m": True, "profit": 0}, [])
    assert follow_up[0].rule_id == "A0" and actions == []


# --- the real rule table and circulars ------------------------------------------------------

def test_every_stored_visit_gets_exactly_one_follow_up(needs_knowledge):
    bundle, base = artifacts.load_bundle(), knowledge.load()
    rows = bundle.store_features.join(bundle.store_predictions)
    assert rows.household_key.str.startswith("SIM-HH-").all()
    eng = recommend.engine_for(base)
    for _, row in rows.iterrows():
        context = recommend.household_context(row)
        matched = [r for r in base.rules if r.level == "A" and eng.matches(r, context)]
        follow_up, actions = eng.select(context, [])
        assert matched and follow_up is not None
        if context["risk_class_t"] == "Unassigned":
            assert follow_up[0].rule_id == "A0" and actions == []
        else:
            assert follow_up[0].rule_id != "A0"


def test_rule_table_triggers_compile_and_use_known_fields(needs_knowledge):
    base = knowledge.load()
    eng = recommend.engine_for(base)
    row = artifacts.load_bundle().store_features.join(artifacts.load_bundle().store_predictions).iloc[0]
    fields = set(recommend.household_context(row))
    for item in base.rules:
        if item.trigger_fields == (recommend.FALLBACK_FIELD,):
            continue
        assert item.rule_id in eng.compiled, item.rule_id
        assert recommend.field_names(eng.compiled[item.rule_id]) <= fields, item.rule_id


def test_financial_support_rules_carry_the_no_second_grant_guardrail(needs_knowledge):
    financial = [r for r in knowledge.load().rules if r.action_category.lower().startswith("financial support")]
    assert financial
    for item in financial:
        assert GRANT_GUARDRAIL in item.guardrail, item.rule_id


def test_retrieval_stays_inside_doc_filter(needs_knowledge):
    base = knowledge.load()
    for item in base.rules:
        found = base.retrieve(item.query, item.doc_filter)
        assert len(found) == (min(2, sum(d in item.doc_filter for d in base.doc_ids)) if item.doc_filter else 0)
        assert all(source["doc_id"] in item.doc_filter for source in found), item.rule_id
        assert all(len(source["excerpt"]) <= knowledge.EXCERPT_CHARS for source in found)
    for query, _ in knowledge.RETRIEVAL_TEST_SET:
        assert all(s["doc_id"] == "MOF_08_2025_iii" for s in base.retrieve(query, ("MOF_08_2025_iii",)))


def test_query_uses_query_terms_first():
    assert rule("T1", query_terms="සවිබල ණය").query == "සවිබල ණය reason T1 action T1"
    assert rule("T1").query == "reason T1 action T1"  # empty query_terms: old behaviour


@pytest.mark.parametrize("citation, pages", [
    ("Samurdhi Circular 2026/05, p.4 (progress reporting)", {4}),
    ("2026/05, p.3 (business plan) and p.4 (guidance)", {3, 4}),
    ("Circular 2026/03, p.1–2 (training); 2026/02 MoA", {1, 2}),
    ("2026/05, p.2 sec. 03 (market survey); p.11", {2, 11}),
    ("– (system data-quality rule)", set()),
])
def test_page_only_fallback_reads_the_citation_text(citation, pages):
    assert rule(citation=citation).citation_pages == pages


@pytest.mark.parametrize("text, pairs, bad", [
    ("SDD_2026_05:4", [("SDD_2026_05", 4)], []),
    ("SDD_2026_05:4; SDD_2026_01_Annex01:1", [("SDD_2026_05", 4), ("SDD_2026_01_Annex01", 1)], []),
    ("CBB_2026_01:1,2,3; SDD_2026_05:2", [("CBB_2026_01", 1), ("CBB_2026_01", 2), ("CBB_2026_01", 3),
                                          ("SDD_2026_05", 2)], []),
    (" A : 1 - 2 , 2 ;; B:3 ", [("A", 1), ("A", 2), ("B", 3)], []),
    ("", [], []),
    ("A:1; no colon; B:x; C:; :4; D:3-1; E:0", [("A", 1)], ["no colon", "B:x", "C:", ":4", "D:3-1", "E:0"]),
])
def test_cited_pages_parser(text, pairs, bad):
    assert knowledge.parse_cited_pages(text) == (pairs, bad)


def test_cited_pages_are_validated_against_registry_and_doc_filter(caplog):
    item = rule("T7", doc_filter=("DOC_A", "DOC_B"))
    registry = {"DOC_A": {}, "DOC_C": {}}
    with caplog.at_level(logging.WARNING):
        kept = knowledge._validated_pages(item, "DOC_A:1,2; DOC_B:3; DOC_C:4; broken", registry)
    assert kept.doc_pages == (("DOC_A", 1), ("DOC_A", 2))
    assert "DOC_B – not in the document registry" in caplog.text
    assert "DOC_C – not in its doc_filter" in caplog.text
    assert "broken" in caplog.text


def test_source_page_check_uses_doc_and_page():
    hit = {"chunk_id": "D1-p4-c1", "doc_id": "D1", "page": 4}
    base = SimpleNamespace(
        rules=(
            rule("R1", doc_filter=("D1", "D2"), doc_pages=(("D1", 4),)),             # same doc and page
            rule("R2", doc_filter=("D1", "D2"), doc_pages=(("D2", 4),)),             # same page, other doc
            rule("R3", doc_filter=("D1",), citation="Circular, p.4"),                 # fallback: page only
            rule("R4", doc_filter=("D1",)),                                           # nothing cited: not counted
            rule("R5", doc_filter=(), doc_pages=()),                                  # no source: not counted
        ),
        retrieve=lambda query, doc_filter, k=2: [hit] if doc_filter else [],
    )
    check = knowledge.source_page_check(base)
    assert (check["matched"], check["total"]) == (2, 3)
    by_rule = {entry["rule_id"]: entry for entry in check["rules"]}
    assert by_rule["R1"]["matched"] and by_rule["R1"]["basis"] == "cited_pages"
    assert not by_rule["R2"]["matched"]
    assert by_rule["R3"]["matched"] and by_rule["R3"]["cited_pages"] == [{"doc_id": None, "page": 4}]


def test_a1_top_source_for_sim_hh_001_is_not_the_letterhead_page(needs_knowledge):
    body = get_recommendations().json()
    a1 = next((i for i in [body["follow_up"], *body["actions"]] if i and i["rule_id"] == "A1"), None)
    assert a1 is not None, "SIM-HH-001 is expected to get A1"
    top = a1["sources"][0]
    assert not (top["doc_id"] == "SDD_2026_05" and top["page"] == 1), top["chunk_id"]


def test_source_page_check_is_computed(needs_knowledge):
    base = knowledge.load()
    check = base.source_page_check
    assert check == knowledge.source_page_check(base)
    cited = [r for r in base.rules if (r.doc_pages or r.citation_pages) and r.doc_filter]
    assert check["total"] == len(cited) == len(check["rules"])
    assert check["matched"] == sum(r["matched"] for r in check["rules"])
    for entry in check["rules"]:
        source_rule = next(r for r in base.rules if r.rule_id == entry["rule_id"])
        top = base.retrieve(source_rule.query, source_rule.doc_filter, k=1)[0]
        assert entry["top_source"] == top["chunk_id"]
        if source_rule.doc_pages:
            assert entry["matched"] is ((top["doc_id"], top["page"]) in source_rule.doc_pages)
        else:
            assert entry["matched"] is (top["page"] in source_rule.citation_pages)
    for source_rule in base.rules:  # validated at load: registry and doc_filter only
        assert all(doc in base.documents and doc in source_rule.doc_filter for doc, _ in source_rule.doc_pages)


def test_retrieval_check_is_computed(needs_knowledge):
    base = knowledge.load()
    assert base.retrieval_check == knowledge.retrieval_check(base)
    assert base.retrieval_check["queries"] == len(knowledge.RETRIEVAL_TEST_SET) == 12
    assert 0 <= base.retrieval_check["hit_at_1"] <= base.retrieval_check["hit_at_3"] <= 12


# --- endpoint -------------------------------------------------------------------------------

def get_recommendations(key=KEY):
    return client.get(f"{BASE}/households/{key}/recommendations")


def test_recommendations_shape_without_key(needs_knowledge):
    response = get_recommendations()
    assert response.status_code == 200
    body = response.json()
    assert body["is_synthetic"] is True
    assert body["household_key"] == KEY
    assert body["generated_by"] == "rules+retrieval"
    assert body["knowledge_version"] == knowledge.load().version
    assert body["disclaimer"] == service.RECOMMENDATION_DISCLAIMER
    assert body["follow_up"]["level"] == "A"
    rules = {r.rule_id: r for r in knowledge.load().rules}
    for item in [body["follow_up"], *body["actions"]]:
        source_rule = rules[item["rule_id"]]
        assert item["summary_steps"] is None and item["decision"] is None
        assert item["draft"] is source_rule.draft
        assert item["guardrail"] == source_rule.guardrail
        assert item["research_basis"] == source_rule.research_basis
        assert all(s["doc_id"] in source_rule.doc_filter for s in item["sources"])
        assert all(s["chunk_id"] != item["research_basis"] for s in item["sources"])
    assert all(item["level"] == "B" for item in body["actions"])


def test_recommendation_errors(needs_knowledge, monkeypatch, tmp_path):
    assert get_recommendations("SIM-HH-NOPE").status_code == 404
    assert get_recommendations("REAL-1").status_code == 422
    monkeypatch.setattr(knowledge, "folder", lambda: tmp_path)
    knowledge.clear_cache()
    try:
        response = get_recommendations()
        assert response.status_code == 503
        assert "Knowledge base not installed" in response.json()["detail"]
        assert client.get(f"{BASE}/model/evidence").json()["recommendations"] is None
        assert client.get(f"{BASE}/risk/household/{KEY}").status_code == 200  # rest of v2 unaffected
    finally:
        knowledge.clear_cache()


def test_evidence_has_recommendation_summary(needs_knowledge):
    block = client.get(f"{BASE}/model/evidence").json()["recommendations"]
    base = knowledge.load()
    assert block == base.evidence()
    assert block["n_rules"] == len(base.rules) and block["n_chunks"] == len(base.chunks)
    assert block["n_documents"] == len(base.documents)


# --- LLM summary (always mocked) ------------------------------------------------------------

def household_identity() -> tuple[str, str]:
    detail = client.get(f"{BASE}/risk/household/{KEY}").json()
    return KEY, detail["latest_visit"]["district"]


def test_prompt_builder_takes_only_allowed_inputs():
    assert set(inspect.signature(summary.build_prompt).parameters) == {
        "risk_class", "alert_3m", "reason_labels", "action_en", "guardrail", "chunks"}


def test_llm_prompt_has_no_household_key_or_district(needs_knowledge, monkeypatch):
    prompts = []

    def fake(prompt, key):
        prompts.append(prompt)
        ids = [line[1:-1] for line in prompt.splitlines() if line.startswith("[") and line.endswith("]")]
        return json.dumps({"steps": [{"text": "Visit the household.", "chunk_ids": ids[:1]},
                                     {"text": "Check the circular.", "chunk_ids": ids[-1:]}]})

    monkeypatch.setattr(summary, "api_key", lambda: "test-key")
    monkeypatch.setattr(summary, "call_llm", fake)
    body = get_recommendations().json()
    key, district = household_identity()
    assert prompts
    for prompt in prompts:
        assert key not in prompt
        own_text = prompt.split("Official circular extracts")[0] + prompt.split("Write ")[-1]
        assert district not in own_text
    assert body["generated_by"] == "rules+retrieval+llm"
    with_sources = [i for i in [body["follow_up"], *body["actions"]] if i["sources"]]
    for item in with_sources:
        cited = {c for step in item["summary_steps"] for c in step["chunk_ids"]}
        assert cited <= {s["chunk_id"] for s in item["sources"]}


@pytest.mark.parametrize("answer", [
    json.dumps({"steps": [{"text": "a", "chunk_ids": ["NOT-A-GIVEN-CHUNK"]}, {"text": "b", "chunk_ids": ["X"]}]}),
    json.dumps({"steps": [{"text": "a", "chunk_ids": []}, {"text": "b", "chunk_ids": []}]}),
    json.dumps({"steps": [{"text": "only one step", "chunk_ids": ["X"]}]}),
    "not json",
])
def test_invalid_llm_answer_falls_back(needs_knowledge, monkeypatch, answer):
    monkeypatch.setattr(summary, "api_key", lambda: "test-key")
    monkeypatch.setattr(summary, "call_llm", lambda prompt, key: answer)
    body = get_recommendations().json()
    assert body["generated_by"] == "rules+retrieval"
    assert all(item["summary_steps"] is None for item in [body["follow_up"], *body["actions"]])


def test_llm_error_falls_back(needs_knowledge, monkeypatch):
    calls = []

    def broken(prompt, key):
        calls.append(1)
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr(summary, "api_key", lambda: "test-key")
    monkeypatch.setattr(summary, "call_llm", broken)
    response = get_recommendations()
    assert response.status_code == 200
    assert response.json()["generated_by"] == "rules+retrieval"
    assert len(calls) == 1  # no more calls after the first failure in a request


def test_no_key_never_calls_the_llm(needs_knowledge):
    assert summary.api_key() is None  # fixture: no key
    assert get_recommendations().json()["generated_by"] == "rules+retrieval"


def test_parse_steps_rules():
    allowed = {"C1", "C2"}
    good = json.dumps({"steps": [{"text": "a", "chunk_ids": ["C1"]}, {"text": "b", "chunk_ids": ["C1", "C2"]}]})
    assert summary.parse_steps(good, allowed) == [{"text": "a", "chunk_ids": ["C1"]},
                                                  {"text": "b", "chunk_ids": ["C1", "C2"]}]
    five = json.dumps({"steps": [{"text": "a", "chunk_ids": ["C1"]}] * 5})
    assert summary.parse_steps(five, allowed) is None


# --- FR7 decisions --------------------------------------------------------------------------

def decide(rule_id, body, key=KEY):
    return client.post(f"{BASE}/households/{key}/recommendations/{rule_id}/decision", json=body)


def test_decision_round_trip_returns_latest_per_rule(needs_knowledge):
    body = get_recommendations().json()
    rule_id = body["follow_up"]["rule_id"]
    first = decide(rule_id, {"decision": "modify", "note": "Visit with the coach."})
    assert first.status_code == 200
    second = decide(rule_id, {"decision": "accept", "planned_visit_date": "2026-12-03"})
    assert second.status_code == 200
    saved = second.json()["decision"]
    assert saved["decision"] == "accept"
    assert saved["planned_visit_date"] == "2026-12-03"
    assert saved["knowledge_version"] == body["knowledge_version"]
    assert saved["created_at"]
    again = get_recommendations().json()
    assert again["follow_up"]["decision"] == saved
    assert all(item["decision"] is None for item in again["actions"])


def test_decision_validation(needs_knowledge):
    rule_id = get_recommendations().json()["follow_up"]["rule_id"]
    assert decide(rule_id, {"decision": "maybe"}).status_code == 422
    assert decide(rule_id, {"decision": "accept", "district": "x"}).status_code == 422
    assert decide(rule_id, {"decision": "accept", "planned_visit_date": "03/12/2026"}).status_code == 422
    assert decide("B99", {"decision": "accept"}).status_code == 404
    assert decide(rule_id, {"decision": "accept"}, key="SIM-HH-NOPE").status_code == 404
    assert decide("drop table", {"decision": "accept"}).status_code in (404, 422)


def test_sqlite_store_keeps_only_allowed_fields(tmp_path):
    store = decisions.SQLiteStore(tmp_path / "d.sqlite3")
    decisions.set_store(store)
    decisions.save({"household_key": KEY, "rule_id": "A1", "decision": "reject", "note": None,
                    "planned_visit_date": None, "knowledge_version": "v"})
    [record] = store.records(KEY)
    assert set(record) == {"id", *decisions.FIELDS}
