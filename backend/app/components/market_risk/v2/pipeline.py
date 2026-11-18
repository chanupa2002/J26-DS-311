"""Feature, rule, prediction and SHAP code ported from SUSTAIN_FE_and_Model_Training.ipynb.

Pure functions: no file, database or network access. Names follow the notebook.
Section numbers refer to the notebook. Any change here needs the parity test.

One deliberate difference from the notebook: a blank business_running gives
Unassigned unless the other signals already give High (owner decision). No visit in
the training data has this blank, so parity is not affected.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

HORIZONS = ("3M", "6M")
CAT = ["category", "district"]
FALLBACK_MARKET_CATEGORY = {"UNASSIGNED": "OTHER"}  # same CCPI series in the notebook

A = ["business_running", "profit", "coach_progressing", "revenue_band", "revenue_low", "hours_band",
     "record_keeping", "borrowed_money", "saved_money", "grant_status"]
P = ["problem_sales_low", "problem_asset_lost", "problem_input_cost", "problem_input_unavailable",
     "problem_storage_transport", "problem_equipment", "problem_disaster"]
MS = ["problem_sales_low", "problem_input_cost", "problem_input_unavailable"]
HCOLS = ["prev_risk_ord", "prev_no_profit", "prev_market_stress", "prev_revenue_band", "revenue_drop",
         "risk_change", "months_since_prev", "tenure_months", "n_prior_visits", "risk_mean_3m",
         "no_profit_rate_3m", "market_stress_rate_3m", "high_count_6m"]
D = ["market_pressure", "ccpi_anomaly", "diesel_anomaly", "dmc_affected_families", "dmc_any_disaster"]
CUR = ["risk_ord_t", "risk_signals_t"]
F = ["revenue_band_dk", "profit_dk", "coach_progressing_dk", "record_keeping_dk",
     "children_in_school_not_applicable", "ill_member_got_care_not_applicable",
     "referral_reached_not_applicable"]
AREA = ["area_food_insecurity_score", "area_debt_pct", "area_land_pct", "area_households_surveyed",
        "area_in_debt_percent_hh", "area_food_price_shock_any_impact_percent_hh",
        "area_fuel_price_shock_any_impact_percent_hh", "area_difficulty_selling_outputs_any_impact_percent_hh",
        "area_input_shortage_any_impact_percent_hh", "area_receives_aswesuma_percent_hh"]

ANSWER_COLUMNS = [c for c in A if c != "revenue_low"] + P + F
ID_COLUMNS = ["household_key", "is_synthetic", "monitoring_period", "district", "category"]
VISIT_INPUT_COLUMNS = ID_COLUMNS + ANSWER_COLUMNS

FEATURE_GROUPS = {
    **{c: "Business" for c in A},
    **{c: "Household shock" for c in P + ["problem_count", "market_stress_any"]},
    **{c: "History" for c in HCOLS},
    **{c: "Market" for c in D},
    **{c: "Current risk" for c in CUR},
}

FEATURE_LABELS = {
    "business_running": "Business status",
    "profit": "Profit last month",
    "coach_progressing": "Coach's view of progress",
    "revenue_band": "Revenue last month",
    "revenue_low": "Revenue against the poverty line",
    "hours_band": "Hours worked per day",
    "record_keeping": "Business record keeping",
    "borrowed_money": "Borrowed money for the business",
    "saved_money": "Saved money last month",
    "grant_status": "Grant status",
    "problem_sales_low": "Sales lower than expected",
    "problem_asset_lost": "Lost a livelihood asset",
    "problem_input_cost": "High input costs",
    "problem_input_unavailable": "Inputs not available",
    "problem_storage_transport": "Storage or transport problem",
    "problem_equipment": "Equipment not working",
    "problem_disaster": "Affected by a natural disaster",
    "problem_count": "Number of problems reported",
    "market_stress_any": "Market stress at this visit",
    "prev_risk_ord": "Risk at the previous visit",
    "prev_no_profit": "No profit at the previous visit",
    "prev_market_stress": "Market stress at the previous visit",
    "prev_revenue_band": "Revenue at the previous visit",
    "revenue_drop": "Revenue fell since the previous visit",
    "risk_change": "Change in risk since the previous visit",
    "months_since_prev": "Months since the previous visit",
    "tenure_months": "Months since the first visit",
    "n_prior_visits": "Number of earlier visits",
    "risk_mean_3m": "Average risk over the last 3 months",
    "no_profit_rate_3m": "Share of visits without profit, last 3 months",
    "market_stress_rate_3m": "Share of visits with market stress, last 3 months",
    "high_count_6m": "High-risk visits in the last 6 months",
    "market_pressure": "Market price pressure for this livelihood",
    "ccpi_anomaly": "Consumer price anomaly",
    "diesel_anomaly": "Diesel price anomaly",
    "dmc_affected_families": "Families affected by disasters in the district",
    "dmc_any_disaster": "Disaster reported in the district",
    "risk_ord_t": "Current risk class",
    "risk_signals_t": "Number of current risk signals",
}

RISK_NAMES = {0: "Low", 1: "Medium", 2: "High"}
YES_NO = {0: "No", 1: "Yes"}
CODED_VALUES = {
    "business_running": {0: "Not running", 1: "Running"},
    "profit": {0: "No profit", 1: "Made a profit"},
    "coach_progressing": {0: "Not progressing", 1: "Progressing"},
    "revenue_low": {0: "At or above the poverty line", 1: "Below the poverty line"},
    "hours_band": {1: "1-4 hours", 2: "5-8 hours", 3: "9 or more hours"},
    "record_keeping": {0: "No records", 1: "A few times a month", 2: "Once or twice a week", 3: "Daily"},
    "grant_status": {0: "Not received", 1: "Not fully used", 2: "Used, bills not settled", 3: "Fully used"},
    "prev_risk_ord": RISK_NAMES,
    "risk_ord_t": RISK_NAMES,
}
YES_NO_FEATURES = set(P) | {"borrowed_money", "saved_money", "market_stress_any", "prev_no_profit",
                            "prev_market_stress", "revenue_drop", "dmc_any_disaster"}


class ExplanationError(RuntimeError):
    """SHAP values do not add up to the model probability."""


@dataclass(frozen=True)
class PipelineTables:
    """Lookup tables the features need, already loaded by the caller."""

    opl: pd.DataFrame  # month, national_opl_lkr
    market: pd.DataFrame  # district x category x month table
    macro: pd.DataFrame  # month, ccpi_anomaly, diesel_anomaly
    revenue_upper: dict[int, float]  # band -> upper limit (NaN = open-ended)
    k_high: int  # signals needed for High


def month_index(month: str) -> int:
    return int(month[:4]) * 12 + int(month[5:])


# ---- Section 1: business status -------------------------------------------------------


def opl_asof(opl: pd.DataFrame, month: str) -> tuple[float, str | None]:
    """Latest published poverty line on or before the month."""
    rows = opl[opl.month <= month].sort_values("month")
    if rows.empty:
        return np.nan, None
    row = rows.iloc[-1]
    return float(row.national_opl_lkr), row.month


def add_revenue_low(df: pd.DataFrame, tables: PipelineTables) -> None:
    asof = {m: opl_asof(tables.opl, m) for m in df.monitoring_period.unique()}
    df["opl_lkr"] = df.monitoring_period.map(lambda m: asof[m][0]).astype(float)
    df["opl_month_used"] = df.monitoring_period.map(lambda m: asof[m][1])
    upper = df.revenue_band.map(tables.revenue_upper).astype(float)
    low = (upper.fillna(np.inf) < df.opl_lkr).astype(float)
    df["revenue_low"] = low.where(df.revenue_band.notna() & df.opl_lkr.notna())


# ---- Section 2: household shocks -------------------------------------------------------


def add_problem_features(df: pd.DataFrame) -> None:
    df["problem_count"] = df[P].sum(axis=1, min_count=1)
    df["market_stress_any"] = np.where(
        df[MS].eq(1).any(axis=1), 1.0, np.where(df[MS].eq(0).all(axis=1), 0.0, np.nan)
    )


# ---- Section 3: current risk -----------------------------------------------------------


def _signals(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "no_profit": 1 - df.profit,
        "not_progressing": 1 - df.coach_progressing,
        "market_stress": df.market_stress_any,
    })


def classify(df: pd.DataFrame, k_high: int = 2) -> pd.Series:
    """SUSTAIN-HH-Risk-Rule v1.0, with a blank business status treated as unknown."""
    sig = _signals(df)
    n_yes = sig.eq(1).sum(axis=1)  # signals surely present
    n_poss = sig.ne(0).sum(axis=1)  # present or unknown (worst case)
    cls = lambda n: np.where(n == 0, "Low", np.where(n < k_high, "Medium", "High"))
    best, worst = cls(n_yes), cls(n_poss)
    out = np.where(best == worst, best, "Unassigned")
    out = np.where(df.business_running.isna() & (n_yes < k_high), "Unassigned", out)
    return pd.Series(np.where(df.business_running == 0, "High", out), index=df.index)


def add_current_risk(df: pd.DataFrame, k_high: int) -> None:
    sig = _signals(df)
    df["risk_class_t"] = classify(df, k_high)
    df["risk_ord_t"] = df.risk_class_t.map({"Low": 0, "Medium": 1, "High": 2}).astype(float)
    df["risk_signals_t"] = (sig.eq(1).sum(axis=1) + (df.business_running == 0).astype(int)).astype(float)


def reasons(r) -> list[str]:
    """Notebook section 19, returned as a list. '; '.join gives the notebook's text."""
    out = []
    if r.business_running == 0:
        out.append("business not running")
    if r.profit == 0:
        out.append("no profit last month")
    if r.coach_progressing == 0:
        out.append("coach: not progressing")
    if r.market_stress_any == 1:
        out.append("market stress (low sales / input cost / inputs unavailable)")
    if r.risk_class_t == "Unassigned":
        answers = (("business status", r.business_running), ("profit", r.profit),
                   ("coach", r.coach_progressing), ("market stress", r.market_stress_any))
        unk = [name for name, value in answers if pd.isna(value)]
        out.append("form incomplete: " + ", ".join(unk) + " unknown - ask SDO")
    return out or ["no warning signals"]


# ---- Section 4: household history ------------------------------------------------------


def history(d: pd.DataFrame) -> pd.DataFrame:
    """The 13 history features. Uses the current and earlier visits, never later ones."""
    d = d.sort_values(["household_key", "month_index"], kind="stable").copy()
    g = d.groupby("household_key", sort=False)
    out = pd.DataFrame(index=d.index)
    out["prev_risk_ord"] = g.risk_ord_t.shift(1)
    out["prev_no_profit"] = 1 - g.profit.shift(1)
    out["prev_market_stress"] = g.market_stress_any.shift(1)
    out["prev_revenue_band"] = g.revenue_band.shift(1)
    out["revenue_drop"] = (d.revenue_band < out.prev_revenue_band).astype(float).where(
        out.prev_revenue_band.notna() & d.revenue_band.notna()
    )
    out["risk_change"] = d.risk_ord_t - out.prev_risk_ord
    out["months_since_prev"] = d.month_index - g.month_index.shift(1)
    out["tenure_months"] = d.month_index - g.month_index.transform("min")
    out["n_prior_visits"] = g.cumcount().astype(float)

    def window(col, k, fn):  # visits in months (t-k, t], same household
        res = pd.Series(np.nan, index=d.index)
        for _, s in d.groupby("household_key", sort=False):
            mo, v = s.month_index.values, s[col].values.astype(float)
            for i, ix in enumerate(s.index):
                x = v[(mo > mo[i] - k) & (mo <= mo[i])]
                x = x[~np.isnan(x)]
                res[ix] = fn(x) if len(x) else np.nan
        return res

    out["risk_mean_3m"] = window("risk_ord_t", 3, np.mean)
    out["no_profit_rate_3m"] = window("no_profit_t", 3, np.mean)
    out["market_stress_rate_3m"] = window("market_stress_any", 3, np.mean)
    out["high_count_6m"] = window("risk_ord_t", 6, lambda x: float((x == 2).sum()))
    return out


def add_history(df: pd.DataFrame) -> None:
    """Visits without a household_key keep every history feature null, as in the notebook."""
    df["no_profit_t"] = 1 - df.profit
    for column in HCOLS:
        df[column] = np.nan
    keyed = df[df.household_key.notna()]
    if not keyed.empty:
        computed = history(keyed)
        for column in HCOLS:
            df.loc[computed.index, column] = computed[column]


# ---- Sections 5 and 6: market and district context --------------------------------------


def add_market(df: pd.DataFrame, tables: PipelineTables) -> None:
    table = tables.market.rename(columns={
        "category": "_market_category",
        "month": "monitoring_period",
        "price_month_used": "market_price_month_used",
        "series": "market_series",
        "ipa_basis": "market_ipa_basis",
    })[["district", "_market_category", "monitoring_period", "market_pressure", "market_pressure_level",
        "market_price_month_used", "market_series", "market_ipa_basis", "dmc_affected_families", *AREA]]
    keys = pd.DataFrame({
        "district": df.district.values,
        "_market_category": df.category.replace(FALLBACK_MARKET_CATEGORY).values,
        "monitoring_period": df.monitoring_period.values,
    })
    joined = keys.merge(table, how="left", on=["district", "_market_category", "monitoring_period"], validate="m:1")
    macro = keys[["monitoring_period"]].merge(
        tables.macro.rename(columns={"month": "monitoring_period"}), how="left", on="monitoring_period", validate="m:1"
    )
    for column in ["market_pressure", "market_pressure_level", "market_price_month_used", "market_series",
                   "market_ipa_basis", "dmc_affected_families", *AREA]:
        df[column] = joined[column].values
    df["ccpi_anomaly"] = macro.ccpi_anomaly.values
    df["diesel_anomaly"] = macro.diesel_anomaly.values
    df["dmc_any_disaster"] = (df.dmc_affected_families > 0).astype(float).where(df.dmc_affected_families.notna())


def build_features(visits: pd.DataFrame, tables: PipelineTables) -> pd.DataFrame:
    """All notebook features for the given visits. Rows and index order are kept."""
    df = visits.reindex(columns=VISIT_INPUT_COLUMNS).copy()
    for column in ANSWER_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce").astype(float)
    df["month_index"] = df.monitoring_period.map(month_index)
    add_revenue_low(df, tables)
    add_problem_features(df)
    add_current_risk(df, tables.k_high)
    add_history(df)
    add_market(df, tables)
    return df


# ---- Sections 12 and 19: model input and predictions -------------------------------------


def design(features: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Model matrix with the training columns. Unseen district or category = all zeros."""
    data = {}
    for column in columns:
        if column.startswith("category_"):
            data[column] = (features.category == column[len("category_"):]).astype(float).values
        elif column.startswith("district_"):
            data[column] = (features.district == column[len("district_"):]).astype(float).values
        else:
            data[column] = pd.to_numeric(features[column], errors="coerce").astype(float).values
    return pd.DataFrame(data, columns=columns, index=features.index)


def predict_visits(features: pd.DataFrame, models: dict, meta: dict) -> pd.DataFrame:
    """P(High), predicted class and alert for each horizon. P(High) is rounded as in the notebook."""
    classes = meta["classes"]
    X_warning = design(features, meta["feature_columns"][meta["warning_model"]["features"]])
    X_classes = design(features, meta["feature_columns"][meta["classes_model"]["features"]])
    out = pd.DataFrame(index=features.index)
    for horizon in HORIZONS:
        p_high = models[f"{horizon}_warning"].predict_proba(X_warning)[:, 1]
        threshold = meta["high_alert_threshold"][horizon]
        out[f"predicted_{horizon}"] = [classes[int(i)] for i in models[f"{horizon}_classes"].predict(X_classes)]
        out[f"P_High_{horizon}"] = np.round(p_high, 3)
        out[f"high_alert_{horizon}"] = p_high >= threshold if threshold is not None else None
    return out


# ---- Section 18: SHAP --------------------------------------------------------------------


def base_feature(name: str) -> str:
    name = name.replace("missingindicator_", "")
    for column in CAT:
        if name.startswith(column + "_"):
            return column
    return name


def group_contributions(names: list[str], values: np.ndarray) -> dict[str, float]:
    """Sum SHAP values over a feature and its missing-indicator or one-hot columns."""
    totals: dict[str, float] = {}
    for name, value in zip(names, values):
        key = base_feature(name)
        totals[key] = totals.get(key, 0.0) + float(value)
    return totals


def format_value(feature: str, raw, revenue_labels: dict[int, str]) -> str:
    """Readable text for a feature value."""
    if pd.isna(raw):
        if FEATURE_GROUPS.get(feature) == "History":
            return "No earlier visit"
        if FEATURE_GROUPS.get(feature) == "Market":
            return "No market data"
        return "Not answered" if feature != "risk_ord_t" else "Unassigned"
    value = float(raw)
    if feature in ("revenue_band", "prev_revenue_band"):
        return revenue_labels.get(int(value), f"Band {int(value)}")
    if feature in CODED_VALUES:
        return CODED_VALUES[feature].get(int(value), f"{value:g}")
    if feature in YES_NO_FEATURES:
        return YES_NO.get(int(value), f"{value:g}")
    if feature in ("no_profit_rate_3m", "market_stress_rate_3m"):
        return f"{value:.0%} of visits"
    if feature == "risk_mean_3m":
        return f"{value:.2f} (0 = Low, 2 = High)"
    if feature == "risk_change":
        return f"{value:+.0f} class" if value else "No change"
    if feature in ("market_pressure", "ccpi_anomaly", "diesel_anomaly"):
        return f"{value:+.2f} SD from normal"
    if feature in ("months_since_prev", "tenure_months"):
        return f"{value:.0f} months"
    return f"{value:,.0f}"


def shap_top_factors(model, explainer, X_row: pd.DataFrame, raw_row: pd.Series,
                     revenue_labels: dict[int, str], top_k: int = 5,
                     tolerance: float = 1e-6) -> tuple[float, list[dict]]:
    """Base value and top factors for P(High) of one visit, ranked by absolute contribution."""
    preprocess, forest = model[:-1], model[-1]
    names = list(preprocess.get_feature_names_out())
    Xt = pd.DataFrame(preprocess.transform(X_row), columns=names, index=X_row.index)
    sv = explainer.shap_values(Xt)
    sv = sv[-1] if isinstance(sv, list) else (sv[:, :, -1] if np.ndim(sv) == 3 else sv)
    base = float(np.ravel(explainer.expected_value)[-1])
    totals = group_contributions(names, np.asarray(sv)[0])

    probability = float(forest.predict_proba(Xt.to_numpy())[0, 1])
    if abs(base + sum(totals.values()) - probability) >= tolerance:
        raise ExplanationError("SHAP values do not add up to the model probability")

    ranked = sorted(totals.items(), key=lambda item: (-abs(item[1]), item[0]))[:top_k]
    factors = []
    for feature, contribution in ranked:
        raw = raw_row[feature]
        factors.append({
            "feature": feature,
            "label": FEATURE_LABELS.get(feature, feature),
            "value": format_value(feature, raw, revenue_labels),
            "raw_value": None if pd.isna(raw) else float(raw),
            "group": FEATURE_GROUPS.get(feature, "Other"),
            "contribution": contribution,
        })
    return base, factors
