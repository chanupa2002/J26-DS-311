"""Sequential financial-risk pipeline."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from .blocks import advisory_block, context_block, ledger_block, reliability_block
from .bill_verifier import BillEvidenceVerifier
from .config_loader import load_config
from .contracts import BlockResult, CheckResult, FinancialReport, Visit
from .features import build_features
from .loader import load_artifact
from .repository import FinancialRepository


class FinancialRiskPipeline:
    """Run evidence reliability, ledger, context and advisory blocks."""

    def __init__(self, repository: FinancialRepository, config: dict[str, Any] | None = None, artifact: dict[str, Any] | None = None, scorer: Any = None, bill_verifier: BillEvidenceVerifier | None = None) -> None:
        self.repository = repository
        self.config, self.config_hash = load_config() if config is None else (config, "injected")
        self.artifact = artifact
        self.scorer = scorer
        bill_config = self.config.get("bill", {})
        self.bill_verifier = bill_verifier or BillEvidenceVerifier(total_tolerance_lkr=float(bill_config.get("total_tolerance_lkr", 0.01)), required_currency=str(bill_config.get("required_currency", "LKR")))

    def score(self, visit_id: str, bill_images: list[bytes] | None = None) -> FinancialReport:
        visit = self.repository.get_visit(visit_id)
        if visit is None: raise ValueError(f"Monitoring visit not found: {visit_id}")
        history = self.repository.get_history(visit)
        features = build_features(visit, history)
        reliability, reliability_checks = reliability_block(visit, self.config)
        blocks = [BlockResult("evidence_reliability", reliability_checks)]
        ledger = ledger_block(visit, history, self.config)
        blocks.append(BlockResult("grant_ledger", ledger))
        blocks.append(BlockResult("livelihood_context", context_block(visit)))
        artifact = self.artifact
        if artifact is None and visit.grant_spent_lkr is not None:
            try: artifact = load_artifact(self.config.get("artifact_path"))
            except (FileNotFoundError, ImportError): artifact = None
        scored = None
        if visit.grant_spent_lkr is not None:
            checks, scored = advisory_block(features, artifact, self.config, self.scorer or (artifact.get("pipeline").score_samples if artifact else None))
        else:
            checks = [CheckResult("ANOMALY_RISK", None, "No grant amounts available; model scoring is not applicable.", {"reason": "no grant amounts"}, "info")]
            scored = {"rule_score": None, "model_score": None, "risk": None, "level": None, "hits": []}
        blocks.append(BlockResult("anomaly_risk", checks))
        blocks.append(BlockResult("bill_to_expenditure", self.bill_verifier.verify_many(visit, bill_images or [])))
        # Context notes and GRANT_STALLED are intentionally display/support hints,
        # not financial flags. The advisory anomaly block remains separate from
        # the FINANCIAL_CONSISTENCY signal used by trust fusion.
        flags = [check for block in blocks if block.name in {"grant_ledger", "anomaly_risk", "bill_to_expenditure"} for check in block.checks if check.value == 0 and check.code != "GRANT_STALLED"]
        unknowns = [check for block in blocks for check in block.checks if check.value is None]
        # Financial consistency comes from ledger block only; advisory anomaly is separate.
        report = FinancialReport(visit_id, str(uuid4()), reliability["level"], reliability["completeness"], scored["risk"], scored["rule_score"], scored["model_score"], scored["level"], "synthetic" if visit.is_synthetic else "observed", blocks, flags, unknowns, features, artifact.get("model_name") if artifact else None, str(artifact.get("created")) if artifact else None, artifact.get("versions", {}) if artifact else {})
        return report

    def score_and_save(self, visit_id: str, bill_images: list[bytes] | None = None) -> FinancialReport:
        report = self.score(visit_id, bill_images)
        self.repository.save_run(report)
        return report
