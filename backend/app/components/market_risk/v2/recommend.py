"""Rule engine for recommendations (FR4) with rule-filtered retrieval (FR5).

Triggers in risk_actions.csv are checked with a small, safe evaluator: Python's ast parser
plus a whitelist (names, constants, tuples, comparisons, in, and/or/not). Nothing is eval'd.
Level A: exactly one follow-up rule (lowest priority number). Level B: every matching rule,
SHAP-linked rules first. Z0 (data completion) comes first when a SHAP factor that raises risk was
not answered; Z1 is added when a raising factor that has a value has no matching rule.
"""

import ast
import logging
import math
import operator
from typing import Any

import pandas as pd

from app.components.market_risk.v2 import pipeline
from app.components.market_risk.v2.knowledge import KnowledgeBase, Rule

logger = logging.getLogger(__name__)

FALLBACK_FIELD = "shap_top_factors"  # trigger_fields of the SHAP-driven rules Z0 and Z1 (not compiled)
MISSING_RULE = "Z0"  # data completion: raising factors without an answer
FALLBACK_RULE = "Z1"  # no official guidance found
NOT_ANSWERED = "Not answered"  # pipeline.format_value text for a missing form answer
ACTIONABLE_GROUPS = {"Business", "Household shock", "Market"}  # SHAP groups that can call for Z1
UNASSIGNED = "Unassigned"

_ALLOWED_NODES = (
    ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.Compare,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In,
    ast.Name, ast.Load, ast.Constant, ast.Tuple,
)
_COMPARE = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt, ast.LtE: operator.le,
    ast.Gt: operator.gt, ast.GtE: operator.ge, ast.In: lambda left, right: left in right,
}
_ORDERING = (ast.Lt, ast.LtE, ast.Gt, ast.GtE)


class UnsafeExpression(ValueError):
    """The trigger uses syntax outside the whitelist."""


class UnknownField(KeyError):
    """The trigger names a field the household data does not have."""


def compile_trigger(text: str) -> ast.Expression:
    """Parse a trigger and reject anything outside the whitelist (calls, attributes, subscripts…)."""
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpression("not a valid expression") from exc
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise UnsafeExpression(f"{type(node).__name__} is not allowed")
        if isinstance(node, ast.Name) and node.id.startswith("_"):
            raise UnsafeExpression("names starting with _ are not allowed")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (str, int, float, bool, type(None))):
            raise UnsafeExpression("only text, number, true/false and null constants are allowed")
    return tree


def field_names(tree: ast.Expression) -> set[str]:
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


def _value(node: ast.AST, context: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return context[node.id]
    if isinstance(node, ast.Tuple):
        return tuple(_value(item, context) for item in node.elts)
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            return all(bool(_value(item, context)) for item in node.values)
        return any(bool(_value(item, context)) for item in node.values)
    if isinstance(node, ast.UnaryOp):
        return not bool(_value(node.operand, context))
    if isinstance(node, ast.Compare):
        left = _value(node.left, context)
        for op, comparator in zip(node.ops, node.comparators):
            right = _value(comparator, context)
            if isinstance(op, _ORDERING) and (left is None or right is None):
                return False  # an unanswered value never satisfies <, <=, >, >=
            try:
                if not _COMPARE[type(op)](left, right):
                    return False
            except TypeError:
                return False
            left = right
        return True
    raise UnsafeExpression(f"{type(node).__name__} is not allowed")  # unreachable after compile_trigger


def evaluate(tree: ast.Expression, context: dict[str, Any]) -> bool:
    """True when the trigger holds. Every field must exist in the context (else UnknownField)."""
    missing = sorted(field_names(tree) - context.keys())
    if missing:
        raise UnknownField(missing[0])
    return bool(_value(tree.body, context))


def _plain(value: Any) -> Any:
    if value is None or value is pd.NA:
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def household_context(row: pd.Series) -> dict[str, Any]:
    """Trigger fields for one stored visit (features joined with predictions).

    Adds the names the rule table uses: alert_3m (the API's 3-month alert) and prev_risk_class
    (the previous visit's class, from prev_risk_ord with the backend's own class names).
    """
    context = {str(name): _plain(value) for name, value in row.items()}
    alert = context.get("high_alert_3M")
    context["alert_3m"] = None if alert is None else bool(alert)
    previous = context.get("prev_risk_ord")
    context["prev_risk_class"] = None if previous is None else pipeline.RISK_NAMES.get(int(previous))
    return context


def _factor(shap_factor: dict[str, Any]) -> dict[str, str]:
    """A linked SHAP factor as shown to the officer: its label and the household's value label."""
    return {"label": str(shap_factor["label"]), "value": str(shap_factor.get("value") or "")}


def is_missing(shap_factor: dict[str, Any]) -> bool:
    """A form question without an answer (not 'No market data' or 'No earlier visit')."""
    return shap_factor.get("raw_value") is None and shap_factor.get("value") == NOT_ANSWERED


class Engine:
    """Compiled rule table of one knowledge-base version."""

    def __init__(self, base: KnowledgeBase):
        self.base = base
        self.compiled: dict[str, ast.Expression] = {}
        self.fallback: Rule | None = None
        self.missing: Rule | None = None
        for rule in base.rules:
            if rule.trigger_fields == (FALLBACK_FIELD,):
                if rule.rule_id == MISSING_RULE:
                    self.missing = rule
                elif rule.rule_id == FALLBACK_RULE:
                    self.fallback = rule
                else:
                    logger.warning("market_risk v2: rule %s skipped – only Z0 and Z1 may use %s",
                                   rule.rule_id, FALLBACK_FIELD)
                continue
            try:
                self.compiled[rule.rule_id] = compile_trigger(rule.trigger)
            except UnsafeExpression as exc:
                logger.warning("market_risk v2: rule %s skipped – trigger not allowed (%s)", rule.rule_id, exc)

    def matches(self, rule: Rule, context: dict[str, Any]) -> bool:
        tree = self.compiled.get(rule.rule_id)
        if tree is None:
            return False
        try:
            return evaluate(tree, context)
        except UnknownField as exc:
            logger.warning("market_risk v2: rule %s skipped – unknown field %s", rule.rule_id, exc.args[0])
            return False

    def select(self, context: dict[str, Any], shap_factors: list[dict[str, Any]]) -> tuple[
            tuple[Rule, list[dict[str, str]]] | None, list[tuple[Rule, list[dict[str, str]]]]]:
        """(follow-up rule, [(action rule, linked SHAP factors as {label, value})]) for one visit."""
        level_a = [r for r in self.base.rules if r.level == "A" and self.matches(r, context)]
        follow_up = min(level_a, key=lambda r: (r.priority, r.rule_id)) if level_a else None
        if follow_up is not None and context.get("risk_class_t") == UNASSIGNED:
            return (follow_up, []), []  # A0: no recommendation from an incomplete form

        raising = [f for f in shap_factors if f["contribution"] > 0]
        level_b = [r for r in self.base.rules if r.level == "B" and self.matches(r, context)]

        def linked(rule: Rule) -> list[dict[str, Any]]:
            return [f for f in raising if f["feature"] in rule.trigger_fields]

        def order(rule: Rule) -> tuple:
            factors = linked(rule)
            first = raising.index(factors[0]) if factors else len(raising)
            return (0 if factors else 1, first, rule.priority, rule.rule_id)

        actions = [(rule, [_factor(f) for f in linked(rule)]) for rule in sorted(level_b, key=order)]
        missing = [f for f in raising if is_missing(f)]
        if missing and self.missing is not None:
            actions.insert(0, (self.missing, [_factor(f) for f in missing]))
        covered = {field for rule in level_b for field in rule.trigger_fields}
        unmatched = [f for f in raising if f["group"] in ACTIONABLE_GROUPS and f["feature"] not in covered
                     and f.get("raw_value") is not None]
        if unmatched and self.fallback is not None:
            actions.append((self.fallback, [_factor(f) for f in unmatched]))
        return ((follow_up, []) if follow_up else None), actions

    def item(self, rule: Rule, factors: list[dict[str, str]]) -> dict[str, Any]:
        return {
            "rule_id": rule.rule_id,
            "level": rule.level,
            "action_category": rule.action_category,
            "reason_label": rule.reason_label,
            "action_en": rule.action_en,
            "timing_days": rule.timing_days,
            "circular_says": rule.circular_says,
            "guardrail": rule.guardrail,
            "research_basis": rule.research_basis,
            "draft": rule.draft,
            "related_factors": factors,
            "sources": self.base.retrieve(rule.query, rule.doc_filter, cited=rule.doc_pages),
            "summary_steps": None,
            "decision": None,
        }


_engines: dict[str, Engine] = {}


def engine_for(base: KnowledgeBase) -> Engine:
    if base.version not in _engines:
        _engines.clear()
        _engines[base.version] = Engine(base)
    return _engines[base.version]
