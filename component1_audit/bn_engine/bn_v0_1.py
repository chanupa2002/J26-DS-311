"""
Component 1 - Bayesian Network engine v0.1 (research output - not an eligibility determination).

Takes the fuzzy layer's soft low/medium/high memberships per domain as soft evidence and
returns a posterior over a Vulnerability node, using a two-level, tree-structured network:

    domain leaves  ->  intermediate nodes (sensitivity, adaptive_capacity)  ->  vulnerability

Direction: every state scale is "deprivation": high = more vulnerable (for adaptive_capacity,
high = LOW capacity). The fuzzy layer already outputs degrees of deprivation.

Decisions implemented (docs/decision log, section 9):
  M-03  conditional tables by the ranked-nodes method (weighted mean + truncated normal)
  M-04  missing stays missing: an unobserved domain contributes no evidence
  M-05  every output carries the research label
  B-01  3 states (n_states=5 is the sensitivity run; applies to internal nodes only because the
        fuzzy evidence has 3 states)
  B-02  equal weights (weights can be perturbed per node)
  B-03  sigma = 0.15 ("moderate"); sensitivity: 0.08 and 0.25
  B-04  evidence blended toward uniform in proportion to n_used / n_total (modes: proportional,
        none, min_coverage)
  B-05  uniform domain priors (empirical priors are the sensitivity run)

Nothing is trained on label_high_vuln or pc_cons; both are refused as inputs.
Because the structure is a tree and evidence sits only on leaves, forward propagation of the
leaf beliefs through the conditional tables gives the exact marginals.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

MODEL_VERSION = "bn_v0.1.0"
RESEARCH_LABEL = "Research output - not an eligibility determination"
LEAF_STATES = ("low", "medium", "high")
N_LEAF = 3
FORBIDDEN_COLUMNS = {"label_high_vuln", "pc_cons"}
_STATE_NAMES = {
    3: ("low", "medium", "high"),
    5: ("very_low", "low", "medium", "high", "very_high"),
}
BLEND_MODES = ("proportional", "none", "min_coverage")


def state_names(n_states: int) -> Tuple[str, ...]:
    return _STATE_NAMES.get(n_states, tuple(f"s{i + 1}" for i in range(n_states)))


def state_midpoints(n_states: int) -> np.ndarray:
    return np.array([(i + 0.5) / n_states for i in range(n_states)])


def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def ranked_node_row(mean: float, sigma: float, n_states: int) -> np.ndarray:
    """Probability of each of n equal-width states on [0,1] under a normal truncated to [0,1]."""
    if sigma <= 0:
        raise ValueError("sigma must be > 0")
    edges = np.linspace(0.0, 1.0, n_states + 1)
    cdf = np.array([_phi((e - mean) / sigma) for e in edges])
    mass = np.diff(cdf)
    total = cdf[-1] - cdf[0]
    if total <= 1e-300:
        row = np.zeros(n_states)
        row[min(int(mean * n_states), n_states - 1)] = 1.0
        return row
    return mass / total


def build_cpt(parent_n_states: Sequence[int], weights: Sequence[float],
              sigma: float, n_states: int) -> np.ndarray:
    """Ranked-nodes table: child mean = weighted mean of the parents' state midpoints."""
    w = np.asarray(weights, dtype=float)
    if (w < 0).any() or w.sum() <= 0:
        raise ValueError("weights must be non-negative with a positive sum")
    w = w / w.sum()
    mids = [state_midpoints(n) for n in parent_n_states]
    cpt = np.zeros(tuple(parent_n_states) + (n_states,))
    for combo in itertools.product(*[range(n) for n in parent_n_states]):
        mean = sum(wi * mids[i][s] for i, (wi, s) in enumerate(zip(w, combo)))
        cpt[combo] = ranked_node_row(mean, sigma, n_states)
    return cpt


@dataclass
class NodeSpec:
    name: str
    parents: List[str]
    weights: Optional[Dict[str, float]] = None  # parent -> weight; None = equal


def default_nodes() -> Tuple[NodeSpec, ...]:
    return (
        NodeSpec("sensitivity", ["housing", "food", "demographic"]),
        NodeSpec("adaptive_capacity", ["economic"]),
        NodeSpec("vulnerability", ["sensitivity", "adaptive_capacity"]),
    )


@dataclass
class BNConfig:
    leaves: Tuple[str, ...] = ("housing", "economic", "food", "demographic")
    nodes: Tuple[NodeSpec, ...] = field(default_factory=default_nodes)
    n_states: int = 3
    sigma: float = 0.15
    blend: str = "proportional"
    min_coverage: float = 0.5
    priors: Optional[Dict[str, Sequence[float]]] = None  # leaf -> 3-vector; None = uniform

    def validate(self) -> None:
        if self.sigma <= 0:
            raise ValueError("sigma must be > 0")
        if self.blend not in BLEND_MODES:
            raise ValueError(f"blend must be one of {BLEND_MODES}")
        if self.n_states < 2:
            raise ValueError("n_states must be >= 2")
        for name in list(self.leaves) + [n.name for n in self.nodes]:
            if name in FORBIDDEN_COLUMNS:
                raise ValueError(f"{name} is a proxy/label column and cannot enter the network")
        known = set(self.leaves)
        seen = set()
        for n in self.nodes:
            if n.name in known or n.name in seen:
                raise ValueError(f"duplicate node name {n.name}")
            if not n.parents:
                raise ValueError(f"node {n.name} has no parents")
            for p in n.parents:
                if p not in known:
                    raise ValueError(f"node {n.name}: parent {p} is not a leaf or an earlier node")
            seen.add(n.name)
            known.add(n.name)
        if not self.nodes or self.nodes[-1].name != "vulnerability":
            raise ValueError("the last node must be named 'vulnerability'")


def structure_v02() -> Tuple[Tuple[str, ...], Tuple[NodeSpec, ...]]:
    """Proposed v0.2 structure (decision M-06). Not usable until those domains exist as scored leaves."""
    leaves = ("housing_shelter", "sanitation", "crowding_tenure", "food", "health", "demographic",
              "economic", "financial_resilience", "coping", "shocks")
    nodes = (
        NodeSpec("exposure", ["shocks"]),
        NodeSpec("sensitivity", ["housing_shelter", "sanitation", "crowding_tenure",
                                 "food", "health", "demographic"]),
        NodeSpec("adaptive_capacity", ["economic", "financial_resilience", "coping"]),
        NodeSpec("vulnerability", ["exposure", "sensitivity", "adaptive_capacity"]),
    )
    return leaves, nodes


def structure_v02_interim(include_exposure: bool = False) -> Tuple[Tuple[str, ...], Tuple[NodeSpec, ...]]:
    """Interim v0.2 structure (decision M-07, approved). Leaf names match the Stage 4 fuzzy columns
    (soft_<leaf>_low/medium/high, dom_<leaf>_n_used/n_total).

    The three housing leaves feed living_conditions first, so housing keeps roughly the weight of one
    domain (B-02). Exposure is OFF by default: X-01 (shocks) has no approved scoring rule while the
    O1 reference period is unverified (ISS-11). include_exposure=True adds it as an UNAPPROVED
    sensitivity run; the leaf is 'exposure' and the intermediate node is 'exposure_group'."""
    leaves = ["shelter_quality", "sanitation", "crowding_tenure", "food", "demographic",
              "health", "economic", "financial_resilience"]
    nodes = [
        NodeSpec("living_conditions", ["shelter_quality", "sanitation", "crowding_tenure"]),
        NodeSpec("sensitivity", ["living_conditions", "food", "demographic", "health"]),
        NodeSpec("adaptive_capacity", ["economic", "financial_resilience"]),
    ]
    top = ["sensitivity", "adaptive_capacity"]
    if include_exposure:
        leaves.append("exposure")
        nodes.append(NodeSpec("exposure_group", ["exposure"]))
        top = ["exposure_group"] + top
    nodes.append(NodeSpec("vulnerability", top))
    return tuple(leaves), tuple(nodes)


def config_v02_interim(include_exposure: bool = False, **kwargs) -> BNConfig:
    leaves, nodes = structure_v02_interim(include_exposure)
    return BNConfig(leaves=leaves, nodes=nodes, **kwargs)


def drop_leaf(cfg: BNConfig, leaf: str) -> BNConfig:
    """Leave-one-domain-out variant for sensitivity runs: the leaf is removed from its parent node.
    A parent node left with no parents is removed with it (and from its own parents)."""
    removed = {leaf}
    nodes = []
    for n in cfg.nodes:
        parents = [p for p in n.parents if p not in removed]
        if not parents:
            removed.add(n.name)
            continue
        w = None if n.weights is None else {p: v for p, v in n.weights.items() if p in parents}
        nodes.append(NodeSpec(n.name, parents, w))
    leaves = tuple(l for l in cfg.leaves if l not in removed)
    return BNConfig(leaves=leaves, nodes=tuple(nodes), n_states=cfg.n_states, sigma=cfg.sigma,
                    blend=cfg.blend, min_coverage=cfg.min_coverage, priors=cfg.priors)


def _node_n_states(cfg: BNConfig, node_name: str, leaf_set: set) -> int:
    return N_LEAF if node_name in leaf_set else cfg.n_states


def build_cpts(cfg: BNConfig) -> Dict[str, np.ndarray]:
    cfg.validate()
    leaf_set = set(cfg.leaves)
    sizes = {leaf: N_LEAF for leaf in cfg.leaves}
    cpts: Dict[str, np.ndarray] = {}
    for n in cfg.nodes:
        pn = [sizes[p] for p in n.parents]
        w = [1.0 if n.weights is None else float(n.weights.get(p, 0.0)) for p in n.parents]
        cpts[n.name] = build_cpt(pn, w, cfg.sigma, cfg.n_states)
        sizes[n.name] = cfg.n_states
    return cpts


def cpt_table(node: str, cfg: Optional[BNConfig] = None) -> pd.DataFrame:
    """Readable conditional table for one node (so the elicited table can be inspected)."""
    cfg = cfg or BNConfig()
    cpts = build_cpts(cfg)
    spec = next(n for n in cfg.nodes if n.name == node)
    sizes = {leaf: N_LEAF for leaf in cfg.leaves}
    for n in cfg.nodes:
        sizes[n.name] = cfg.n_states
        if n.name == node:
            break
    rows = []
    for combo in itertools.product(*[range(sizes[p]) for p in spec.parents]):
        row = {p: state_names(sizes[p])[s] for p, s in zip(spec.parents, combo)}
        for nm, v in zip(state_names(cfg.n_states), cpts[node][combo]):
            row[f"P({nm})"] = round(float(v), 4)
        rows.append(row)
    return pd.DataFrame(rows)


def _leaf_beliefs(df: pd.DataFrame, leaf: str, cfg: BNConfig) -> Tuple[np.ndarray, np.ndarray]:
    cols = [f"soft_{leaf}_{s}" for s in LEAF_STATES]
    for c in cols + [f"dom_{leaf}_n_used", f"dom_{leaf}_n_total"]:
        if c not in df.columns:
            raise KeyError(f"missing column {c}")
    ev = df[cols].to_numpy(dtype=float)
    n_used = df[f"dom_{leaf}_n_used"].to_numpy(dtype=float)
    n_total = df[f"dom_{leaf}_n_total"].to_numpy(dtype=float)

    has_ev = ~np.isnan(ev).any(axis=1)
    sums = np.where(has_ev, np.nansum(ev, axis=1), 1.0)
    if (np.abs(sums - 1.0) > 1e-6).any():
        raise ValueError(f"soft memberships for {leaf} do not sum to 1")
    if (np.nan_to_num(ev) < -1e-12).any():
        raise ValueError(f"negative soft membership for {leaf}")
    n_used = np.nan_to_num(n_used, nan=0.0)
    n_total = np.nan_to_num(n_total, nan=0.0)
    observed = has_ev & (n_used > 0)

    with np.errstate(divide="ignore", invalid="ignore"):
        cov = np.where(n_total > 0, np.clip(n_used / n_total, 0.0, 1.0), 0.0)
    if cfg.blend == "proportional":
        c = cov
    elif cfg.blend == "none":
        c = np.ones_like(cov)
    else:  # min_coverage
        c = (cov >= cfg.min_coverage).astype(float)
    c = np.where(observed, c, 0.0)

    ev0 = np.nan_to_num(ev, nan=0.0)
    like = c[:, None] * ev0 + (1.0 - c[:, None]) / N_LEAF

    prior = np.full(N_LEAF, 1.0 / N_LEAF)
    if cfg.priors and leaf in cfg.priors:
        prior = np.asarray(cfg.priors[leaf], dtype=float)
        if prior.shape != (N_LEAF,) or (prior < 0).any() or prior.sum() <= 0:
            raise ValueError(f"bad prior for {leaf}")
        prior = prior / prior.sum()
    post = like * prior[None, :]
    return post / post.sum(axis=1, keepdims=True), observed


def _propagate(parent_beliefs: List[np.ndarray], cpt: np.ndarray) -> np.ndarray:
    n = parent_beliefs[0].shape[0]
    out = np.zeros((n, cpt.shape[-1]))
    for combo in itertools.product(*[range(b.shape[1]) for b in parent_beliefs]):
        w = np.ones(n)
        for b, s in zip(parent_beliefs, combo):
            w = w * b[:, s]
        out += w[:, None] * cpt[combo][None, :]
    return out


def score(df: pd.DataFrame, cfg: Optional[BNConfig] = None) -> pd.DataFrame:
    """Score every row. Returns node posteriors, p_high, expected vulnerability, uncertainty."""
    cfg = cfg or BNConfig()
    cfg.validate()
    # label_high_vuln / pc_cons may exist in the frame but are never read.
    cpts = build_cpts(cfg)

    beliefs: Dict[str, np.ndarray] = {}
    observed_flags = []
    for leaf in cfg.leaves:
        b, obs = _leaf_beliefs(df, leaf, cfg)
        beliefs[leaf] = b
        observed_flags.append(obs)
    for n in cfg.nodes:
        beliefs[n.name] = _propagate([beliefs[p] for p in n.parents], cpts[n.name])

    out = pd.DataFrame(index=df.index)
    out["research_label"] = RESEARCH_LABEL
    if "hhcode" in df.columns:
        out["hhcode"] = df["hhcode"].values
    namesN = state_names(cfg.n_states)
    for n in cfg.nodes:
        for nm, j in zip(namesN, range(cfg.n_states)):
            out[f"bn_{n.name}_{nm}"] = beliefs[n.name][:, j]
    v = beliefs["vulnerability"]
    mids = state_midpoints(cfg.n_states)
    out["bn_p_high"] = v[:, -2:].sum(axis=1) if cfg.n_states == 5 else v[:, -1]
    out["bn_expected_vulnerability"] = v @ mids
    with np.errstate(divide="ignore", invalid="ignore"):
        ent = -np.nansum(np.where(v > 0, v * np.log(v), 0.0), axis=1) / math.log(cfg.n_states)
    out["bn_uncertainty_entropy"] = ent
    obs = np.vstack(observed_flags).T
    out["bn_leaves_observed"] = obs.sum(axis=1).astype(int)
    out["bn_leaves_total"] = len(cfg.leaves)
    out["bn_model_version"] = MODEL_VERSION
    out["bn_sigma"] = cfg.sigma
    out["bn_blend"] = cfg.blend
    return out


def score_record(record: Dict[str, float], cfg: Optional[BNConfig] = None) -> pd.Series:
    """Score a single household given as a dict with the same column names as the fuzzy output."""
    return score(pd.DataFrame([record]), cfg).iloc[0]


def rank_agreement(a: pd.Series, b: pd.Series) -> float:
    """Spearman rank correlation between two scorings (for sensitivity comparisons)."""
    return float(pd.concat([a, b], axis=1).dropna().corr(method="spearman").iloc[0, 1])
