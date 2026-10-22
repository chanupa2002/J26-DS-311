"""Minimal Stage 6 agreement, stability and robustness evaluation.

Reads frozen Stage 3/4/5 outputs and writes only beneath outputs/stage6/.
Household-level output is local and covered by the repository's *.csv ignore.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy.stats import kendalltau, rankdata, spearmanr
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "component1_audit"
OUT = ROOT / "outputs" / "stage6"
S4 = PROJECT / "outputs" / "stage4b" / "fuzzy_scores_v0_2.csv"
S5 = PROJECT / "outputs" / "stage5" / "bn_scores_v0_2_interim.csv"
S3 = PROJECT / "outputs" / "stage3" / "modelling_inputs_v0_1.csv"
S3B = PROJECT / "outputs" / "stage3b" / "modelling_inputs_v0_2_additions.csv"
CONTEXT = ROOT / "Data" / "processed" / "hh_context.csv"
BN_DIR = PROJECT / "bn_engine"
FUZZY_DIR = PROJECT / "fuzzy_engine"
LABEL = "Research output - not an eligibility determination"
SEED = 20261022
R_PERTURB = 200
R_MASK = 100
MIN_CELL = 10
METHODS = ("F1", "F0", "B1", "B2", "B3")
MU_COLUMNS = (
    "mu_food", "mu_crowding", "mu_dependency", "mu_income", "mu_assets",
    "mu_tenure", "mu_toilet", "mu_wall", "mu_floor", "mu_roof",
    "mu_bank_account", "mu_has_debt", "mu_health", "mu_shock",
)
FOUR_DOMAINS = {
    "housing": ["mu_wall", "mu_floor", "mu_roof", "mu_toilet", "mu_tenure", "mu_crowding"],
    "economic": ["mu_income", "mu_assets"],
    "food": ["mu_food"],
    "demographic": ["mu_dependency"],
}

sys.path.insert(0, str(BN_DIR))
sys.path.insert(0, str(FUZZY_DIR))
import bn_v0_1 as bn
import fuzzy_v0_1 as fuzzy


def safe_corr(a, b, method="spearman"):
    # Every caller has already aligned rows; use positional pairs even when one
    # argument is a numpy array and the other retains household-key labels.
    a = pd.Series(pd.to_numeric(pd.Series(a), errors="coerce").to_numpy())
    b = pd.Series(pd.to_numeric(pd.Series(b), errors="coerce").to_numpy())
    keep = a.notna() & b.notna()
    if keep.sum() < 2 or a[keep].nunique() < 2 or b[keep].nunique() < 2:
        return np.nan
    fn = spearmanr if method == "spearman" else kendalltau
    return float(fn(a[keep], b[keep]).statistic)


def top_set(values, fraction):
    s = pd.to_numeric(pd.Series(values), errors="coerce")
    valid = np.flatnonzero(s.notna().to_numpy())
    k = int(np.ceil(len(valid) * fraction))
    if not k:
        return set()
    # Stable row-order tie break makes repeated runs deterministic.
    order = valid[np.argsort(-s.iloc[valid].to_numpy(), kind="stable")]
    return set(order[:k].tolist())


def top_k_jaccard(a, b, fraction):
    aa, bb = top_set(a, fraction), top_set(b, fraction)
    union = aa | bb
    return float(len(aa & bb) / len(union)) if union else np.nan


def fix_pca_sign(component, additive):
    """Orient PC1 so larger values agree in direction with additive vulnerability."""
    component = np.asarray(component, dtype=float).copy()
    corr = safe_corr(component, additive)
    if np.isfinite(corr) and corr < 0:
        component *= -1
    return component, corr


def counting_index(mu, domains=FOUR_DOMAINS, threshold=0.5):
    """Equal domain weights; equal indicator weights within domain; unknowns skipped."""
    scores = pd.Series(np.nan, index=mu.index, dtype=float)
    counts = pd.Series(0, index=mu.index, dtype=int)
    domain_values = []
    for cols in domains.values():
        block = mu[cols]
        counts += block.notna().sum(axis=1)
        deprived = block.ge(threshold).where(block.notna())
        domain_values.append(deprived.mean(axis=1, skipna=True))
    dv = pd.concat(domain_values, axis=1)
    scores = dv.mean(axis=1, skipna=True)
    return scores, counts


def mask_known(mu, fraction, rng):
    """Mask exactly round(fraction * known cells); never fills an unknown cell."""
    out = mu.copy()
    flat_original = out.to_numpy(dtype=float).ravel()
    known = np.flatnonzero(np.isfinite(flat_original))
    n_mask = int(round(float(fraction) * len(known)))
    if n_mask:
        chosen = rng.choice(known, size=n_mask, replace=False)
        flat = out.to_numpy(copy=True).ravel()
        flat[chosen] = np.nan
        out.iloc[:, :] = flat.reshape(out.shape)
    return out, n_mask, len(known)


def suppressed(n, min_cell=MIN_CELL):
    return int(n) < int(min_cell)


def weighted_spearman(a, b, weights):
    frame = pd.DataFrame({"a": a, "b": b, "w": weights}).apply(pd.to_numeric, errors="coerce").dropna()
    if len(frame) < 2 or frame.a.nunique() < 2 or frame.b.nunique() < 2 or frame.w.sum() <= 0:
        return np.nan
    ra = rankdata(frame.a, method="average")
    rb = rankdata(frame.b, method="average")
    w = frame.w.to_numpy(float)
    ma, mb = np.average(ra, weights=w), np.average(rb, weights=w)
    cov = np.average((ra-ma)*(rb-mb), weights=w)
    va = np.average((ra-ma)**2, weights=w)
    vb = np.average((rb-mb)**2, weights=w)
    return float(cov / np.sqrt(va * vb)) if va > 0 and vb > 0 else np.nan


def weighted_quantile(values, weights, quantile):
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    keep = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    if not keep.any():
        return np.nan
    order = np.argsort(values[keep], kind="stable")
    v, w = values[keep][order], weights[keep][order]
    return float(v[min(np.searchsorted(np.cumsum(w), quantile*w.sum(), side="left"), len(v)-1)])


def make_f1_inputs(mu):
    """Reconstruct the frozen v0.2 leaves from current Stage 4 input memberships."""
    inputs = mu.copy()
    def mean(cols):
        return inputs[cols].mean(axis=1, skipna=True), inputs[cols].notna().sum(axis=1), len(cols)
    leaf_degrees = {}
    leaf_degrees["shelter_quality"] = mean(["mu_wall", "mu_floor", "mu_roof"])
    leaf_degrees["sanitation"] = (inputs.mu_toilet, inputs.mu_toilet.notna().astype(int), 1)
    leaf_degrees["crowding_tenure"] = mean(["mu_crowding", "mu_tenure"])
    leaf_degrees["food"] = (inputs.mu_food, inputs.mu_food.notna().astype(int), 1)
    leaf_degrees["demographic"] = (inputs.mu_dependency, inputs.mu_dependency.notna().astype(int), 1)
    leaf_degrees["health"] = (inputs.mu_health, inputs.mu_health.notna().astype(int), 1)
    leaf_degrees["economic"] = mean(["mu_income", "mu_assets"])
    leaf_degrees["financial_resilience"] = mean(["mu_bank_account", "mu_has_debt"])
    frame = pd.DataFrame(index=mu.index)
    for leaf, (degree, n_used, n_total) in leaf_degrees.items():
        soft = fuzzy.soft_levels(degree)
        for state in ("low", "medium", "high"):
            frame[f"soft_{leaf}_{state}"] = soft[state]
        frame[f"dom_{leaf}_n_used"] = n_used
        frame[f"dom_{leaf}_n_total"] = n_total
    return frame, leaf_degrees


def score_f1(mu, extra=None, cfg=None):
    frame, leaves = make_f1_inputs(mu)
    result = bn.score(frame, cfg or bn.config_v02_interim())
    return result, leaves


def weighted_cfg(base, rng):
    nodes = []
    for node in base.nodes:
        n = len(node.parents)
        alpha = np.full(n, 20.0 / n)
        draw = rng.dirichlet(alpha)
        nodes.append(bn.NodeSpec(node.name, node.parents, dict(zip(node.parents, draw.tolist()))))
    return bn.BNConfig(leaves=base.leaves, nodes=tuple(nodes), n_states=base.n_states,
                       sigma=base.sigma, blend=base.blend, min_coverage=base.min_coverage,
                       priors=base.priors)


def refitted_memberships(raw, bootstrap_index, midpoint, half_width):
    refs = fuzzy.fit_references(raw.iloc[bootstrap_index])
    values = fuzzy.memberships(raw, refs)
    x = pd.to_numeric(raw.persons_per_bedroom, errors="coerce")
    values["mu_crowding"] = ((x - (midpoint-half_width)) / (2*half_width)).clip(0, 1)
    for col in ("mu_health", "mu_bank_account", "mu_has_debt"):
        values[col] = pd.to_numeric(raw[col], errors="coerce")
    return values


def read_inputs():
    for path in (S4, S5, S3, S3B, CONTEXT):
        if not path.is_file():
            raise FileNotFoundError(f"Required Stage 6 input missing: {path.relative_to(ROOT)}")
    fuzzy_scores = pd.read_csv(S4, dtype={"hhcode": "string"}, low_memory=False).set_index("hhcode")
    stage5 = pd.read_csv(S5, dtype={"hhcode": "string"}, low_memory=False).set_index("hhcode")
    stage3 = pd.read_csv(S3, dtype={"hhcode": "string"}, low_memory=False).set_index("hhcode")
    additions = pd.read_csv(S3B, dtype={"hhcode": "string"}, low_memory=False).set_index("hhcode")
    context = pd.read_csv(CONTEXT, dtype={"hhcode": "string"}, low_memory=False).set_index("hhcode")
    frames = {"stage4b": fuzzy_scores, "stage5": stage5, "stage3": stage3,
              "stage3b": additions, "context": context}
    for name, frame in frames.items():
        if frame.index.isna().any() or frame.index.has_duplicates:
            raise ValueError(f"{name} does not have unique nonmissing household keys")
    reference = fuzzy_scores.index
    if any(set(frame.index) != set(reference) for frame in frames.values()):
        raise ValueError("Stage 3, Stage 3b, Stage 4b, Stage 5 and proxy/context keys are not aligned")
    stage3 = stage3.reindex(reference)
    additions = additions.reindex(reference)
    context = context.reindex(reference)
    raw = pd.DataFrame(index=reference)
    raw["fies_raw_score"] = stage3.fies_raw_score
    raw["persons_per_bedroom"] = stage3.persons_per_bedroom
    raw["dependency_ratio"] = stage3.dependency_ratio
    raw["no_working_age_member"] = stage3.no_working_age_member
    raw["income_value"] = stage3.h1_17_raw_household_value
    raw["asset_types_owned_n"] = stage3.asset_types_owned_n
    raw["asset_items_valid_n"] = stage3.asset_items_valid_n
    raw["tenure_class"] = stage3.tenure_class
    raw["toilet_service_class"] = stage3.toilet_service_class
    raw["wall_durability"] = stage3.c1_04_durability_class
    raw["floor_durability"] = stage3.c1_05_durability_class
    raw["roof_durability"] = stage3.c1_06_durability_class
    for c in ("mu_bank_account", "mu_has_debt", "mu_health"):
        raw[c] = pd.to_numeric(fuzzy_scores[c], errors="coerce")
    mu_cols = list(MU_COLUMNS)
    mu = fuzzy_scores.reindex(columns=mu_cols).apply(pd.to_numeric, errors="coerce")
    # Bank, debt and health are Stage 3b v0.2 inputs; use exact published memberships.
    for c in ("mu_bank_account", "mu_has_debt", "mu_health"):
        mu[c] = pd.to_numeric(fuzzy_scores[c], errors="coerce")
    return frames, fuzzy_scores, stage5.reindex(reference), stage3, additions, context, raw, mu


def scored_methods(mu, stage4, stage5, extra):
    output = pd.DataFrame(index=mu.index)
    output["F1"] = pd.to_numeric(stage5.bn_expected_vulnerability, errors="coerce")
    output["F1_p_high"] = pd.to_numeric(stage5.bn_p_high, errors="coerce")
    output["F1_uncertainty"] = pd.to_numeric(stage5.bn_uncertainty_entropy, errors="coerce")
    four = pd.DataFrame({
        "housing": stage4.dom_housing,
        "economic": stage4.dom_economic,
        "food": stage4.dom_food,
        "demographic": stage4.dom_demographic,
    }, index=mu.index).apply(pd.to_numeric, errors="coerce")
    output["F0"] = four.mean(axis=1, skipna=True)
    output["F0_evidence_n_used"] = four.notna().sum(axis=1)
    output["B1"] = mu.mean(axis=1, skipna=True)
    output["B1_evidence_n_used"] = mu.notna().sum(axis=1)
    complete = mu.notna().all(axis=1)
    pc1 = pd.Series(np.nan, index=mu.index, dtype=float)
    loadings = pd.DataFrame()
    variance = np.nan
    sign_corr = np.nan
    if complete.sum() >= 2:
        scaler = StandardScaler()
        standardized = scaler.fit_transform(mu.loc[complete])
        pca = PCA(n_components=1, svd_solver="full")
        component = pca.fit_transform(standardized).ravel()
        component, sign_corr = fix_pca_sign(component, output.loc[complete, "B1"])
        pc1.loc[complete] = component
        variance = float(pca.explained_variance_ratio_[0])
        loadings = pd.DataFrame({"input": mu.columns, "loading": pca.components_[0] * (1 if sign_corr >= 0 else -1)})
    output["B2"] = pc1
    output["B2_complete_case"] = complete
    output["B3"], output["B3_evidence_n_used"] = counting_index(mu, threshold=.5)
    output["B3_t50"] = output["B3"]
    for threshold in (.4, .6):
        output[f"B3_t{int(threshold*100)}"], _ = counting_index(mu, threshold=threshold)
    output["F1_rank_percentile"] = output.F1.rank(method="average", pct=True) * 100
    output["F1_evidence_n_used"] = pd.to_numeric(stage5.bn_leaves_observed, errors="coerce")
    output["F1_evidence_n_total"] = pd.to_numeric(stage5.bn_leaves_total, errors="coerce")
    output["F0_evidence_n_total"] = 4
    output["B1_evidence_n_total"] = mu.shape[1]
    output["B2_evidence_n_used"] = mu.notna().sum(axis=1)
    output["B2_evidence_n_total"] = mu.shape[1]
    output["B3_evidence_n_total"] = sum(len(cols) for cols in FOUR_DOMAINS.values())
    return output, four, {"pca_loadings": loadings, "pca_variance_explained": variance,
                          "pca_sign_correlation_with_B1": sign_corr, "pca_complete_n": int(complete.sum())}


def tie_stats(values):
    s = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    counts = s.value_counts()
    tied_values = counts[counts > 1]
    return int(len(tied_values)), int(tied_values.sum()), float(tied_values.sum()/len(s)) if len(s) else np.nan


def distribution_table(scores):
    rows = []
    for method in METHODS:
        s = pd.to_numeric(scores[method], errors="coerce")
        valid = s.dropna()
        nties, tied_hh, tie_share = tie_stats(s)
        rows.append({"method": method, "n_scored": int(len(valid)), "coverage_share": float(len(valid)/len(s)),
                     "mean": valid.mean(), "sd": valid.std(), "min": valid.min(), "q05": valid.quantile(.05),
                     "q25": valid.quantile(.25), "median": valid.median(), "q75": valid.quantile(.75),
                     "q95": valid.quantile(.95), "max": valid.max(), "tied_score_values_n": nties,
                     "households_in_ties_n": tied_hh, "tie_share": tie_share})
    return pd.DataFrame(rows)


def pair_metrics(scores):
    rows = []
    for i, a in enumerate(METHODS):
        for b in METHODS[i+1:]:
            pair = scores[[a, b]].dropna()
            row = {"method_a": a, "method_b": b, "n_common": len(pair),
                   "spearman": safe_corr(pair[a], pair[b], "spearman"),
                   "kendall_tau": safe_corr(pair[a], pair[b], "kendall")}
            for pct in (.10, .20, .30):
                row[f"top_{int(pct*100)}_jaccard"] = top_k_jaccard(pair[a], pair[b], pct)
            rows.append(row)
    return pd.DataFrame(rows)


def perturbation(mu, raw, baseline, rng):
    n = len(mu)
    ranks = np.zeros((R_PERTURB, n), dtype=np.float32)
    rho_rows, retention_rows = [], []
    base_top = top_set(baseline.F1, .10)
    cfg0 = bn.config_v02_interim()
    for replicate in range(R_PERTURB):
        midpoint = rng.uniform(2.5, 4.0)
        half_width = rng.uniform(.5, 1.5)
        bootstrap = rng.integers(0, n, size=n)
        varied_mu = refitted_memberships(raw, bootstrap, midpoint, half_width)
        cfg = weighted_cfg(cfg0, rng)
        scored, _ = score_f1(varied_mu, raw, cfg)
        values = scored.bn_expected_vulnerability.to_numpy(float)
        ranks[replicate] = rankdata(-values, method="average").astype(np.float32)
        rho_rows.append(safe_corr(baseline.F1, values))
        varied_top = top_set(values, .10)
        retention_rows.append(len(base_top & varied_top) / max(len(base_top), 1))
    interval = pd.DataFrame({"F1_rank_p05": np.quantile(ranks, .05, axis=0),
                             "F1_rank_p50": np.quantile(ranks, .50, axis=0),
                             "F1_rank_p95": np.quantile(ranks, .95, axis=0)}, index=baseline.index)
    interval["F1_rank_interval_width"] = interval.F1_rank_p95 - interval.F1_rank_p05
    summary = pd.DataFrame([{
        "replicates": R_PERTURB, "spearman_mean": np.nanmean(rho_rows), "spearman_sd": np.nanstd(rho_rows),
        "spearman_p05": np.nanquantile(rho_rows, .05), "spearman_median": np.nanmedian(rho_rows),
        "spearman_p95": np.nanquantile(rho_rows, .95), "top_decile_retention_mean": np.mean(retention_rows),
        "top_decile_retention_p05": np.quantile(retention_rows, .05),
        "top_decile_retention_p95": np.quantile(retention_rows, .95),
    }])
    return interval, summary


def mask_stress(mu, raw, baseline, rng):
    rows = []
    rates = (.10, .20, .30)
    for rate in rates:
        rho = {m: [] for m in ("F1", "F0", "B1", "B3")}
        retain = {m: [] for m in ("F1", "F0", "B1", "B3")}
        masked_counts = {m: [] for m in rho}
        for _ in range(R_MASK):
            subsets = {"F1": mu.drop(columns=["mu_shock"]),
                       "F0": mu[list(dict.fromkeys(c for cols in FOUR_DOMAINS.values() for c in cols))],
                       "B1": mu,
                       "B3": mu[list(dict.fromkeys(c for cols in FOUR_DOMAINS.values() for c in cols))]}
            masked_inputs = {}
            for method, inputs in subsets.items():
                masked_inputs[method], n_mask, n_known = mask_known(inputs, rate, rng)
                masked_counts[method].append((n_mask, n_known))
            f1, _ = score_f1(masked_inputs["F1"].reindex(columns=mu.columns, fill_value=np.nan), raw)
            f0m = masked_inputs["F0"]
            f0 = pd.DataFrame({k: f0m[v].mean(axis=1, skipna=True) for k, v in FOUR_DOMAINS.items()}, index=f0m.index).mean(axis=1, skipna=True)
            b1 = masked_inputs["B1"].mean(axis=1, skipna=True)
            b3, _ = counting_index(masked_inputs["B3"], threshold=.5)
            candidates = {"F1": f1.bn_expected_vulnerability, "F0": f0, "B1": b1, "B3": b3}
            for method, values in candidates.items():
                rho[method].append(safe_corr(baseline[method], values))
                base_top = top_set(baseline[method], .10)
                new_top = top_set(values, .10)
                retain[method].append(len(base_top & new_top)/max(len(base_top), 1))
        for method in rho:
            rows.append({"method": method, "masked_fraction": rate, "replicates": R_MASK,
                         "mean_cells_masked": float(np.mean([x[0] for x in masked_counts[method]])),
                         "mean_known_cells_before_mask": float(np.mean([x[1] for x in masked_counts[method]])),
                         "actual_mask_fraction": float(np.mean([x[0]/x[1] if x[1] else np.nan for x in masked_counts[method]])),
                         "spearman_mean": float(np.nanmean(rho[method])), "spearman_sd": float(np.nanstd(rho[method])),
                         "top_decile_retention_mean": float(np.mean(retain[method])),
                         "top_decile_retention_sd": float(np.std(retain[method]))})
    return pd.DataFrame(rows)


def uncertainty_evidence(stage5):
    evidence = pd.to_numeric(stage5.bn_leaves_observed, errors="coerce")
    rows = []
    for metric, values in (("expected_vulnerability", stage5.bn_expected_vulnerability),
                           ("posterior_entropy", stage5.bn_uncertainty_entropy)):
        rows.append({"relationship": "available BN leaves vs " + metric, "n": int(evidence.notna().sum()),
                     "spearman": safe_corr(evidence, values), "kendall_tau": safe_corr(evidence, values, "kendall"),
                     "direction": "higher evidence associated with higher value" if safe_corr(evidence, values) > 0 else "higher evidence associated with lower value" if safe_corr(evidence, values) < 0 else "no monotone association detected"})
    group = pd.DataFrame({"available_leaves": evidence, "expected_vulnerability": stage5.bn_expected_vulnerability,
                          "posterior_entropy": stage5.bn_uncertainty_entropy}).groupby("available_leaves", dropna=False).agg(
                              households_n=("expected_vulnerability", "size"), mean_expected_vulnerability=("expected_vulnerability", "mean"),
                              mean_posterior_entropy=("posterior_entropy", "mean")).reset_index()
    return pd.DataFrame(rows), group


def subgroup_tables(scores, context, intervals):
    rows = []
    base = scores[["F1", "B1"]].join(intervals["F1_rank_interval_width"]).join(context[["a_01_province", "a_02_district", "sector", "hhweight"]])
    base["unknown_input_share"] = 1.0 - scores["B1_evidence_n_used"] / scores["B1_evidence_n_total"]
    for field in ("a_01_province", "a_02_district", "sector"):
        for value, group in base.groupby(field, dropna=False, sort=True):
            n = len(group)
            label = "Unknown" if pd.isna(value) else str(value)
            if suppressed(n):
                rows.append({"subgroup_field": field, "subgroup": label, "weighting": "sample", "households_n": n, "suppressed": True})
                continue
            rows.append({"subgroup_field": field, "subgroup": label, "weighting": "sample", "households_n": n, "suppressed": False,
                         "mean_F1": group.F1.mean(), "q25_F1": group.F1.quantile(.25), "median_F1": group.F1.median(),
                         "q75_F1": group.F1.quantile(.75), "mean_B1": group.B1.mean(),
                         "unknown_input_share": group.unknown_input_share.mean(),
                         "mean_rank_interval_width": group.F1_rank_interval_width.mean(),
                         "F1_B1_spearman": safe_corr(group.F1, group.B1)})
            w = pd.to_numeric(group.hhweight, errors="coerce")
            valid = w.notna() & (w > 0)
            if valid.sum() >= MIN_CELL:
                g = group.loc[valid]
                ww = w[valid]
                rows.append({"subgroup_field": field, "subgroup": label, "weighting": "weighted", "households_n": int(valid.sum()), "suppressed": False,
                             "mean_F1": np.average(g.F1, weights=ww), "q25_F1": weighted_quantile(g.F1, ww, .25),
                             "median_F1": weighted_quantile(g.F1, ww, .5), "q75_F1": weighted_quantile(g.F1, ww, .75),
                             "mean_B1": np.average(g.B1, weights=ww),
                             "unknown_input_share": np.average(g.unknown_input_share, weights=ww),
                             "mean_rank_interval_width": np.average(g.F1_rank_interval_width, weights=ww),
                             "F1_B1_spearman": weighted_spearman(g.F1, g.B1, ww)})
            else:
                rows.append({"subgroup_field": field, "subgroup": label, "weighting": "weighted", "households_n": int(valid.sum()), "suppressed": True})
    return pd.DataFrame(rows)


def proxy_metrics(scores, context):
    rows = []
    from sklearn.metrics import roc_auc_score
    label = pd.to_numeric(context.label_high_vuln, errors="coerce")
    pc_cons = pd.to_numeric(context.pc_cons, errors="coerce")
    for method in METHODS:
        s = pd.to_numeric(scores[method], errors="coerce")
        n_pc = s.notna() & pc_cons.notna()
        n_label = s.notna() & label.isin([0, 1])
        y = label[n_label].astype(int)
        auc = roc_auc_score(y, s[n_label]) if y.nunique() == 2 else np.nan
        top = top_set(s, .10)
        valid_ids = pd.Series(np.arange(len(s)), index=s.index)
        top_ids = set(s.iloc[list(top)].index) if top else set()
        pos_total = int(label[n_label].sum())
        pos_in_top = int(label.reindex(list(top_ids)).fillna(0).sum())
        rows.append({"method": method, "pc_cons_spearman": safe_corr(s[n_pc], pc_cons[n_pc]), "pc_cons_n": int(n_pc.sum()),
                     "label_auc_descriptive": auc, "label_n": int(n_label.sum()),
                     "label_positive_n": pos_total, "top_decile_proxy_capture": pos_in_top/pos_total if pos_total else np.nan})
    return pd.DataFrame(rows)


def write_csv(frame, path):
    frame = frame.copy()
    frame.insert(0, "research_label", LABEL)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, na_rep="")


def write_figures(scores, agreement, intervals, masking, subgroup):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4), constrained_layout=True)
    labels = list(METHODS)
    for ax, metric, title, lo, hi in (
        (axes[0], "spearman", "Spearman agreement", -1, 1),
        (axes[1], "kendall_tau", "Kendall tau agreement", -1, 1),
        (axes[2], "top_10_jaccard", "Top-decile Jaccard overlap", 0, 1),
    ):
        matrix = np.eye(len(labels))
        for _, row in agreement.iterrows():
            i, j = labels.index(row.method_a), labels.index(row.method_b)
            matrix[i, j] = matrix[j, i] = row[metric]
        image = ax.imshow(matrix, vmin=lo, vmax=hi, cmap="coolwarm" if lo < 0 else "viridis")
        ax.set_xticks(range(len(labels)), labels); ax.set_yticks(range(len(labels)), labels)
        ax.set_title(title); fig.colorbar(image, ax=ax, fraction=.046, pad=.04)
        for i in range(len(labels)):
            for j in range(len(labels)):
                ax.text(j, i, f"{matrix[i,j]:.2f}", ha="center", va="center", fontsize=8)
    fig.suptitle("Method agreement")
    fig.text(.5, .001, LABEL, ha="center", fontsize=8)
    fig.savefig(OUT / "figures" / "method_agreement_heatmap.png", dpi=160); plt.close(fig)

    rng = np.random.default_rng(SEED + 2)
    decile = pd.qcut(scores.F1.rank(method="first"), 10, labels=False)
    sample = []
    for group_id in range(10):
        indices = np.flatnonzero((decile == group_id).to_numpy())
        sample.extend(rng.choice(indices, size=min(20, len(indices)), replace=False).tolist())
    sample = np.asarray(sample, dtype=int)
    fig, ax = plt.subplots(figsize=(12, 5), constrained_layout=True)
    ax.vlines(np.arange(len(sample)), intervals.F1_rank_p05.iloc[sample], intervals.F1_rank_p95.iloc[sample], color="#4361a5", alpha=.55, linewidth=1)
    ax.scatter(np.arange(len(sample)), intervals.F1_rank_p50.iloc[sample], s=8, color="#172554")
    ax.set(title="F1 rank intervals for a stratified sample", xlabel="Sampled households (grouped by baseline decile; IDs omitted)", ylabel="Rank (1 = highest expected vulnerability)")
    fig.text(.5, .001, LABEL, ha="center", fontsize=8)
    fig.savefig(OUT / "figures" / "rank_intervals_stratified_sample.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    for method, group in masking.groupby("method"):
        ax.plot(group.masked_fraction * 100, group.spearman_mean, marker="o", label=method)
    ax.set(title="Missing-evidence stress: rank agreement with unmasked scores", xlabel="Known input values masked (%)", ylabel="Mean Spearman across replicates", ylim=(-1, 1)); ax.legend()
    fig.text(.5, .001, LABEL, ha="center", fontsize=8)
    fig.savefig(OUT / "figures" / "masking_curve.png", dpi=160); plt.close(fig)

    for field, fname, title in (("a_01_province", "province", "province"), ("a_02_district", "district", "district"), ("sector", "sector", "stored sector code")):
        usable = subgroup[(subgroup.subgroup_field == field) & (subgroup.weighting == "sample") & (~subgroup.suppressed.fillna(False))]
        fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
        ax.bar(usable.subgroup, usable.mean_F1, color="#4361a5")
        ax.set(title=f"F1 mean by {title} (sample; MIN_CELL applied)", xlabel=f"{title} code", ylabel="Mean expected vulnerability")
        fig.text(.5, .001, LABEL, ha="center", fontsize=8)
        fig.savefig(OUT / "figures" / f"subgroup_{fname}_F1.png", dpi=160); plt.close(fig)


def describe_inputs(frames, runtime):
    stage5 = frames["stage5"]
    stage4 = frames["stage4b"]
    cols = ", ".join(stage5.columns)
    return f"""# Stage 6 inputs audit

{LABEL}

## Frozen inputs and alignment

- Stage 5 score file: `component1_audit/outputs/stage5/bn_scores_v0_2_interim.csv`.
- Stage 4b memberships: `component1_audit/outputs/stage4b/fuzzy_scores_v0_2.csv`.
- Both tables contain {len(stage5):,} rows, unique nonmissing household keys, and identical key sets. Stage 3 and Stage 3b modelling inputs plus prepared context also passed one-to-one key-set alignment.
- Stage 5 columns include expected vulnerability (`bn_expected_vulnerability`), posterior high probability (`bn_p_high`), and normalized posterior entropy (`bn_uncertainty_entropy`). It does not store a rank percentile or a rank interval. The percentile is derived from the saved expected scores; rank intervals are calculated in Stage 6 perturbations.
- Stage 5 runner: `component1_audit/outputs/stage5/build_stage5.py` calls `bn_v0_1.score(network, config_v02_interim())` over the full table. The single-record interface is `bn_v0_1.score_record(record, cfg)`. A 200-call synthetic one-record benchmark averaged {runtime:.6f} seconds per call on this machine; this is an engine microbenchmark, not a full-pipeline or household-specific timing.
- Stage 5 summary describes 6,847 baseline households. It reports expected vulnerability, P(high), entropy, and aggregate sensitivity outputs. No interval is stored in the Stage 5 score file.

## Proxy documentation and circularity

- Existing data-quality and proposed-resolution notes document `pc_cons` as `total_month / hh_size`; the component construction upstream of `total_month` is not fully reproducible from available source documentation.
- `label_high_vuln` is documented as a household-weighted bottom-quintile indicator of `pc_cons`, with approximate weighted prevalence 0.20. It is a descriptive sensitivity proxy.
- Stage 3, Stage 4b and Stage 5 explicitly exclude both proxy fields from the model-input/scoring tables. Exact overlap between proxy construction components and income/asset features is not fully documented; consumption and economic-capacity features may be related, so proxy agreement is potentially circular and is kept in its own folder.

## Subgroup fields

- Prepared context provides province code, district code, `sector`, and `hhweight`. The codebook also confirms `hhweight` exists.
- Stage 5 scores themselves contain `hhcode` and network scores; subgroup fields are joined from the prepared context for aggregate analysis only. `sector` is reported by its stored code; urban/rural/estate meanings are not assumed.
- Household identifiers are used only in the ignored local score output and are not printed in logs, reports, or figures.

## Input columns

- Stage 5: {cols}
- Stage 4b includes {len(stage4.columns)} columns, including the `mu_*` membership fields and `dom_*` coverage fields used by the frozen framework and baselines.
"""


def run():
    started = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "figures").mkdir(exist_ok=True)
    (OUT / "proxy_reference").mkdir(exist_ok=True)
    frames, stage4, stage5, stage3, additions, context, raw, mu = read_inputs()
    cfg = bn.config_v02_interim()
    synthetic = {}
    for leaf in cfg.leaves:
        synthetic.update({f"soft_{leaf}_{state}": value for state, value in zip(("low", "medium", "high"), (.2, .5, .3))})
        synthetic[f"dom_{leaf}_n_used"] = 1.0; synthetic[f"dom_{leaf}_n_total"] = 1.0
    t0 = time.perf_counter()
    for _ in range(200):
        bn.score_record(synthetic, cfg)
    runtime = (time.perf_counter() - t0) / 200

    rebuilt_f1, _ = score_f1(mu)
    baseline_rebuild_error = float(np.nanmax(np.abs(rebuilt_f1.bn_expected_vulnerability.to_numpy() - stage5.bn_expected_vulnerability.to_numpy())))
    if baseline_rebuild_error > 1e-8:
        raise ValueError(f"Stage 4b inputs did not reproduce the frozen Stage 5 baseline (max difference {baseline_rebuild_error:.3g})")
    scores, _, pca_info = scored_methods(mu, stage4, stage5, raw)
    scores.insert(0, "hhcode", mu.index)
    baseline = scores.set_index("hhcode")
    rng_perturb = np.random.default_rng(SEED)
    intervals, m2 = perturbation(mu, raw, baseline, rng_perturb)
    scores = scores.join(intervals)
    baseline = baseline.join(intervals)

    m1 = pair_metrics(baseline)
    dist = distribution_table(baseline)
    tie_rows = dist[["method", "tied_score_values_n", "households_in_ties_n", "tie_share", "n_scored"]].copy()
    tie_rows["research_label"] = LABEL

    rng_mask = np.random.default_rng(SEED + 1)
    m3 = mask_stress(mu, raw, baseline, rng_mask)
    m4, evidence_bands = uncertainty_evidence(stage5)
    subgroups = subgroup_tables(baseline, context, intervals)
    proxy = proxy_metrics(baseline, context)

    b3_thresholds = []
    for threshold in (.4, .5, .6):
        score = baseline[f"B3_t{int(threshold*100)}"]
        b3_thresholds.append({"deprivation_threshold": threshold, "share_score_at_or_above_1_3": float((score >= 1/3).mean()),
                              "share_score_at_or_above_1_2": float((score >= .5).mean()), "n_scored": int(score.notna().sum())})
    pca_loadings = pca_info.pop("pca_loadings")

    write_csv(scores.reset_index(drop=True), OUT / "scores_all_methods.csv")
    write_csv(m1, OUT / "m1_method_agreement.csv")
    write_csv(dist, OUT / "method_score_distributions.csv")
    write_csv(tie_rows.drop(columns="research_label"), OUT / "m6_ties_resolution.csv")
    write_csv(m2, OUT / "m2_perturbation_stability.csv")
    interval_output = intervals.reset_index().rename(columns={"index": "hhcode"})
    write_csv(interval_output, OUT / "m2_household_rank_intervals.csv")
    write_csv(m3, OUT / "m3_missing_evidence_stress.csv")
    write_csv(m4, OUT / "m4_uncertainty_evidence.csv")
    write_csv(evidence_bands, OUT / "m4_evidence_bands.csv")
    write_csv(subgroups, OUT / "m5_subgroups.csv")
    write_csv(pd.DataFrame(b3_thresholds), OUT / "b3_threshold_sensitivity.csv")
    write_csv(pca_loadings, OUT / "pca_loadings.csv")
    proxy_dir = OUT / "proxy_reference"
    write_csv(proxy, proxy_dir / "proxy_agreement.csv")
    (proxy_dir / "README.md").write_text(f"""# Separate descriptive sensitivity proxy — NOT ground truth

{LABEL}

This table reports rank association with `pc_cons` and descriptive AUC/top-decile capture for `label_high_vuln`. No method was tuned on either proxy. The label is a weighted bottom-quintile classification derived from `pc_cons`; proxy construction may overlap with economic features. Do not use this folder as a headline result or as a statement of validation.
""", encoding="utf-8")
    write_figures(baseline, m1, intervals.reset_index(drop=True), m3, subgroups)

    stage5_hash = hashlib.sha256(S5.read_bytes()).hexdigest()
    stage4_hash = hashlib.sha256(S4.read_bytes()).hexdigest()
    input_paths = [S4, S5, S3, S3B, CONTEXT, BN_DIR / "bn_v0_1.py", FUZZY_DIR / "fuzzy_v0_1.py"]
    manifest = {
        "research_label": LABEL, "stage": 6, "model_unchanged": True,
        "stage5_pipeline": "stage5-v0.2.0", "bn_model": bn.MODEL_VERSION,
        "fuzzy_model": fuzzy.MODEL_VERSION, "seed": SEED,
        "seeds": {"perturbation": SEED, "missingness": SEED+1, "rank_plot_sample": SEED+2},
        "replicates": {"perturbation": R_PERTURB, "missingness_per_fraction": R_MASK},
        "parameters": {"MIN_CELL": MIN_CELL, "B3_threshold_primary": .5, "B3_threshold_sensitivity": [.4, .6],
                       "mask_rates": [.1, .2, .3], "crowding_midpoint_range": [2.5, 4.0],
                       "crowding_half_width_range": [.5, 1.5], "dirichlet_total_concentration": 20},
        "alignment_n": len(stage5), "stage4_sha256": stage4_hash, "stage5_sha256": stage5_hash,
        "runtime_synthetic_score_record_mean_seconds": runtime,
        "baseline_rebuild_max_abs_difference": baseline_rebuild_error,
        "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__,
        "input_hashes": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in input_paths},
    }
    (OUT / "stage6_inputs_audit.md").write_text(describe_inputs(frames, runtime), encoding="utf-8")
    open_questions = f"""# Stage 6 open questions

{LABEL}

- Confirm `MIN_CELL=10` with the researcher; it is applied to every subgroup statistic.
- B3 thresholds 0.4, 0.5 and 0.6 are researcher-judgement settings, not an official MPI. The primary reporting threshold is 0.5; 0.4 and 0.6 are sensitivity views.
- B3 uses the four Stage 4 domains (housing, economic, food, demographic). The newer Stage 4b health, financial-resilience and exposure indicators do not have a single approved mapping into these four legacy domains; they are not silently assigned in B3. B1 includes every published `mu_*` field, including `mu_shock`, as specified by the task.
- The perturbation applies one Dirichlet(20 x equal weights) draw to each exposed BN node-parent weight vector. There is no separately named “domain weight” field in the engine; this interpretation perturbs each domain aggregation weight vector exposed by the BN configuration.
- `pc_cons` is documented as `total_month / hh_size`; exact upstream consumption components are not fully documented. `label_high_vuln` is the weighted bottom quintile of `pc_cons`. Their association with economic inputs may be circular; results remain isolated and descriptive.
- The `sector` values are reported by stored code because current source documentation does not establish urban/rural/estate labels.
- Stage 5 stores no percentile or interval. Percentile is derived from its expected score; perturbation intervals are new Stage 6 rank stability summaries, not uncertainty intervals from a calibrated model.
- PCA is complete-case only and may cover fewer households than other methods; missing memberships are not imputed.
"""
    (OUT / "open_questions.md").write_text(open_questions, encoding="utf-8")
    report = make_report(scores, m1, dist, m2, m3, m4, subgroups, proxy, pca_info, b3_thresholds, runtime)
    (OUT / "stage6_evaluation_report.md").write_text(report, encoding="utf-8")
    (OUT / "stage6_summary.md").write_text(make_summary(m1, m2, m3, dist), encoding="utf-8")
    manifest["output_hashes"] = {}
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            manifest["output_hashes"][str(path.relative_to(OUT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    elapsed = time.perf_counter() - started
    print(f"{LABEL}; completed Stage 6 on {len(scores):,} aligned records in {elapsed:.1f}s; household identifiers were not printed.")


def md_table(frame, columns=None, max_rows=25):
    f = frame if columns is None else frame[columns]
    f = f.head(max_rows)
    headers = [str(c) for c in f.columns]
    rows = []
    for values in f.itertuples(index=False, name=None):
        rows.append([f"{v:.3f}" if isinstance(v, (float, np.floating)) and np.isfinite(v) else "Unavailable" if isinstance(v, (float, np.floating)) else str(v) for v in values])
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(len(headers))]
    line = lambda row: "| " + " | ".join(value.ljust(widths[i]) for i, value in enumerate(row)) + " |"
    return "\n".join([line(headers), "| " + " | ".join("-"*w for w in widths) + " |", *(line(row) for row in rows)])


def make_report(scores, m1, dist, m2, m3, m4, subgroups, proxy, pca_info, b3_thresholds, runtime):
    favorable = m1.sort_values("spearman", ascending=False).head(5)
    unfavorable = m1.sort_values("spearman", ascending=True).head(5)
    return f"""# Stage 6 evaluation report

{LABEL}

## Purpose and design

This is a comparative agreement, ranking-stability and missing-evidence robustness study. There is no independent outcome reference. No method is calibrated or selected using the proxy fields. The fuzzy rules, BN structure, tables, baseline outputs, and approved specification were read-only. No eligibility interpretation is supported.

The Stage 4b and Stage 5 inputs aligned on {len(scores):,} unique household keys. The Stage 5 network score itself does not store a percentile; F1 percentile is derived from the expected-vulnerability ranking. A 200-call synthetic `score_record` benchmark averaged {runtime:.6f} seconds per call.

## Methods compared

- **F1:** current v0.2 interim Bayesian framework expected vulnerability (primary); P(high) reported separately.
- **F0:** equal-weight available-case mean of the four Stage 4 domain degrees.
- **B1:** available-case unweighted mean of all 14 Stage 4b `mu_*` memberships, including the published exposure membership.
- **B2:** first principal component of standardized Stage 4b memberships, complete cases only; sign oriented to agree with B1. Complete-case coverage: {pca_info['pca_complete_n']:,}; variance explained: {pca_info['pca_variance_explained']:.3f}; pre-orientation PC1/B1 correlation: {pca_info['pca_sign_correlation_with_B1']:.3f}.
- **B3:** equal-weight four-domain counting score, within-domain equal indicator weights, deprivation threshold 0.5, and available-indicator rescaling. It is a transparent counting baseline, not the official MPI. Threshold sensitivities at 0.4 and 0.6 are in `b3_threshold_sensitivity.csv`.

All scores are oriented higher = more vulnerable. Coverage, tie resolution, and distributions are reported in `method_score_distributions.csv` and `m6_ties_resolution.csv`.

## Results per metric

### M1 — Agreement between methods

Spearman, Kendall tau, and top-10/20/30% Jaccard are in `m1_method_agreement.csv`; heatmaps are in `figures/method_agreement_heatmap.png`.

Highest five pairwise Spearman values:

{md_table(favorable, ['method_a','method_b','n_common','spearman','kendall_tau','top_10_jaccard'])}

Lowest five pairwise Spearman values are also shown to give less-aligned results equal prominence:

{md_table(unfavorable, ['method_a','method_b','n_common','spearman','kendall_tau','top_10_jaccard'])}

### M2 — Perturbation stability of F1

Ran {R_PERTURB} replicates with crowding midpoint U(2.5, 4.0), half-width U(0.5, 1.5), bootstrap-refitted income/assets/dependency TFR references, and independent Dirichlet weight draws for each exposed BN node-parent vector. Network input weights are exposed and were perturbed. Per-household rank p05/p50/p95 and interval width are stored in the ignored local `scores_all_methods.csv` and `m2_household_rank_intervals.csv`. Stratified sample plot: `figures/rank_intervals_stratified_sample.png`.

{md_table(m2)}

### M3 — Missing-evidence stress

For F1, F0, B1, and B3, {R_MASK} replicates at each rate mask exactly the rounded requested fraction of known membership cells completely at random. Unknown values remain unknown. Results report Spearman against each method's unmasked score and top-decile retention; curve: `figures/masking_curve.png`.

{md_table(m3, ['method','masked_fraction','replicates','spearman_mean','top_decile_retention_mean'])}

### M4 — Evidence and uncertainty relationship

Evidence count is the number of observed BN leaves. Uncertainty is Stage 5 normalized posterior entropy; no posterior interval is provided. Associations are descriptive and do not establish that changing evidence causes score changes.

{md_table(m4)}

### M5 — Subgroup behaviour

Province, district, and stored sector-code summaries include sample and `hhweight`-weighted views. Statistics for cells below MIN_CELL=10 are suppressed. See `m5_subgroups.csv`; a province sample plot is `figures/subgroup_province_F1.png`. Weighted rank agreement uses weighted Pearson correlation of within-subgroup midranks.

### M6 — Tie and resolution check

Counts and share of households in tied score groups are in `m6_ties_resolution.csv`.

## Where F1 has higher and lower agreement/stability

The pairwise results above show both closer and weaker agreement between F1 and baselines; interpret the complete table, not only the strongest comparisons. Perturbation stability and missing-evidence degradation are reported alongside the baselines. No method is described as accurate or validated.

## Separate descriptive sensitivity proxy

Proxy agreement is isolated in `proxy_reference/` and includes all methods. `label_high_vuln` is the weighted bottom-quintile classification of `pc_cons`; `pc_cons` is documented as `total_month / hh_size`. Exact upstream consumption construction is incomplete. Economic inputs may overlap conceptually or through source components. These are descriptive sensitivity comparisons, not independent outcome measurements and not headline findings.

## Limitations

- No independent outcome data exist; calibration and outcome validation are not performed.
- The interim D-03a shelter-material rule remains a limitation.
- BN conditional tables are expert-set research tables.
- FIES form comparability remains pending.
- Inputs are missing for some households; no missing value was imputed.
- Baseline estimates are research composites and are not eligibility determinations.

## Appendix: parameters and seeds

Seeds: perturbation {SEED}; missingness {SEED+1}; stratified figure sample {SEED+2}. Replicates: perturbation {R_PERTURB}; missingness {R_MASK} per rate. MIN_CELL={MIN_CELL}. B3 threshold 0.5 primary, with 0.4/0.6 sensitivity. Full hashes and package versions are in `manifest.json`; unresolved choices are listed in `open_questions.md`.
"""


def make_summary(m1, m2, m3, dist):
    return f"""# Stage 6 summary

{LABEL}

## Scope

Compared the frozen v0.2 framework with four transparent baselines for agreement, rank stability, missing-evidence robustness, evidence/uncertainty relationships, subgroup behaviour, and ties. No independent outcomes were available.

## Key findings

- F1 expected-vulnerability score covers {int(dist.loc[dist.method=='F1','n_scored'].iloc[0]):,} households. F1 P(high) is reported separately.
- F1 vs B1 Spearman agreement: {float(m1.query("method_a == 'F1' and method_b == 'B1'").spearman.iloc[0]):.3f}.
- F1 perturbation Spearman mean: {float(m2.spearman_mean.iloc[0]):.3f}; top-decile retention mean: {float(m2.top_decile_retention_mean.iloc[0]):.3f}.
- Missing-evidence comparisons are in `m3_missing_evidence_stress.csv`; results are not uniformly better for every method or mask rate.
- Proxy comparisons are separate and descriptive only.

See `stage6_evaluation_report.md` for full results, including weaker agreements and limitations. Research output only; not an eligibility determination.
"""


if __name__ == "__main__":
    run()
