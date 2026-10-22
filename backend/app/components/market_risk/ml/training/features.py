"""Signals, features and targets for retraining from the cleaned monitoring data.

Ports the notebook (SUSTAIN_3M_6M_Risk_Prediction.ipynb) to the cleaned column
names of monitoring_visits_clean.csv:
  section 5   T_* signals                      -> t_signals
  section 12  household risk rule, variant A   -> risk_rule_a
  section 13  build_features (53 features)     -> build_features
  sections 14-15  exact t+h target matching    -> build_targets
Market and macro features come from combined.xlsx (Category_Month_Table), and
the grant date (not in the cleaned file) from Training_Table_HH_Month for the
rows that match the original synthetic panel.

Every keyed row (with a household_id) is SYNTHETIC; rows without one are real
and are never used for training.
"""

from typing import Any

import numpy as np
import pandas as pd

from app.components.market_risk.ml.training.xlsx_reader import excel_serial_to_datetime
from app.components.market_risk.schemas import MarketRiskFeatures

FEATURES = list(MarketRiskFeatures.model_fields)
FEATURES_CAT = ["F_Category", "F_District"]
FEATURES_NUM = [f for f in FEATURES if f not in FEATURES_CAT]
CLASSES = ["Low", "Medium", "High"]
CLASS_TO_INT = {c: i for i, c in enumerate(CLASSES)}
HORIZONS = {"3M": 3, "6M": 6}
DATA_BASIS = "SYNTHETIC panel (70 households, 9 categories)"

# Notebook KEY_TO_PROG plus the two categories that exist only in the cleaned data.
KEY_TO_LEVEL = {
    "AGRICULTURE & PLANTATION CROPS": "Agriculture & Plantation Crops",
    "LIVESTOCK & ANIMAL HUSBANDRY": "Livestock & Animal Husbandry",
    "FOOD PROCESSING & PRODUCTION": "Food Processing & Production",
    "TRADE": "Trade",
    "GARMENT TEXTILE, HANDICRAFTS": "Garment & Textile / Handicrafts (combined in source)",
    "CONSTRUCTION, BUILDING AND REPAIR": "Construction, Building & Repair",
    "OTHER": "Other",
    "FISHERIES & AQUACULTURE": "Other",
    "MISCELLANEOUS": "Other",
    "BEAUTY AND WELLNESS": "Beauty & Wellness",
    "TRANSPORT & LOGISTICS": "Transport & Logistics",
}
NEW_CATEGORY_KEYS = ("BEAUTY AND WELLNESS", "TRANSPORT & LOGISTICS")

T_COLS = [
    "T_Business_Not_Running", "T_No_Profit_Last_Month", "T_Not_Progressing_Well", "T_Revenue_Lowest_Band",
    "T_Sales_Below_Expected", "T_High_Input_Cost", "T_Inputs_Unavailable", "T_Market_Stress_Any",
]
RULE_SIGNALS = ["T_No_Profit_Last_Month", "T_Not_Progressing_Well", "T_Market_Stress_Any"]
LOWEST_REVENUE_BAND = "LKR 0-10,000"

HOURS_ORD = {"1-4 hours a day": 1, "5-8 hours a day": 2, "9+ hours a day": 3}
GRANT_STATUS_ORD = {
    "Not received": 0,
    "Received, not fully used": 1,
    "Received, fully used, bills not settled": 2,
    "Received, fully used": 3,
}
YES_NO_FEATURES = {
    "F_Borrowed_t": "borrowed_money",
    "F_Saved_t": "saved_money",
    "F_Cyclone_Affected_t": "cyclone_affected",
    "F_Female_Head": "female_headed",
    "F_Asset_Lost_t": "problem_asset_lost",
    "F_Storage_Transport_Issue_t": "problem_storage_transport",
    "F_Machinery_Issue_t": "problem_equipment",
    "F_Natural_Disaster_t": "problem_disaster",
}
MARKET_COLUMNS = [
    "Primary_Pressure_t", "Primary_Pressure_t_minus_1", "Primary_Volatility_t", "Primary_Volatility_t_minus_1",
    "Category_Pressure_Tier_Ord_t", "Category_Volatility_Tier_Ord_t", "Category_Pressure_Tier_Ord_t_minus_1",
]
MACRO_COLUMNS = [
    "Macro_CCPI_YoY_Inflation_t", "Macro_CCPI_YoY_Inflation_t_minus_1",
    "Macro_CCPI_Food_Index_t", "Macro_CCPI_Food_Index_t_minus_1",
    "Macro_AutoDiesel_Price_t", "Macro_AutoDiesel_Price_t_minus_1",
]
GRANT_DATE_COLUMN = "6.2. Grant Received date"
# The 13 features that depend only on (category, month) or on month: served by GET /market-context.
MARKET_FEATURES = [
    "F_Mkt_Pressure_t", "F_Mkt_Volatility_t", "F_Mkt_Pressure_Change_1M", "F_Mkt_Volatility_Change_1M",
    "F_Mkt_Pressure_Tier_Ord_t", "F_Mkt_Volatility_Tier_Ord_t", "F_Mkt_Pressure_Tier_Ord_t_minus_1",
    "F_Mkt_Evidence_Missing",
]
MACRO_FEATURES = [
    "F_Macro_CCPI_YoY_t", "F_Macro_CCPI_YoY_Change_1M", "F_Macro_Food_Index_Change_1M_pct",
    "F_Macro_Diesel_t", "F_Macro_Diesel_Change_1M_pct",
]
CONTEXT_FEATURES = MARKET_FEATURES + MACRO_FEATURES
# The 14 features computed from the same household's earlier visits (and the grant date).
HISTORY_FEATURES = [
    "F_Months_Since_Prev_Visit", "F_Prev_Risk_Ord", "F_Prev_No_Profit_Last_Month", "F_Prev_Market_Stress_Any",
    "F_Prev_Not_Progressing_Well", "F_Prev_Business_Not_Running", "F_Risk_Change_vs_Prev", "F_Tenure_Months",
    "F_N_Prior_Visits", "F_Risk_Mean_3M_Window", "F_NoProfit_Rate_3M_Window", "F_MarketStress_Rate_3M_Window",
    "F_High_Count_6M_Window", "F_Months_Since_Grant",
]
# Columns history_features needs, one row per visit.
HISTORY_INPUT_COLUMNS = [
    "household_id", "Month_Ord", "Risk_Ord_t", "T_No_Profit_Last_Month", "T_Market_Stress_Any",
    "T_Not_Progressing_Well", "T_Business_Not_Running", "visit_date", "grant_date",
]


def flag(values: pd.Series) -> pd.Series:
    """True/'True'/'TRUE' -> 1.0, False/... -> 0.0, anything else -> NaN."""
    mapping = {True: 1.0, False: 0.0, "True": 1.0, "False": 0.0, "TRUE": 1.0, "FALSE": 0.0}
    return values.map(lambda v: mapping.get(v, np.nan) if not isinstance(v, float) else np.nan).astype(float)


def month_ord(periods: pd.Series) -> pd.Series:
    """'YYYY-MM' -> pandas monthly Period ordinal (as the notebook's Month_Ord)."""
    return pd.PeriodIndex(periods.astype(str), freq="M").map(lambda p: p.ordinal).to_series(index=periods.index).astype(int)


def category_level(key: Any) -> str | None:
    if key is None or (isinstance(key, float) and np.isnan(key)):
        return None
    return KEY_TO_LEVEL.get(str(key).strip().upper())


def t_signals(cleaned: pd.DataFrame) -> pd.DataFrame:
    """The 8 T_* signals (1 / 0 / NaN) from the cleaned columns (notebook T_RULES)."""
    T = pd.DataFrame(index=cleaned.index)
    T["T_Business_Not_Running"] = 1.0 - flag(cleaned["business_running"])
    T["T_No_Profit_Last_Month"] = 1.0 - flag(cleaned["profit"])
    T["T_Not_Progressing_Well"] = 1.0 - flag(cleaned["coach_progressing"])
    band = cleaned["revenue_band"]
    T["T_Revenue_Lowest_Band"] = np.where(band.isna(), np.nan, (band == LOWEST_REVENUE_BAND).astype(float))
    T["T_Sales_Below_Expected"] = flag(cleaned["problem_sales_low"])
    T["T_High_Input_Cost"] = flag(cleaned["problem_input_cost"])
    T["T_Inputs_Unavailable"] = flag(cleaned["problem_input_unavailable"])
    parts = T[["T_Sales_Below_Expected", "T_High_Input_Cost", "T_Inputs_Unavailable"]]
    T["T_Market_Stress_Any"] = np.where((parts == 1).any(axis=1), 1.0, np.where((parts == 0).all(axis=1), 0.0, np.nan))
    return T[T_COLS]


def risk_rule_a(T: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Notebook risk_rule variant A: (risk ord 0/1/2 or NaN, n positive, n blank)."""
    business_not_running = T["T_Business_Not_Running"]
    signals = T[RULE_SIGNALS]
    n_pos = (signals == 1).sum(axis=1)
    n_unknown = signals.isna().sum(axis=1)

    def cls(n):
        return np.where(n >= 2, 2, np.where(n >= 1, 1, 0))

    low, high = cls(n_pos), cls(n_pos + n_unknown)
    out = np.where(low == high, low, -1).astype(float)
    out = np.where(business_not_running == 1, 2, out)
    out = np.where(business_not_running.isna() & (out < 2), -1, out)
    risk_ord = pd.Series(np.where(out < 0, np.nan, out), index=T.index)
    return risk_ord, n_pos, n_unknown


def join_market_macro(month: pd.Series, category_key: pd.Series, category_month: pd.DataFrame) -> pd.DataFrame:
    """Market columns by (month, category) from Row_Basis 'ALL'; macro columns by month only."""
    table = category_month.copy()
    table["Month"] = table["Month"].astype(str)
    market = table[table["Row_Basis"] == "ALL"][["Month", "Category_Key"] + MARKET_COLUMNS]
    if market.duplicated(["Month", "Category_Key"]).any():
        raise ValueError("Category_Month_Table has duplicate (Month, Category_Key) rows for Row_Basis 'ALL'")
    macro = table.groupby("Month")[MACRO_COLUMNS].first().reset_index()

    keys = pd.DataFrame({"Month": month.astype(str).values, "Category_Key": category_key.values})
    # left merges keep the left row order, so the original index can be reattached
    joined = keys.merge(market, on=["Month", "Category_Key"], how="left").merge(macro, on="Month", how="left")
    if len(joined) != len(keys):
        raise ValueError("Market/macro join changed the number of rows")
    joined.index = month.index
    for column in MARKET_COLUMNS + MACRO_COLUMNS:
        joined[column] = pd.to_numeric(joined[column], errors="coerce")
    return joined[MARKET_COLUMNS + MACRO_COLUMNS]


def history_features(d: pd.DataFrame) -> pd.DataFrame:
    """The 14 HISTORY_FEATURES (notebook section 13): each visit uses only itself and the same
    household's earlier visits. `d` has HISTORY_INPUT_COLUMNS and is sorted by household and
    month (as in build_features). Shared by training and POST /api/risk/history-features."""
    F = pd.DataFrame(index=d.index)
    g = d.groupby("household_id", sort=False)
    F["F_Months_Since_Prev_Visit"] = d["Month_Ord"] - g["Month_Ord"].shift(1)
    previous = {
        "F_Prev_Risk_Ord": "Risk_Ord_t",
        "F_Prev_No_Profit_Last_Month": "T_No_Profit_Last_Month",
        "F_Prev_Market_Stress_Any": "T_Market_Stress_Any",
        "F_Prev_Not_Progressing_Well": "T_Not_Progressing_Well",
        "F_Prev_Business_Not_Running": "T_Business_Not_Running",
    }
    for feature, column in previous.items():
        F[feature] = g[column].shift(1)
    F["F_Risk_Change_vs_Prev"] = d["Risk_Ord_t"] - F["F_Prev_Risk_Ord"]
    F["F_Tenure_Months"] = d["Month_Ord"] - g["Month_Ord"].transform("cummin")
    F["F_N_Prior_Visits"] = g.cumcount()

    windows = ["F_Risk_Mean_3M_Window", "F_NoProfit_Rate_3M_Window", "F_MarketStress_Rate_3M_Window", "F_High_Count_6M_Window"]
    for feature in windows:
        F[feature] = np.nan

    def nan_mean(values):
        return float(np.nanmean(values)) if np.any(~np.isnan(values)) else np.nan

    for _, gi in d.groupby("household_id", sort=False):
        months = gi["Month_Ord"].to_numpy()
        risk = gi["Risk_Ord_t"].to_numpy(dtype=float)
        no_profit = gi["T_No_Profit_Last_Month"].to_numpy(dtype=float)
        stress = gi["T_Market_Stress_Any"].to_numpy(dtype=float)
        for i, idx in enumerate(gi.index):
            w3 = (months <= months[i]) & (months >= months[i] - 2)
            w6 = (months <= months[i]) & (months >= months[i] - 5)
            F.at[idx, "F_Risk_Mean_3M_Window"] = nan_mean(risk[w3])
            F.at[idx, "F_NoProfit_Rate_3M_Window"] = nan_mean(no_profit[w3])
            F.at[idx, "F_MarketStress_Rate_3M_Window"] = nan_mean(stress[w3])
            F.at[idx, "F_High_Count_6M_Window"] = float(np.sum(risk[w6] == 2))

    grant = g["grant_date"].transform(lambda s: s.ffill())
    F["F_Months_Since_Grant"] = ((d["visit_date"] - grant).dt.days / 30.44).where(lambda x: x >= 0)

    return F[HISTORY_FEATURES]


def market_macro_features(d: pd.DataFrame) -> pd.DataFrame:
    """The 13 CONTEXT_FEATURES from joined MARKET_COLUMNS + MACRO_COLUMNS (notebook section 13)."""
    F = pd.DataFrame(index=d.index)
    F["F_Mkt_Pressure_t"] = d["Primary_Pressure_t"]
    F["F_Mkt_Volatility_t"] = d["Primary_Volatility_t"]
    F["F_Mkt_Pressure_Change_1M"] = d["Primary_Pressure_t"] - d["Primary_Pressure_t_minus_1"]
    F["F_Mkt_Volatility_Change_1M"] = d["Primary_Volatility_t"] - d["Primary_Volatility_t_minus_1"]
    F["F_Mkt_Pressure_Tier_Ord_t"] = d["Category_Pressure_Tier_Ord_t"]
    F["F_Mkt_Volatility_Tier_Ord_t"] = d["Category_Volatility_Tier_Ord_t"]
    F["F_Mkt_Pressure_Tier_Ord_t_minus_1"] = d["Category_Pressure_Tier_Ord_t_minus_1"]
    F["F_Mkt_Evidence_Missing"] = d["Primary_Pressure_t"].isna().astype(int)
    F["F_Macro_CCPI_YoY_t"] = d["Macro_CCPI_YoY_Inflation_t"]
    F["F_Macro_CCPI_YoY_Change_1M"] = d["Macro_CCPI_YoY_Inflation_t"] - d["Macro_CCPI_YoY_Inflation_t_minus_1"]
    F["F_Macro_Food_Index_Change_1M_pct"] = 100 * (d["Macro_CCPI_Food_Index_t"] / d["Macro_CCPI_Food_Index_t_minus_1"] - 1)
    F["F_Macro_Diesel_t"] = d["Macro_AutoDiesel_Price_t"]
    F["F_Macro_Diesel_Change_1M_pct"] = 100 * (d["Macro_AutoDiesel_Price_t"] / d["Macro_AutoDiesel_Price_t_minus_1"] - 1)
    return F[CONTEXT_FEATURES]


def build_panel(
    cleaned: pd.DataFrame, training_table: pd.DataFrame, category_month: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Keyed (synthetic) rows with signals, rule-A class, codings, joins and checks.

    Rows are matched to the original synthetic panel by household number + month
    (HH-n <-> SYN-HH-n); the grant date is taken from the match (NaT otherwise).
    Raises ValueError if the match is not one-to-one or the T_* signals differ.
    """
    keyed = cleaned[cleaned["household_id"].notna()].copy()
    if keyed.duplicated(["household_id", "monitoring_period"]).any():
        raise ValueError("Duplicate (household_id, monitoring_period) in the cleaned data")

    panel = pd.DataFrame(index=keyed.index)
    panel["household_id"] = keyed["household_id"].astype(str)
    panel["visit_id"] = keyed["visit_id"].astype(str)
    panel["month"] = keyed["monitoring_period"].astype(str)
    panel["Month_Ord"] = month_ord(keyed["monitoring_period"])
    panel["visit_date"] = pd.to_datetime(keyed["visit_date"], errors="coerce")
    panel["is_synthetic"] = True
    panel["category_key"] = keyed["category"].astype(str).str.strip().str.upper()
    panel["is_new_category"] = panel["category_key"].isin(NEW_CATEGORY_KEYS)

    T = t_signals(keyed)
    risk_ord, n_pos, n_unknown = risk_rule_a(T)
    panel[T_COLS] = T
    panel["Risk_Ord_t"] = risk_ord
    panel["Risk_Signal_Count_t"] = n_pos
    panel["Risk_Signal_Unknown_t"] = n_unknown

    panel["hours_band"] = keyed["hours_band"]
    panel["record_keeping_level"] = pd.to_numeric(keyed["record_keeping_level"], errors="coerce")
    panel["grant_use_status"] = keyed["grant_use_status"]
    for feature, column in YES_NO_FEATURES.items():
        panel[feature] = flag(keyed[column])
    panel["age"] = pd.to_numeric(keyed["age"], errors="coerce")
    panel["participant_gender"] = keyed["participant_gender"]
    panel["F_Category"] = panel["category_key"].map(category_level)
    panel["F_District"] = keyed["district"]
    unmapped = sorted(panel.loc[panel["F_Category"].isna(), "category_key"].unique())
    if unmapped:
        raise ValueError(f"Unknown category keys in keyed rows: {unmapped}")

    # match the original synthetic panel: HH-n <-> SYN-HH-n, same month
    original = training_table[training_table["household_key"].notna()].copy()
    original["_num"] = original["household_key"].astype(str).str.extract(r"(\d+)$")[0].astype(int)
    original["_month"] = original["Month"].astype(str)
    if original.duplicated(["_num", "_month"]).any():
        raise ValueError("Original synthetic panel has duplicate (household, month) rows")
    panel["_num"] = panel["household_id"].str.extract(r"(\d+)$")[0].astype(int)
    match = panel[["_num", "month"]].merge(
        original[["_num", "_month", GRANT_DATE_COLUMN, "Date of SDO household visit"] + T_COLS],
        left_on=["_num", "month"], right_on=["_num", "_month"], how="left", indicator=True,
    )
    match.index = panel.index  # left merge keeps the left row order
    panel["is_original"] = match["_merge"].eq("both").values
    panel["grant_date"] = excel_serial_to_datetime(match[GRANT_DATE_COLUMN]).where(panel["is_original"])

    matched = panel["is_original"]
    t_mismatches = {}
    for column in T_COLS:
        a = panel.loc[matched, column].to_numpy(dtype=float)
        b = pd.to_numeric(match.loc[matched, column], errors="coerce").to_numpy(dtype=float)
        t_mismatches[column] = int((~((a == b) | (np.isnan(a) & np.isnan(b)))).sum())
    if any(t_mismatches.values()):
        raise ValueError(f"T_* signals differ from the original synthetic panel: {t_mismatches}")
    original_visit = excel_serial_to_datetime(match.loc[matched, "Date of SDO household visit"]).dt.normalize()
    visit_date_agreement = float((original_visit.values == panel.loc[matched, "visit_date"].dt.normalize().values).mean()) if matched.any() else float("nan")

    panel = panel.join(join_market_macro(panel["month"], panel["category_key"], category_month))
    panel = panel.drop(columns="_num")

    checks = {
        "cleaned_rows": int(len(cleaned)),
        "keyed_rows_used": int(len(panel)),
        "unkeyed_rows_excluded": int(cleaned["household_id"].isna().sum()),
        "households": int(panel["household_id"].nunique()),
        "categories": int(panel["F_Category"].nunique()),
        "rows_matched_to_original_panel": int(matched.sum()),
        "original_panel_rows": int(len(original)),
        "new_category_rows": int(panel["is_new_category"].sum()),
        "t_signal_mismatches_vs_original": t_mismatches,
        "visit_date_agreement_vs_original": visit_date_agreement,
        "grant_dates_available": int(panel["grant_date"].notna().sum()),
        "rows_without_market_evidence": int(panel["Primary_Pressure_t"].isna().sum()),
    }
    return panel, checks


def build_features(panel: pd.DataFrame) -> pd.DataFrame:
    """The 53 F_* features (notebook section 13), using visit t and earlier visits only."""
    d = panel.sort_values(["household_id", "Month_Ord", "visit_id"]).copy()
    F = pd.DataFrame(index=d.index)
    for t in T_COLS:
        F["F_" + t[2:] + "_t"] = d[t]
    F["F_Risk_Ord_t"] = d["Risk_Ord_t"]
    F["F_Risk_Signal_Count_t"] = d["Risk_Signal_Count_t"]
    F["F_Risk_Unknown_t"] = d["Risk_Signal_Unknown_t"]
    F["F_Hours_Ord_t"] = d["hours_band"].map(HOURS_ORD)
    F["F_Records_Ord_t"] = d["record_keeping_level"]
    F["F_Grant_Status_Ord_t"] = d["grant_use_status"].map(GRANT_STATUS_ORD)
    for feature in YES_NO_FEATURES:
        F[feature] = d[feature]
    F["F_Age"] = d["age"]
    F["F_Female_Participant"] = d["participant_gender"].map({"Female": 1, "Male": 0})

    F[HISTORY_FEATURES] = history_features(d)

    F[CONTEXT_FEATURES] = market_macro_features(d)

    F["F_Category"] = d["F_Category"]
    F["F_District"] = d["F_District"]
    return F.loc[panel.index, FEATURES]


def build_targets(panel: pd.DataFrame, horizons: dict[str, int] = HORIZONS) -> pd.DataFrame:
    """Risk_Label_hM = rule-A class of the same household's visit in calendar month t+h (exact)."""
    last_month = int(panel["Month_Ord"].max())
    lookup = panel.set_index(["household_id", "Month_Ord"])["Risk_Ord_t"]
    out = pd.DataFrame(index=panel.index)
    for name, h in horizons.items():
        labels, target_months = [], []
        for household, month in zip(panel["household_id"], panel["Month_Ord"]):
            target = int(month) + h
            target_months.append(str(pd.Period(ordinal=target, freq="M")))
            value = lookup.get((household, target), np.nan) if target <= last_month else np.nan
            labels.append(CLASSES[int(value)] if pd.notna(value) else np.nan)
        out[f"Risk_Label_{name}"] = labels
        out[f"Target_Month_{name}"] = target_months
    return out


def model_datasets(panel: pd.DataFrame, features: pd.DataFrame, targets: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Per-horizon modelling tables (rows with a label), sorted as in notebook section 18."""
    ids = panel[["household_id", "visit_id", "month", "Month_Ord", "F_Category", "is_new_category", "is_original"]].rename(
        columns={"F_Category": "category_level"}
    )
    out = {}
    for name in HORIZONS:
        label = targets[f"Risk_Label_{name}"]
        keep = label.notna()
        frame = pd.concat([ids[keep], features[keep], targets.loc[keep, [f"Risk_Label_{name}", f"Target_Month_{name}"]]], axis=1)
        frame["y"] = frame[f"Risk_Label_{name}"].map(CLASS_TO_INT).astype(int)
        out[name] = frame.sort_values(["Month_Ord", "household_id"])
    return out


def truncation_differences(panel: pd.DataFrame, features: pd.DataFrame) -> tuple[int, int]:
    """Leakage test (notebook section 17): features on data cut at each month must not change."""
    differences, checked = 0, 0
    for month in sorted(panel["Month_Ord"].unique()):
        part = panel[panel["Month_Ord"] <= month]
        rows = part.index[part["Month_Ord"] == month]
        recomputed = build_features(part).loc[rows, FEATURES_NUM]
        full = features.loc[rows, FEATURES_NUM]
        for column in FEATURES_NUM:
            a, b = recomputed[column].astype(float), full[column].astype(float)
            differences += int((~np.isclose(a, b, equal_nan=True)).sum())
            checked += len(a)
    return differences, checked
