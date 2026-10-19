"""Component 1 - Stage 4 fuzzy layer, version 0.1.

Implements the approved Spec v0.1 (decisions D-01 to D-10, M-01, M-04):
  * one membership ("degree of deprivation", 0 to 1) per input;
  * equal-weight mean of the AVAILABLE memberships within each domain;
  * unknown evidence stays unknown: no imputation, never treated as 0.

This is a research tool. Its outputs are NOT eligibility determinations.
label_high_vuln and pc_cons are never inputs.

Input contract (one row per household; NaN / None / unrecognised = unknown):
  fies_raw_score          0-8, count of items coded 1 (blank unless all 8 valid)   D-01
  persons_per_bedroom     roster members / C1_02 (blank if C1_02 < 1)              D-06
  dependency_ratio        (under15 + 65plus) / (15-64), blank if no worker         D-07
  no_working_age_member   1 if no member aged 15-64                                D-07
  income_value            H1_17, only where repeated records agree                 D-09
  asset_types_owned_n     number of asset types owned                              D-10
  asset_items_valid_n     number of asset items with a valid value                 D-10
  tenure_class            secure | intermediate | insecure                         D-05
  toilet_service_class    basic | limited | unimproved | open_defecation           D-04
  wall_durability, floor_durability, roof_durability: durable | non_durable        D-03
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd

MODEL_VERSION = "fuzzy-0.1.0"
SPEC_VERSION = "0.1"
OUTPUT_LABEL = "Research output - not an eligibility determination"

# --- Defaults that are researcher judgements (log them; test in sensitivity) ---
CROWDING_MIDPOINT = 3.0      # D-06: persons per bedroom, midpoint of the ramp
CROWDING_HALF_WIDTH = 1.0    # D-06: ramp runs from 2 to 4
MIN_VALID_ASSETS = None      # D-10 denominator rule still open: no minimum enforced
# Ordinal degrees use equal spacing between ordered levels (default, not a standard).
TENURE_DEGREE = {"secure": 0.0, "intermediate": 0.5, "insecure": 1.0}
TOILET_DEGREE = {"basic": 0.0, "limited": 1 / 3, "unimproved": 2 / 3, "open_defecation": 1.0}
MATERIAL_DEGREE = {"durable": 0.0, "non_durable": 1.0}

DOMAINS = {
    "housing": ["mu_wall", "mu_floor", "mu_roof", "mu_toilet", "mu_tenure", "mu_crowding"],
    "economic": ["mu_income", "mu_assets"],
    "food": ["mu_food"],
    "demographic": ["mu_dependency"],
}


def ramp(x, lo: float, hi: float):
    """Linear 0->1 between lo and hi; NaN stays NaN."""
    x = pd.to_numeric(pd.Series(x), errors="coerce")
    return ((x - lo) / (hi - lo)).clip(0, 1)


class Reference:
    """Frozen empirical distribution for Totally Fuzzy and Relative memberships.

    Fit once on the BRIGHT 2025 data and save with the model version, so a household
    gets the same score whatever other records are loaded with it.
    """

    def __init__(self, values=None):
        self.sorted = None
        if values is not None:
            self.fit(values)

    def fit(self, values):
        v = pd.to_numeric(pd.Series(values), errors="coerce").dropna().to_numpy(float)
        if v.size == 0:
            raise ValueError("Reference needs at least one non-missing value")
        self.sorted = np.sort(v)
        return self

    def cdf(self, x):
        """Mid-rank empirical CDF in [0, 1]; ties share the middle of their range."""
        x = pd.to_numeric(pd.Series(x), errors="coerce")
        out = pd.Series(np.nan, index=x.index)
        ok = x.notna()
        left = np.searchsorted(self.sorted, x[ok].to_numpy(float), side="left")
        right = np.searchsorted(self.sorted, x[ok].to_numpy(float), side="right")
        out[ok] = (left + right) / 2.0 / self.sorted.size
        return out

    def to_json(self) -> str:
        return json.dumps({"sorted": self.sorted.tolist()})

    @classmethod
    def from_json(cls, s: str):
        ref = cls()
        ref.sorted = np.asarray(json.loads(s)["sorted"], float)
        return ref


def _ordinal(series: pd.Series, mapping: dict) -> pd.Series:
    return series.map(mapping).astype(float)  # unrecognised -> NaN (unknown)


def fit_references(df: pd.DataFrame) -> dict:
    """Fit the frozen reference distributions on a reference dataset."""
    refs = {"income": Reference(df["income_value"]), "assets": Reference(df["asset_types_owned_n"])}
    dep = df["dependency_ratio"].where(df.get("no_working_age_member", 0) != 1)
    refs["dependency"] = Reference(dep)
    return refs


def memberships(df: pd.DataFrame, refs: dict) -> pd.DataFrame:
    """Per-input degree of deprivation, 0 (not deprived) to 1 (fully deprived)."""
    out = pd.DataFrame(index=df.index)
    col = lambda name: df[name] if name in df else pd.Series(np.nan, index=df.index)

    out["mu_food"] = col("fies_raw_score").pipe(pd.to_numeric, errors="coerce").clip(0, 8) / 8.0
    out["mu_crowding"] = ramp(col("persons_per_bedroom"),
                              CROWDING_MIDPOINT - CROWDING_HALF_WIDTH,
                              CROWDING_MIDPOINT + CROWDING_HALF_WIDTH)
    dep = refs["dependency"].cdf(col("dependency_ratio"))
    dep = dep.where(col("no_working_age_member") != 1, 1.0)  # D-07: top-code, do not drop
    out["mu_dependency"] = dep
    out["mu_income"] = 1.0 - refs["income"].cdf(col("income_value"))  # lower income = more deprived
    assets = col("asset_types_owned_n").copy()
    if MIN_VALID_ASSETS is not None:
        assets = assets.where(col("asset_items_valid_n") >= MIN_VALID_ASSETS)
    out["mu_assets"] = 1.0 - refs["assets"].cdf(assets)
    out["mu_tenure"] = _ordinal(col("tenure_class"), TENURE_DEGREE)
    out["mu_toilet"] = _ordinal(col("toilet_service_class"), TOILET_DEGREE)
    for part in ("wall", "floor", "roof"):
        out[f"mu_{part}"] = _ordinal(col(f"{part}_durability"), MATERIAL_DEGREE)
    return out


def domain_degrees(mu: pd.DataFrame) -> pd.DataFrame:
    """Equal-weight mean of the available memberships; reports how much evidence was used."""
    out = pd.DataFrame(index=mu.index)
    for name, cols in DOMAINS.items():
        block = mu[cols]
        out[f"dom_{name}"] = block.mean(axis=1, skipna=True)  # NaN only if all unknown
        out[f"dom_{name}_n_used"] = block.notna().sum(axis=1)
        out[f"dom_{name}_n_total"] = len(cols)
    return out


def soft_levels(degree: pd.Series) -> pd.DataFrame:
    """Triangular low / medium / high memberships of a domain degree (soft evidence for
    the Bayesian Network; the boundaries are a default to be tested, M-02)."""
    d = pd.to_numeric(degree, errors="coerce")
    low = (1 - 2 * d).clip(0, 1)
    high = (2 * d - 1).clip(0, 1)
    med = 1 - low - high
    return pd.DataFrame({"low": low, "medium": med, "high": high})


def score_households(df: pd.DataFrame, refs: dict) -> pd.DataFrame:
    mu = memberships(df, refs)
    dom = domain_degrees(mu)
    res = pd.concat([mu, dom], axis=1)
    for name in DOMAINS:
        lv = soft_levels(dom[f"dom_{name}"]).add_prefix(f"soft_{name}_")
        res = pd.concat([res, lv], axis=1)
    if "hhcode" in df:
        res.insert(0, "hhcode", df["hhcode"])
    res.attrs.update(model_version=MODEL_VERSION, spec_version=SPEC_VERSION, label=OUTPUT_LABEL)
    return res
