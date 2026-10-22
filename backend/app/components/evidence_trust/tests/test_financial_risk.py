"""Offline tests for the financial-risk module."""

from datetime import date

from app.components.evidence_trust.ml.financial_risk.contracts import Visit
from app.components.evidence_trust.ml.financial_risk.features import build_features
from app.components.evidence_trust.ml.financial_risk.pipeline import FinancialRiskPipeline
from app.components.evidence_trust.ml.financial_risk.repository import InMemoryFinancialRepository
from app.components.evidence_trust.ml.financial_risk.scoring import rule_hits
from app.components.evidence_trust.ml.financial_risk.bill_verifier import BillEvidenceVerifier, ExtractedBill


def visit(month=1, spent=50000, remaining=100000, household="hashed-household", **kwargs):
    return Visit(str(month), f"source-{month}", household, month, date(2026, 1, 1), **{"grant_spent_lkr": spent, "grant_remaining_lkr": remaining, "grant_used_per_plan": True, "business_running": True, "profit": True, "borrowed_money": False, "revenue_mid_lkr": 5000, "problem_count": 0, "record_keeping_level": 1, "saved_amount_lkr": 0, **kwargs})


def test_feature_parity_hand_computed():
    current = visit(month=2, spent=60000, remaining=90000)
    previous = visit(month=1, spent=50000, remaining=100000)
    features = build_features(current, [previous])
    assert features["spent_pct"] == 0.4
    assert features["spend_rate"] == 0.2
    assert features["spend_change"] == 10000
    assert features["total_change"] == 0
    assert features["has_history"] == 1
    assert features["remaining_up"] == 0


def test_history_only_earlier_same_household():
    repo = InMemoryFinancialRepository()
    target = visit(month=3)
    repo.upsert_visit(visit(month=1))
    repo.upsert_visit(visit(month=2))
    repo.upsert_visit(visit(month=4))
    repo.upsert_visit(visit(month=3, household="other"))
    repo.upsert_visit(target)
    assert [x.month_index for x in repo.get_history(target)] == [1, 2]


def test_missing_amount_is_unknown_not_zero():
    repo = InMemoryFinancialRepository()
    current = visit(month=1, spent=None, remaining=None)
    repo.upsert_visit(current)
    report = FinancialRiskPipeline(repo, artifact=None).score("1")
    ledger = next(x for x in report.blocks if x.name == "grant_ledger")
    assert next(x for x in ledger.checks if x.code == "BALANCE_MISMATCH").value is None
    assert not report.flags


def test_fake_pipeline_scores_batch_without_real_artifact():
    repo = InMemoryFinancialRepository()
    for number in range(50): repo.upsert_visit(visit(month=number + 1, household=None))
    reports = [FinancialRiskPipeline(repo).score(str(number + 1)) for number in range(50)]
    assert len(reports) == 50


def test_each_configured_rule_fires_and_clean_row_does_not():
    names = ("total_changed", "remaining_up", "spent_but_stopped", "not_per_plan", "bills_unsettled", "slow_use")
    config = {"rules": [{"name": name, "points": 1, "text": name} for name in names]}
    features = {"has_history": 1, "total_change": 1, "remaining_up": 1, "spent_pct": .5, "business_running": 0, "not_per_plan": 1, "bills_streak": 2, "slow_use": 1}
    assert {x["name"] for x in rule_hits(features, config)} == set(names)
    clean = dict(features, has_history=0, total_change=0, remaining_up=0, business_running=1, not_per_plan=0, bills_streak=0, slow_use=0)
    assert rule_hits(clean, config) == []


def test_status_balance_conflict_for_not_fully_used_zero_balance():
    repo = InMemoryFinancialRepository()
    current = visit(month=2, remaining=0, grant_use_status="Received, not fully used")
    repo.upsert_visit(current)
    report = FinancialRiskPipeline(repo).score("2")
    check = next(x for block in report.blocks for x in block.checks if x.code == "STATUS_BALANCE_CONFLICT")
    assert check.value == 0


def test_bill_total_and_month_advisory_checks():
    class FakeExtractor:
        def __init__(self): self.items = iter([ExtractedBill(30000, date(2026, 2, 4), "LKR"), ExtractedBill(20000, date(2026, 2, 20), "LKR")])
        def extract(self, image): return next(self.items)

    monitored = visit(month=2, spent=50000, remaining=100000)
    monitored.visit_date = date(2026, 2, 1)
    checks = BillEvidenceVerifier(FakeExtractor()).verify_many(monitored, [b"one", b"two"])
    assert next(x for x in checks if x.code == "BILL_TOTAL_MATCH").value == 1
    assert next(x for x in checks if x.code == "BILL_MONTH_MATCH").value == 1


def test_bill_mismatch_is_advisory_and_does_not_change_financial_consistency():
    class FakeExtractor:
        def extract(self, image): return ExtractedBill(1, date(2026, 1, 1), "LKR")

    checks = BillEvidenceVerifier(FakeExtractor()).verify_many(visit(month=1, spent=50000, remaining=100000), [b"bill"])
    assert {x.code for x in checks if x.value == 0} == {"BILL_TOTAL_MATCH"}
