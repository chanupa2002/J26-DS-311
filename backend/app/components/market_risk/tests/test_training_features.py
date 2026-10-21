"""Unit tests for the retraining feature code (ml/training). Inline toy data only; no data files."""

import itertools
import zipfile

import numpy as np
import pandas as pd
import pytest

from app.components.market_risk import services
from app.components.market_risk.ml import loader
from app.components.market_risk.ml.training import features as fx
from app.components.market_risk.ml.training.xlsx_reader import excel_serial_to_datetime, read_xlsx

CLEANED_DEFAULTS = {
    "visit_date": "2026-01-10", "category": "TRADE", "business_running": True, "profit": True,
    "coach_progressing": True, "revenue_band": "LKR 10,001-20,000", "problem_sales_low": False,
    "problem_input_cost": False, "problem_input_unavailable": False, "hours_band": "1-4 hours a day",
    "record_keeping_level": 1.0, "grant_use_status": "Received, fully used", "borrowed_money": False,
    "saved_money": True, "cyclone_affected": False, "female_headed": False, "problem_asset_lost": False,
    "problem_storage_transport": False, "problem_equipment": False, "problem_disaster": False,
    "age": 40.0, "participant_gender": "Female", "district": "Badulla",
}


def _cleaned(rows):
    return pd.DataFrame([{**CLEANED_DEFAULTS, **row} for row in rows])


def _panel(rows):
    """Minimal panel rows for build_features / build_targets."""
    base = {
        **{t: 0.0 for t in fx.T_COLS}, "Risk_Ord_t": 0.0, "Risk_Signal_Count_t": 0, "Risk_Signal_Unknown_t": 0,
        "hours_band": "5-8 hours a day", "record_keeping_level": 2.0, "grant_use_status": "Not received",
        **{f: 0.0 for f in fx.YES_NO_FEATURES}, "age": 30.0, "participant_gender": "Male",
        "grant_date": pd.NaT, "visit_date": pd.Timestamp("2026-01-15"),
        **{c: np.nan for c in fx.MARKET_COLUMNS},
        "Macro_CCPI_YoY_Inflation_t": 2.0, "Macro_CCPI_YoY_Inflation_t_minus_1": 1.5,
        "Macro_CCPI_Food_Index_t": 110.0, "Macro_CCPI_Food_Index_t_minus_1": 100.0,
        "Macro_AutoDiesel_Price_t": 300.0, "Macro_AutoDiesel_Price_t_minus_1": 250.0,
        "F_Category": "Trade", "F_District": "Badulla",
    }
    frame = pd.DataFrame([{**base, **row} for row in rows])
    frame["visit_id"] = [f"V{i:04d}" for i in range(len(frame))]
    return frame


# ---------------------------------------------------------------- signals ----
def test_flag_handles_bools_strings_and_blanks():
    values = pd.Series([True, False, np.True_, "TRUE", "False", np.nan, None, "maybe"], dtype=object)

    assert fx.flag(values).tolist()[:5] == [1.0, 0.0, 1.0, 1.0, 0.0]
    assert fx.flag(values).iloc[5:].isna().all()


def test_t_signals_follow_the_notebook_rules():
    cleaned = _cleaned([
        {"business_running": False, "profit": False, "coach_progressing": False, "revenue_band": "LKR 0-10,000",
         "problem_sales_low": True},
        {"profit": np.nan, "coach_progressing": np.nan, "revenue_band": np.nan,
         "problem_sales_low": np.nan, "problem_input_cost": False, "problem_input_unavailable": False},
        {"problem_sales_low": False, "problem_input_cost": False, "problem_input_unavailable": False},
    ])

    T = fx.t_signals(cleaned)

    assert list(T.columns) == fx.T_COLS
    assert T.iloc[0].tolist() == [1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 1.0]
    assert T.iloc[1][["T_Business_Not_Running", "T_High_Input_Cost", "T_Inputs_Unavailable"]].tolist() == [0.0, 0.0, 0.0]
    assert T.iloc[1][["T_No_Profit_Last_Month", "T_Not_Progressing_Well", "T_Revenue_Lowest_Band",
                      "T_Sales_Below_Expected", "T_Market_Stress_Any"]].isna().all()
    assert T.iloc[2]["T_Market_Stress_Any"] == 0.0 and T.iloc[2]["T_Revenue_Lowest_Band"] == 0.0


def test_risk_rule_a_equals_identify_current_risk_on_all_81_combinations():
    combos = list(itertools.product([0, 1, None], repeat=4))
    T = pd.DataFrame(combos, columns=["T_Business_Not_Running", *fx.RULE_SIGNALS], dtype=float)

    risk_ord, n_pos, n_unknown = fx.risk_rule_a(T)

    for i, values in enumerate(combos):
        expected = services.identify_current_risk(dict(zip(
            ["business_not_running", "no_profit_last_month", "not_progressing_well", "market_stress_any"], values)))
        assert (None if pd.isna(risk_ord[i]) else int(risk_ord[i])) == expected.risk_ord, values
        assert (n_pos[i], n_unknown[i]) == (expected.signal_count, expected.unknown_count)


@pytest.mark.parametrize(
    ("key", "level"),
    [
        ("TRADE", "Trade"),
        ("  beauty and wellness ", "Beauty & Wellness"),
        ("TRANSPORT & LOGISTICS", "Transport & Logistics"),
        ("GARMENT TEXTILE, HANDICRAFTS", "Garment & Textile / Handicrafts (combined in source)"),
        ("FISHERIES & AQUACULTURE", "Other"),
        ("UNASSIGNED", None),
        (np.nan, None),
    ],
)
def test_category_level(key, level):
    assert fx.category_level(key) == level


@pytest.mark.parametrize("horizon", ["3M", "6M"])
def test_category_mapping_matches_the_nine_deployed_levels(horizon):
    deployed = set(loader.load_metadata(horizon)["categorical_levels"]["F_Category"])
    levels = set(fx.KEY_TO_LEVEL.values())

    assert len(deployed) == 9
    assert deployed == levels
    assert {"Beauty & Wellness", "Transport & Logistics"} <= deployed


def test_feature_lists_match_the_api_contract():
    meta = loader.load_metadata("3M")

    assert fx.FEATURES == meta["feature_names_in_order"]
    assert fx.FEATURES_NUM == meta["numeric_features"] and fx.FEATURES_CAT == meta["categorical_features"]


# --------------------------------------------------------------- features ----
def _toy_panel():
    return _panel([
        {"household_id": "HH-001", "Month_Ord": 672, "Risk_Ord_t": 2.0, "T_No_Profit_Last_Month": 1.0,
         "visit_date": pd.Timestamp("2026-01-15"), "Primary_Pressure_t": 4.0, "Primary_Pressure_t_minus_1": 1.0,
         "Primary_Volatility_t": 2.0, "Primary_Volatility_t_minus_1": 3.0, "Category_Pressure_Tier_Ord_t": 2.0},
        {"household_id": "HH-001", "Month_Ord": 673, "Risk_Ord_t": 1.0, "T_Market_Stress_Any": 1.0,
         "visit_date": pd.Timestamp("2026-02-15"), "grant_date": pd.Timestamp("2026-02-01")},
        {"household_id": "HH-001", "Month_Ord": 675, "Risk_Ord_t": np.nan, "T_No_Profit_Last_Month": np.nan,
         "visit_date": pd.Timestamp("2026-04-15"), "hours_band": "9+ hours a day"},
        {"household_id": "HH-002", "Month_Ord": 673, "Risk_Ord_t": 0.0, "participant_gender": "Female",
         "grant_use_status": "Received, fully used, bills not settled", "visit_date": pd.Timestamp("2026-02-10"),
         "grant_date": pd.Timestamp("2026-03-01")},
    ])


def test_build_features_history_windows_and_grant():
    F = fx.build_features(_toy_panel())

    assert list(F.columns) == fx.FEATURES and list(F.index) == [0, 1, 2, 3]
    assert F["F_Months_Since_Prev_Visit"].tolist()[:3] == [pytest.approx(np.nan, nan_ok=True), 1, 2]
    assert F["F_Prev_Risk_Ord"].tolist()[1:3] == [2.0, 1.0]
    assert F.loc[1, "F_Risk_Change_vs_Prev"] == -1.0
    assert F["F_Tenure_Months"].tolist() == [0, 1, 3, 0]
    assert F["F_N_Prior_Visits"].tolist() == [0, 1, 2, 0]
    # calendar windows: month 675's 3M window is [673, 675] -> excludes month 672
    assert F.loc[2, "F_Risk_Mean_3M_Window"] == 1.0
    assert F.loc[1, "F_Risk_Mean_3M_Window"] == 1.5
    assert F.loc[2, "F_High_Count_6M_Window"] == 1.0
    assert F.loc[2, "F_NoProfit_Rate_3M_Window"] == 0.0
    # grant date carried forward within the household; future grant -> NaN
    assert np.isnan(F.loc[0, "F_Months_Since_Grant"])
    assert F.loc[1, "F_Months_Since_Grant"] == pytest.approx(14 / 30.44)
    assert F.loc[2, "F_Months_Since_Grant"] == pytest.approx(73 / 30.44)
    assert np.isnan(F.loc[3, "F_Months_Since_Grant"])
    # codings
    assert F.loc[2, "F_Hours_Ord_t"] == 3 and F.loc[3, "F_Grant_Status_Ord_t"] == 2 and F.loc[0, "F_Grant_Status_Ord_t"] == 0
    assert F.loc[3, "F_Female_Participant"] == 1 and F.loc[0, "F_Female_Participant"] == 0


def test_build_features_market_and_macro():
    F = fx.build_features(_toy_panel())

    assert F.loc[0, "F_Mkt_Pressure_Change_1M"] == 3.0 and F.loc[0, "F_Mkt_Volatility_Change_1M"] == -1.0
    assert F["F_Mkt_Evidence_Missing"].tolist() == [0, 1, 1, 1]
    assert F.loc[0, "F_Macro_CCPI_YoY_Change_1M"] == pytest.approx(0.5)
    assert F.loc[0, "F_Macro_Food_Index_Change_1M_pct"] == pytest.approx(10.0)
    assert F.loc[0, "F_Macro_Diesel_Change_1M_pct"] == pytest.approx(20.0)


def test_build_targets_use_the_exact_calendar_month():
    panel = _panel([
        {"household_id": "HH-001", "Month_Ord": 672, "Risk_Ord_t": 0.0},
        {"household_id": "HH-001", "Month_Ord": 673, "Risk_Ord_t": 1.0},
        {"household_id": "HH-001", "Month_Ord": 675, "Risk_Ord_t": 2.0},
        {"household_id": "HH-001", "Month_Ord": 676, "Risk_Ord_t": np.nan},
        {"household_id": "HH-002", "Month_Ord": 678, "Risk_Ord_t": 1.0},
    ])

    targets = fx.build_targets(panel)

    assert targets.loc[0, "Risk_Label_3M"] == "High"           # 672 + 3 = 675
    assert pd.isna(targets.loc[1, "Risk_Label_3M"])            # 676 is Unassigned
    assert pd.isna(targets.loc[2, "Risk_Label_3M"])            # 678 has no HH-001 visit
    assert pd.isna(targets.loc[4, "Risk_Label_3M"])            # beyond the last month
    assert targets.loc[0, "Target_Month_3M"] == str(pd.Period(ordinal=675, freq="M"))
    assert targets["Risk_Label_6M"].isna().all()


def test_features_do_not_use_future_visits():
    panel = _toy_panel()

    differences, checked = fx.truncation_differences(panel, fx.build_features(panel))

    assert differences == 0 and checked > 0


def test_model_datasets_sort_and_encode():
    panel = _panel([
        {"household_id": "HH-002", "Month_Ord": 672, "Risk_Ord_t": 0.0},
        {"household_id": "HH-001", "Month_Ord": 672, "Risk_Ord_t": 1.0},
        {"household_id": "HH-002", "Month_Ord": 675, "Risk_Ord_t": 2.0},
        {"household_id": "HH-001", "Month_Ord": 675, "Risk_Ord_t": 0.0},
    ])
    panel["month"] = "2026-01"
    panel["is_new_category"] = False
    panel["is_original"] = True

    data = fx.model_datasets(panel, fx.build_features(panel), fx.build_targets(panel))

    assert data["3M"].household_id.tolist() == ["HH-001", "HH-002"]
    assert data["3M"].y.tolist() == [0, 2]
    assert len(data["6M"]) == 0


# ---------------------------------------------------------- joins / panel ----
def _category_month():
    rows = []
    for basis in ("ALL", "SYNTHETIC"):
        rows.append({"Row_Basis": basis, "Month": "2026-01", "Category_Key": "AGRICULTURE & PLANTATION CROPS",
                     **{c: 1.0 for c in fx.MARKET_COLUMNS}, **{c: 5.0 for c in fx.MACRO_COLUMNS}})
        rows.append({"Row_Basis": basis, "Month": "2026-01", "Category_Key": "TRADE",
                     **{c: None for c in fx.MARKET_COLUMNS}, **{c: 5.0 for c in fx.MACRO_COLUMNS}})
    return pd.DataFrame(rows)


def test_join_market_macro_by_month_and_category():
    month = pd.Series(["2026-01", "2026-01", "2026-01"], index=[10, 11, 12])
    keys = pd.Series(["AGRICULTURE & PLANTATION CROPS", "TRADE", "BEAUTY AND WELLNESS"], index=[10, 11, 12])

    joined = fx.join_market_macro(month, keys, _category_month())

    assert list(joined.index) == [10, 11, 12]
    assert joined.loc[10, "Primary_Pressure_t"] == 1.0
    assert joined.loc[[11, 12], fx.MARKET_COLUMNS].isna().all().all()
    assert (joined[fx.MACRO_COLUMNS] == 5.0).all().all()


def test_join_market_macro_rejects_duplicate_rows():
    table = pd.concat([_category_month(), _category_month().iloc[[0]]])

    with pytest.raises(ValueError, match="duplicate"):
        fx.join_market_macro(pd.Series(["2026-01"]), pd.Series(["TRADE"]), table)


def _training_table(rows):
    base = {**{t: 0.0 for t in fx.T_COLS}, fx.GRANT_DATE_COLUMN: None, "Date of SDO household visit": 46032}
    return pd.DataFrame([{**base, **row} for row in rows])


def test_build_panel_matches_original_panel_and_takes_grant_date():
    cleaned = _cleaned([
        {"visit_id": "V1", "household_id": "HH-001", "monitoring_period": "2026-01", "visit_date": "2026-01-10",
         "category": "AGRICULTURE & PLANTATION CROPS"},
        {"visit_id": "V2", "household_id": "HH-059", "monitoring_period": "2026-01", "visit_date": "2026-01-10",
         "category": "BEAUTY AND WELLNESS"},
        {"visit_id": "V3", "household_id": np.nan, "monitoring_period": "2026-01", "category": "UNASSIGNED"},
    ])
    original = _training_table([
        {"household_key": "SYN-HH-001", "Month": "2026-01", fx.GRANT_DATE_COLUMN: 45658.5},
        {"household_key": None, "Month": "2026-01"},
    ])

    panel, checks = fx.build_panel(cleaned, original, _category_month())

    assert len(panel) == 2 and checks["unkeyed_rows_excluded"] == 1
    assert panel.is_synthetic.all()
    assert panel.is_original.tolist() == [True, False]
    assert panel.is_new_category.tolist() == [False, True]
    assert panel.grant_date.iloc[0] == pd.Timestamp("2025-01-01 12:00")
    assert pd.isna(panel.grant_date.iloc[1])
    assert panel.F_Category.tolist() == ["Agriculture & Plantation Crops", "Beauty & Wellness"]
    assert panel.Primary_Pressure_t.iloc[0] == 1.0 and np.isnan(panel.Primary_Pressure_t.iloc[1])
    assert checks["rows_matched_to_original_panel"] == 1 and checks["visit_date_agreement_vs_original"] == 1.0


def test_build_panel_stops_when_signals_differ_from_the_original():
    cleaned = _cleaned([{"visit_id": "V1", "household_id": "HH-001", "monitoring_period": "2026-01", "profit": False}])
    original = _training_table([{"household_key": "SYN-HH-001", "Month": "2026-01", "T_No_Profit_Last_Month": 0.0}])

    with pytest.raises(ValueError, match="T_\\* signals differ"):
        fx.build_panel(cleaned, original, _category_month())


def test_build_panel_rejects_unknown_categories_and_duplicates():
    unknown = _cleaned([{"visit_id": "V1", "household_id": "HH-001", "monitoring_period": "2026-01", "category": "SPACE"}])
    with pytest.raises(ValueError, match="Unknown category"):
        fx.build_panel(unknown, _training_table([]).assign(household_key=[], Month=[]), _category_month())

    twice = _cleaned([{"visit_id": f"V{i}", "household_id": "HH-001", "monitoring_period": "2026-01"} for i in (1, 2)])
    with pytest.raises(ValueError, match="Duplicate"):
        fx.build_panel(twice, _training_table([]).assign(household_key=[], Month=[]), _category_month())


# ------------------------------------------------------------ xlsx reader ----
def test_excel_serial_to_datetime():
    converted = excel_serial_to_datetime(pd.Series([45658, 45658.5, "2026-02-03", None, "x"], dtype=object))

    assert converted.iloc[0] == pd.Timestamp("2025-01-01")
    assert converted.iloc[1] == pd.Timestamp("2025-01-01 12:00")
    assert converted.iloc[2] == pd.Timestamp("2026-02-03")
    assert converted.iloc[3:].isna().all()


def test_read_xlsx_reads_a_minimal_workbook(tmp_path):
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    path = tmp_path / "tiny.xlsx"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml",
                   f'<workbook xmlns="{main}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                   '<sheets><sheet name="Data" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/sharedStrings.xml", f'<sst xmlns="{main}"><si><t>name</t></si><si><t>value</t></si><si><t>a</t></si></sst>')
        z.writestr("xl/worksheets/sheet1.xml",
                   f'<worksheet xmlns="{main}"><sheetData>'
                   '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1" t="inlineStr"><is><t>flag</t></is></c></row>'
                   '<row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2"><v>1.5</v></c><c r="C2" t="b"><v>1</v></c></row>'
                   '<row r="3"><c r="B3"><v>7</v></c></row>'
                   '</sheetData></worksheet>')

    frames = read_xlsx(path, sheets=["Data"])

    df = frames["Data"]
    assert list(df.columns) == ["name", "value", "flag"]
    assert df.iloc[0].tolist() == ["a", 1.5, True]
    assert df.iloc[1, 0] is None and df.iloc[1, 1] == 7 and df.iloc[1, 2] is None
    with pytest.raises(ValueError, match="not found"):
        read_xlsx(path, sheets=["Missing"])
