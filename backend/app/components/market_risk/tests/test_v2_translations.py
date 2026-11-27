"""Machine translations of Sinhala chunks: the one-off script (LLM always mocked) and loading.

Synthetic chunks in a temporary folder only. No API calls.
"""

import json

import pytest

from app.components.market_risk.v2 import knowledge, translate_chunks

CHUNKS = [
    {"chunk_id": "S1-p1-c1", "doc_id": "S1", "page": 1, "language": "si", "text": "සමෘද්ධි   ප්‍රජාමූල 2026/05."},
    {"chunk_id": "S1-p1-c2", "doc_id": "S1", "page": 1, "language": "si", "text": "ණය රු. 25,000 කි."},
    {"chunk_id": "S1-p2-c1", "doc_id": "S1", "page": 2, "language": "si", "text": "ඉතුරුම් වැඩසටහන."},
    {"chunk_id": "E1-p1-c1", "doc_id": "E1", "page": 1, "language": "en", "text": "English circular text."},
]


def fake_llm(calls, broken=()):
    """Answers every id in the prompt with 'EN <id>'; ids in `broken` are left out (invalid answer)."""
    def llm(prompt, key, model):
        ids = [line[1:-1] for line in prompt.splitlines() if line.startswith("[") and line.endswith("]")]
        calls.append(ids)
        return json.dumps({"translations": [{"chunk_id": i, "text_en": f"EN {i}"} for i in ids if i not in broken]})
    return llm


def lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_script_translates_only_sinhala_and_writes_the_fields(tmp_path):
    out, calls = tmp_path / "en.jsonl", []
    counts = translate_chunks.run(CHUNKS, out, "test-key", "test-model", batch_size=2, llm=fake_llm(calls))
    assert counts == {"translated": 3, "skipped": 0, "failed": 0}
    assert calls == [["S1-p1-c1", "S1-p1-c2"], ["S1-p2-c1"]]  # batched; the English chunk is never sent
    rows = lines(out)
    assert [r["chunk_id"] for r in rows] == ["S1-p1-c1", "S1-p1-c2", "S1-p2-c1"]
    assert all(set(r) == {"chunk_id", "text_en", "model", "created_at"} and r["model"] == "test-model" for r in rows)


def test_script_is_resumable(tmp_path):
    out, calls = tmp_path / "en.jsonl", []
    translate_chunks.run(CHUNKS, out, "k", "m", batch_size=2, limit=2, llm=fake_llm(calls))
    calls.clear()
    counts = translate_chunks.run(CHUNKS, out, "k", "m", batch_size=2, llm=fake_llm(calls))
    assert counts == {"translated": 1, "skipped": 2, "failed": 0}
    assert calls == [["S1-p2-c1"]]
    assert len(lines(out)) == 3


def test_incomplete_answer_is_retried_once_then_failed(tmp_path):
    out, calls = tmp_path / "en.jsonl", []
    counts = translate_chunks.run(CHUNKS, out, "k", "m", batch_size=2, llm=fake_llm(calls, broken={"S1-p1-c2"}))
    assert counts == {"translated": 1, "skipped": 0, "failed": 2}
    assert calls == [["S1-p1-c1", "S1-p1-c2"]] * translate_chunks.ATTEMPTS + [["S1-p2-c1"]]
    assert [r["chunk_id"] for r in lines(out)] == ["S1-p2-c1"]  # nothing written for the failed batch


def test_llm_error_counts_as_failed(tmp_path):
    def broken(prompt, key, model):
        raise TimeoutError("simulated")

    counts = translate_chunks.run(CHUNKS, tmp_path / "en.jsonl", "k", "m", batch_size=6, llm=broken)
    assert counts == {"translated": 0, "skipped": 0, "failed": 3}


@pytest.mark.parametrize("answer", [
    "not json",
    json.dumps({"translations": [{"chunk_id": "A", "text_en": "x"}]}),                            # B missing
    json.dumps({"translations": [{"chunk_id": "A", "text_en": "x"}, {"chunk_id": "B", "text_en": " "}]}),
    json.dumps({"translations": [{"chunk_id": "A", "text_en": "x"}, {"chunk_id": "B", "text_en": "y"},
                                 {"chunk_id": "C", "text_en": "z"}]}),                          # unknown id
])
def test_parse_translations_rejects_bad_answers(answer):
    assert translate_chunks.parse_translations(answer, ["A", "B"]) is None


def test_parse_translations_accepts_a_bare_list():
    answer = json.dumps([{"chunk_id": "A", "text_en": " x  y "}, {"chunk_id": "B", "text_en": "z"}])
    assert translate_chunks.parse_translations(answer, ["A", "B"]) == {"A": "x y", "B": "z"}


def test_prompt_keeps_numbers_and_holds_only_the_passages():
    prompt = translate_chunks.build_prompt([("S1-p1-c2", "ණය රු. 25,000 කි.")])
    assert "[S1-p1-c2]\nණය රු. 25,000 කි." in prompt
    assert "Keep all numbers, dates, amounts" in prompt and "circular numbers" in prompt
    assert "SIM-HH" not in prompt


def test_read_translations_skips_bad_lines_and_unknown_chunks(tmp_path, caplog):
    path = tmp_path / "en.jsonl"
    path.write_text("\n".join([
        json.dumps({"chunk_id": "S1-p1-c1", "text_en": "Samurdhi", "model": "m1"}),
        "not json",
        json.dumps({"chunk_id": "UNKNOWN", "text_en": "x", "model": "m1"}),
        json.dumps({"chunk_id": "S1-p1-c2", "text_en": "  ", "model": "m1"}),
    ]), encoding="utf-8")
    found = knowledge.read_translations(path, {c["chunk_id"] for c in CHUNKS})
    assert found == {"S1-p1-c1": {"text_en": "Samurdhi", "model": "m1"}}
    assert "3 translation lines skipped" in caplog.text
    assert knowledge.read_translations(tmp_path / "missing.jsonl", {"S1-p1-c1"}) == {}


def tiny(translations):
    vectorizer = knowledge.TfidfVectorizer(**knowledge.VECTORIZER_SETTINGS)
    matrix = vectorizer.fit_transform([c["text"] for c in CHUNKS])
    return knowledge.KnowledgeBase(
        version="test", rules=(), documents={}, chunks=CHUNKS, vectorizer=vectorizer, matrix=matrix,
        doc_ids=knowledge.np.array([c["doc_id"] for c in CHUNKS]), retrieval_check={}, source_page_check={},
        translations=translations)


def test_sources_get_trimmed_excerpt_en_or_null():
    long_en = "ject cut. " + " ".join(f"Officers report progress to division {i}." for i in range(40))
    base = tiny({"S1-p1-c1": {"text_en": long_en, "model": "m1"}})
    source = base.source(CHUNKS[0])
    assert source["excerpt_en"] == knowledge.excerpt(long_en)
    assert source["excerpt_en"].startswith("Officers") and source["excerpt_en"].endswith("." + knowledge.ELLIPSIS)
    assert base.source(CHUNKS[1])["excerpt_en"] is None   # Sinhala, not translated
    assert base.source(CHUNKS[3])["excerpt_en"] is None   # English chunk


def test_translation_summary_counts_sinhala_chunks():
    assert tiny({}).translation_summary() == {"translated": 0, "sinhala_chunks": 3, "model": None}
    base = tiny({"S1-p1-c1": {"text_en": "a", "model": "m1"}, "S1-p1-c2": {"text_en": "b", "model": "m1"},
                 "E1-p1-c1": {"text_en": "c", "model": "m2"}})  # an English chunk does not count
    assert base.translation_summary() == {"translated": 2, "sinhala_chunks": 3, "model": "m1"}


def test_loaded_base_picks_up_a_new_translations_file(tmp_path, monkeypatch):
    """The cached knowledge base re-reads the translations file when it appears or changes."""
    monkeypatch.setattr(knowledge, "folder", lambda: tmp_path)
    monkeypatch.setattr(knowledge, "_load", lambda: tiny({}))
    knowledge.clear_cache()
    try:
        assert knowledge.load().translation_summary()["translated"] == 0
        (tmp_path / knowledge.TRANSLATIONS_FILE).write_text(
            json.dumps({"chunk_id": "S1-p2-c1", "text_en": "Savings programme.", "model": "m1"}) + "\n",
            encoding="utf-8")
        loaded = knowledge.load()
        assert loaded.translation_summary()["translated"] == 1
        assert loaded.version == "test"  # translations never change knowledge_version
    finally:
        knowledge.clear_cache()
