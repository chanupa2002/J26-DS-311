"""Retrain the SUSTAIN 3M/6M models from the cleaned monitoring data (CANDIDATE only).

Same method as the notebook (sections 17-21 and 29): sklearn Pipeline, LR and RF
candidates tuned with GroupKFold(4) by household on the training split only,
final test on the latest prediction month (embargoed where possible), plus a
walk-forward comparison of the current RF configuration and the candidate.

Data basis: SYNTHETIC panel (70 households, 9 categories). Never real-world evidence.

Inputs come from environment variables; nothing is read from or written to the repo
except the optional aggregate report (--report). The deployed models in ml/models/
are only read (for the reproduction gate), never written.

    SUSTAIN_CLEANED        path to monitoring_visits_clean.csv
    SUSTAIN_COMBINED       path to combined.xlsx
    SUSTAIN_CANDIDATE_OUT  output folder (default ~/Documents/sustain_data/models_candidate)

From backend/:
    python -m app.components.market_risk.ml.training.train_from_cleaned [--gate-only] [--report PATH]
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.components.market_risk.ml.training import features as fx
from app.components.market_risk.ml.training.xlsx_reader import read_xlsx

RANDOM_STATE = 42
MIN_TRAIN = 80  # notebook section 19-21
WF_MIN_TRAIN, WF_MIN_TEST = 30, 15  # notebook section 29
GATE_TOLERANCE = 5e-5  # metadata metrics are rounded to 4 decimals
PROMOTION_MACRO_F1_MARGIN = 0.02
SAVED_ALGORITHM = "RandomForest"
MODEL_VERSION = "2.0-cleaned-candidate"
# Notebook section 29 E1 (448-row panel): mean walk-forward Macro-F1 of the current RF config and persistence.
WALK_FORWARD_448_EXPECTED = {"3M": {"rf": 0.356, "persistence": 0.295}, "6M": {"rf": 0.431, "persistence": 0.179}}
LABEL_METHOD_VERSION = "SUSTAIN-HH-Risk-Rule v1.0 (provisional, requires expert validation)"

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[6]
CURRENT_MODELS_DIR = HERE.parents[1] / "models"
DEFAULT_CANDIDATE_OUT = Path("~/Documents/sustain_data/models_candidate").expanduser()


# ---------------------------------------------------------------- helpers ----
def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _env_path(name: str, default: Path | None = None) -> Path:
    value = os.environ.get(name)
    if not value and default is None:
        raise SystemExit(f"Set the environment variable {name} (path outside the repo).")
    return Path(value).expanduser() if value else default


def _outside_repo(path: Path) -> Path:
    resolved = path.resolve()
    if resolved == REPO_ROOT or REPO_ROOT in resolved.parents:
        raise SystemExit(f"Refusing to write candidate models inside the repository: {resolved}")
    return resolved


def make_pre():
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    num = Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)), ("sc", StandardScaler())])
    cat = Pipeline([("imp", SimpleImputer(strategy="constant", fill_value="missing")), ("oh", OneHotEncoder(handle_unknown="ignore"))])
    return ColumnTransformer([("num", num, fx.FEATURES_NUM), ("cat", cat, fx.FEATURES_CAT)])


def rf_pipeline(**params):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.pipeline import Pipeline

    forest = RandomForestClassifier(
        n_estimators=300, class_weight="balanced_subsample", random_state=RANDOM_STATE, n_jobs=-1, **params
    )
    return Pipeline([("pre", make_pre()), ("clf", forest)])


def candidates() -> dict[str, tuple[Any, dict]]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    return {
        "LogisticRegression": (
            Pipeline([("pre", make_pre()), ("clf", LogisticRegression(class_weight="balanced", max_iter=5000))]),
            {"clf__C": [0.01, 0.1, 1.0, 10.0]},
        ),
        "RandomForest": (rf_pipeline(), {"clf__max_depth": [3, 5, None], "clf__min_samples_leaf": [1, 5, 10]}),
    }


def metrics(y, p) -> dict[str, float]:
    from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, precision_score, recall_score

    y, p = np.asarray(y), np.asarray(p)
    return {
        "Accuracy": accuracy_score(y, p),
        "Macro_Precision": precision_score(y, p, average="macro", labels=[0, 1, 2], zero_division=0),
        "Macro_Recall": recall_score(y, p, average="macro", labels=[0, 1, 2], zero_division=0),
        "Macro_F1": f1_score(y, p, average="macro", labels=[0, 1, 2], zero_division=0),
        "Balanced_Accuracy": balanced_accuracy_score(y, p),
        "High_Precision": precision_score(y, p, labels=[2], average="macro", zero_division=0),
        "High_Recall": recall_score(y, p, labels=[2], average="macro", zero_division=0),
    }


def macro_f1(y, p) -> float:
    return metrics(y, p)["Macro_F1"]


def persistence_predict(X: pd.DataFrame, fallback: int) -> np.ndarray:
    return X["F_Risk_Ord_t"].fillna(fallback).astype(int).values


def boot_ci(y, p, n: int = 1000, seed: int = RANDOM_STATE) -> str:
    rng = np.random.default_rng(seed)
    y, p = np.asarray(y), np.asarray(p)
    values = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        values.append(macro_f1(y[i], p[i]))
    lo, hi = np.percentile(values, [2.5, 97.5])
    return f"[{lo:.3f}, {hi:.3f}]"


def _month(ordinal: int) -> str:
    return str(pd.Period(ordinal=int(ordinal), freq="M"))


def _class_counts(frame: pd.DataFrame) -> dict[str, int]:
    return {c: int((frame.y == i).sum()) for i, c in enumerate(fx.CLASSES)}


# ------------------------------------------------------- final split + fit ----
def final_split(dd: pd.DataFrame, h: int):
    test_month = dd.Month_Ord.max()
    embargoed = dd[dd.Month_Ord + h <= test_month]
    if len(embargoed) >= MIN_TRAIN and embargoed.y.nunique() == 3:
        train = embargoed
        design = (f"Embargoed: train prediction months whose target month <= test prediction month; "
                  f"test = prediction month {_month(test_month)}")
    else:
        train = dd[dd.Month_Ord < test_month]
        design = (f"NO EMBARGO POSSIBLE (embargoed train would have {len(embargoed)} rows): train = all earlier "
                  f"prediction months; test = prediction month {_month(test_month)}; train targets overlap test period -> optimistic")
    return train, dd[dd.Month_Ord == test_month], design


def fit_and_evaluate(dd: pd.DataFrame, h_name: str) -> dict[str, Any]:
    """Notebook sections 19-21 for one horizon: baselines, LR and RF, selection by CV on train."""
    from sklearn.model_selection import GridSearchCV, GroupKFold

    h = fx.HORIZONS[h_name]
    train, test, design = final_split(dd, h)
    if train.y.nunique() < 3 or test.y.nunique() < 2:
        raise RuntimeError(f"{h_name}: training split lacks a class or test split has <2 classes")
    X_train, y_train, groups = train[fx.FEATURES], train.y.values, train.household_id.values
    X_test, y_test = test[fx.FEATURES], test.y.values
    gkf = GroupKFold(n_splits=4)

    rows, fitted = [], {}
    majority = int(pd.Series(y_train).mode()[0])
    cv_majority, cv_persistence = [], []
    for a, b in gkf.split(X_train, y_train, groups):
        m = int(pd.Series(y_train[a]).mode()[0])
        cv_majority.append(macro_f1(y_train[b], np.full(len(b), m)))
        cv_persistence.append(macro_f1(y_train[b], persistence_predict(X_train.iloc[b], m)))
    p_persistence = persistence_predict(X_test, majority)
    rows.append({"Model": "Baseline: majority class", "Best_params": f"class={fx.CLASSES[majority]}",
                 "CV_Macro_F1_mean": float(np.mean(cv_majority)), **metrics(y_test, np.full(len(y_test), majority))})
    rows.append({"Model": "Baseline: persistence", "Best_params": "-", "CV_Macro_F1_mean": float(np.mean(cv_persistence)),
                 **metrics(y_test, p_persistence)})
    for name, (pipe, grid) in candidates().items():
        search = GridSearchCV(pipe, grid, scoring="f1_macro", cv=gkf, n_jobs=1, refit=True)
        search.fit(X_train, y_train, groups=groups)
        fitted[name] = search.best_estimator_
        params = {k.replace("clf__", ""): v for k, v in search.best_params_.items()}
        rows.append({"Model": name, "Best_params": params, "CV_Macro_F1_mean": float(search.best_score_),
                     **metrics(y_test, search.best_estimator_.predict(X_test))})

    table = pd.DataFrame(rows)
    ml_rows = table[~table.Model.str.startswith("Baseline")]
    selected = ml_rows.loc[ml_rows.CV_Macro_F1_mean.idxmax(), "Model"]
    rf_row = table[table.Model == SAVED_ALGORITHM].iloc[0]
    persistence_row = table[table.Model == "Baseline: persistence"].iloc[0]
    return {
        "horizon": h_name,
        "design": design,
        "embargoed": design.startswith("Embargoed"),
        "train": train,
        "test": test,
        "table": table,
        "selected_by_cv": selected,
        "rf": fitted[SAVED_ALGORITHM],
        "rf_params": rf_row.Best_params,
        "rf_metrics": {k: float(rf_row[k]) for k in metrics([0], [0])},
        "rf_ci": boot_ci(y_test, fitted[SAVED_ALGORITHM].predict(X_test)),
        "persistence_macro_f1": float(persistence_row.Macro_F1),
        "persistence_ci": boot_ci(y_test, p_persistence),
    }


def _same_training_statistics(refit, h_name: str) -> bool:
    """Imputer medians, scaler means/scales, indicators and one-hot levels equal the deployed pipeline's."""
    import joblib

    deployed = joblib.load(CURRENT_MODELS_DIR / h_name / "model.joblib")
    d_num = deployed.named_steps["pre"].named_transformers_["num"]
    r_num = refit.named_steps["pre"].named_transformers_["num"]
    d_cat = deployed.named_steps["pre"].named_transformers_["cat"].named_steps["oh"]
    r_cat = refit.named_steps["pre"].named_transformers_["cat"].named_steps["oh"]
    return bool(
        np.allclose(d_num.named_steps["imp"].statistics_, r_num.named_steps["imp"].statistics_, equal_nan=True)
        and list(d_num.named_steps["imp"].indicator_.features_) == list(r_num.named_steps["imp"].indicator_.features_)
        and np.allclose(d_num.named_steps["sc"].mean_, r_num.named_steps["sc"].mean_, rtol=0, atol=1e-9)
        and np.allclose(d_num.named_steps["sc"].scale_, r_num.named_steps["sc"].scale_, rtol=0, atol=1e-9)
        and all(list(a) == list(b) for a, b in zip(d_cat.categories_, r_cat.categories_))
    )


# ------------------------------------------------------------ walk-forward ----
def walk_forward_folds(dd: pd.DataFrame, h: int):
    for month in sorted(dd.Month_Ord.unique()):
        test = dd[dd.Month_Ord == month]
        embargoed = dd[dd.Month_Ord + h <= month]
        if len(embargoed) >= WF_MIN_TRAIN and embargoed.y.nunique() == 3:
            train, design = embargoed, "embargoed"
        else:
            train, design = dd[dd.Month_Ord < month], "no embargo (optimistic)"
        if len(train) < WF_MIN_TRAIN or train.y.nunique() < 3 or len(test) < WF_MIN_TEST or test.y.nunique() < 2:
            continue
        yield month, train, test, design


def _fold_scores(model, test: pd.DataFrame) -> dict[str, float]:
    p = model.predict(test[fx.FEATURES])
    m = metrics(test.y.values, p)
    return {"Macro_F1": m["Macro_F1"], "High_Recall": m["High_Recall"]}


def walk_forward_compare(dd: pd.DataFrame, h_name: str, current_params: dict, candidate_params: dict) -> pd.DataFrame:
    """Per fold: current RF config trained on original-category rows only vs candidate RF on all rows.

    Both are scored on the same test month: all rows, and original-category rows only.
    """
    h = fx.HORIZONS[h_name]
    rows = []
    for month, train, test, design in walk_forward_folds(dd, h):
        train_original = train[train.is_original]
        majority = int(pd.Series(train.y).mode()[0])
        for scope, scored in (("all test rows", test), ("original-category test rows", test[test.is_original])):
            if len(scored) == 0 or scored.y.nunique() < 2:
                continue
            base = {"Horizon": h_name, "Test_month": _month(month), "Design": design, "Scope": scope,
                    "Train_n_candidate": len(train), "Train_n_current": len(train_original), "Test_n": len(scored)}
            p = persistence_predict(scored, majority)
            m = metrics(scored.y.values, p)
            rows.append({**base, "Model": "Persistence baseline", "Macro_F1": m["Macro_F1"], "High_Recall": m["High_Recall"]})
            if len(train_original) >= WF_MIN_TRAIN and train_original.y.nunique() == 3:
                current = rf_pipeline(**current_params).fit(train_original[fx.FEATURES], train_original.y)
                rows.append({**base, "Model": "Current RF (original 448-row panel)", **_fold_scores(current, scored)})
            candidate = rf_pipeline(**candidate_params).fit(train[fx.FEATURES], train.y)
            rows.append({**base, "Model": "Candidate RF (550-row panel)", **_fold_scores(candidate, scored)})
    return pd.DataFrame(rows)


def walk_forward_original(dd: pd.DataFrame, h_name: str, params: dict) -> pd.DataFrame:
    """Notebook section 29 E1 on the 448-row panel (reproduction check)."""
    h = fx.HORIZONS[h_name]
    rows = []
    for month, train, test, design in walk_forward_folds(dd, h):
        majority = int(pd.Series(train.y).mode()[0])
        m = metrics(test.y.values, persistence_predict(test, majority))
        rows.append({"Horizon": h_name, "Test_month": _month(month), "Design": design, "Model": "Persistence baseline",
                     "Macro_F1": m["Macro_F1"], "High_Recall": m["High_Recall"]})
        model = rf_pipeline(**params).fit(train[fx.FEATURES], train.y)
        rows.append({"Horizon": h_name, "Test_month": _month(month), "Design": design, "Model": "Random Forest (current)",
                     **_fold_scores(model, test)})
    return pd.DataFrame(rows)


def summarise(folds: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    return folds.groupby(by, sort=False).agg(
        Folds=("Macro_F1", "size"), Macro_F1_mean=("Macro_F1", "mean"), High_Recall_mean=("High_Recall", "mean")
    ).reset_index()


# ------------------------------------------------------------ proxy check ----
def grant_proxy_analysis(result: dict[str, Any]) -> dict[str, Any]:
    """Does F_Months_Since_Grant's missing flag act as a proxy for the two new categories?"""
    import shap
    from sklearn.inspection import permutation_importance

    train, test, model = result["train"], result["test"], result["rf"]
    missing = train.F_Months_Since_Grant.isna()
    new = train.is_new_category.astype(bool)

    perm = permutation_importance(model, test[fx.FEATURES], test.y, scoring="f1_macro", n_repeats=50, random_state=RANDOM_STATE)
    perm_rank = pd.Series(perm.importances_mean, index=fx.FEATURES).rank(ascending=False, method="min")

    transformed = model[:-1].transform(train[fx.FEATURES])
    names = list(model[:-1].get_feature_names_out())
    values = np.asarray(shap.TreeExplainer(model[-1]).shap_values(transformed))  # (rows, columns, classes)
    mean_abs = pd.Series(np.abs(values).sum(axis=2).mean(axis=0), index=names)
    rank = mean_abs.rank(ascending=False, method="min")
    indicator = "num__missingindicator_F_Months_Since_Grant"
    value_col = "num__F_Months_Since_Grant"
    high = fx.CLASS_TO_INT["High"]
    out = {
        "horizon": result["horizon"],
        "train_rows": int(len(train)),
        "missing_rate_new_categories": float(missing[new].mean()) if new.any() else None,
        "missing_rate_original_categories": float(missing[~new].mean()),
        "share_of_missing_rows_in_new_categories": float(new[missing].mean()) if missing.any() else None,
        "permutation_importance_test_macro_f1": {
            f: {"mean": float(perm.importances_mean[fx.FEATURES.index(f)]), "sd": float(perm.importances_std[fx.FEATURES.index(f)]),
                "rank_of_53": int(perm_rank[f])}
            for f in ("F_Months_Since_Grant", "F_Category")
        },
        "shap_columns": len(names),
    }
    for label, column in (("missing_indicator", indicator), ("value", value_col)):
        if column in names:
            j = names.index(column)
            out[f"shap_{label}"] = {
                "mean_abs_all_classes": float(mean_abs[column]),
                "rank": int(rank[column]),
                "mean_high_contribution_new_categories": float(values[new.values, j, high].mean()) if new.any() else None,
                "mean_high_contribution_original_categories": float(values[~new.values, j, high].mean()),
            }
        else:
            out[f"shap_{label}"] = None
    category_columns = [n for n in names if n.startswith("cat__F_Category_")]
    out["shap_F_Category_all_levels_mean_abs"] = float(mean_abs[category_columns].sum())
    out["shap_top10"] = [{"column": n, "mean_abs": float(v)} for n, v in mean_abs.sort_values(ascending=False).head(10).items()]
    return out


def proxy_verdict(proxy: dict[str, Any]) -> str:
    """Plain verdict: is the missing flag a strong driver of the candidate model?"""
    indicator = proxy["shap_missing_indicator"]
    perm = proxy["permutation_importance_test_macro_f1"]["F_Months_Since_Grant"]
    top10 = indicator is not None and indicator["rank"] <= 10
    perm_signal = perm["mean"] > 0.01 and perm["mean"] > 2 * perm["sd"]
    if top10 or perm_signal:
        return ("possible proxy: the missing flag is a strong driver (top-10 SHAP column or clear permutation importance); "
                "review before promotion")
    return ("not a strong proxy in this model: the flag is fully confounded with the new categories, but it is outside the "
            "top-10 SHAP columns and its permutation importance is within noise")


# ------------------------------------------------------------------- save ----
def software_versions() -> dict[str, str]:
    import joblib
    import shap
    import sklearn

    return {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
            "scikit-learn": sklearn.__version__, "joblib": joblib.__version__, "shap": shap.__version__}


def build_metadata(result: dict[str, Any], current_meta: dict, hashes: dict[str, str]) -> dict[str, Any]:
    h_name, train = result["horizon"], result["train"]
    reasons = ["trained and tested only on SYNTHETIC rows (source: 'do not use them as evidence')",
               "target rule is new and not validated by experts",
               "no real household can be followed over time (no persistent ID)",
               "candidate model from the cleaned data, not promoted"]
    if result["rf_metrics"]["Macro_F1"] <= result["persistence_macro_f1"]:
        reasons.append("does not beat the persistence baseline on the test month")
    if not result["embargoed"]:
        reasons.append("test split could not be embargoed (optimistic)")
    return {
        "model_name": f"SUSTAIN_Model_{h_name}",
        "model_version": MODEL_VERSION,
        "horizon_months": fx.HORIZONS[h_name],
        "target": f"Risk_Label_{h_name}",
        "classes": fx.CLASSES,
        "class_encoding": fx.CLASS_TO_INT,
        "algorithm": SAVED_ALGORITHM,
        "selected_by_cv": result["selected_by_cv"],
        "best_params": result["rf_params"],
        "feature_names_in_order": fx.FEATURES,
        "numeric_features": fx.FEATURES_NUM,
        "categorical_features": fx.FEATURES_CAT,
        "categorical_levels": {c: sorted(train[c].dropna().unique().tolist()) for c in fx.FEATURES_CAT},
        "target_generation_method": LABEL_METHOD_VERSION,
        "target_rule": current_meta["target_rule"],
        "category_mapping": fx.KEY_TO_LEVEL,
        "training_period": {"prediction_months": f"{train.month.min()}..{train.month.max()}",
                            "target_months": f"{train[f'Target_Month_{h_name}'].min()}..{train[f'Target_Month_{h_name}'].max()}"},
        "validation_methodology": result["design"] + "; tuning by GroupKFold(4) by household within training set",
        "test_metrics": {k: round(v, 4) for k, v in result["rf_metrics"].items()},
        "test_macro_f1_95ci": result["rf_ci"],
        "persistence_baseline_test_macro_f1": round(result["persistence_macro_f1"], 4),
        "train_n": int(len(train)),
        "test_n": int(len(result["test"])),
        "data_basis": fx.DATA_BASIS,
        "deployment_status": "NOT_READY",
        "deployment_reason": "; ".join(reasons),
        "input_sha256": hashes,
        "software_versions": software_versions(),
        "source": "ml/training/train_from_cleaned.py",
        "created": dt.datetime.now().isoformat(timespec="seconds"),
    }


def save_candidate(out_dir: Path, h_name: str, model, metadata: dict) -> Path:
    import joblib

    folder = out_dir / h_name
    folder.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, folder / "model.joblib")
    (folder / "metadata.json").write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
    schema = (CURRENT_MODELS_DIR / h_name / "feature_schema.json").read_text(encoding="utf-8")
    (folder / "feature_schema.json").write_text(schema, encoding="utf-8")
    return folder


# ------------------------------------------------------------------ report ----
def _fmt(value: Any) -> str:
    return f"{value:.3f}" if isinstance(value, float) else str(value)


def _md_table(frame: pd.DataFrame) -> str:
    header = "| " + " | ".join(frame.columns) + " |"
    rule = "|" + "|".join("---" for _ in frame.columns) + "|"
    body = ["| " + " | ".join(_fmt(v) for v in row) + " |" for row in frame.itertuples(index=False)]
    return "\n".join([header, rule, *body])


def write_report(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# market_risk: retrain report (cleaned data)",
        "",
        f"Generated {report['created']} by `ml/training/train_from_cleaned.py`. Aggregates only: no rows, IDs or data values.",
        "",
        f"> **Data basis: {fx.DATA_BASIS}. Not real-world evidence.** Candidate models are NOT_READY and are stored "
        "outside the repo. The deployed models in `ml/models/` were not changed.",
        "",
        "## Input checks",
        "",
        _md_table(pd.DataFrame([{"Check": k, "Result": json.dumps(v) if isinstance(v, dict) else v} for k, v in report["checks"].items()])),
        "",
        "## 1. Reproduction gate (448 original synthetic rows)",
        "",
        _md_table(pd.DataFrame(report["gate"]["rows"])),
        "",
        f"**Gate: {'PASS' if report['gate']['passed'] else 'FAIL'}**. Required: the same split sizes; training statistics equal to "
        "the deployed pipeline's (imputer medians, scaler means/scales, missing indicators, one-hot levels); test Macro-F1 and "
        f"High recall of the deployed configuration within {GATE_TOLERANCE} of `ml/models/*/metadata.json`; and the notebook "
        "section 29 walk-forward means reproduced.",
        "",
        "Grid search on this machine (reported, not gated):",
        "",
        _md_table(pd.DataFrame(report["gate"]["grid_selection"])),
        "",
        "The grid search does not reproduce the Colab choice exactly. The data are identical, but about 10 of 300 trees choose "
        "differently between exactly tied, duplicate columns (for example the missing flags of `F_Mkt_Volatility_t` and "
        "`F_Mkt_Volatility_Tier_Ord_t`, or diesel price and diesel change), which is floating-point and platform dependent. On "
        "the small folds this re-orders near-tied CV scores. Hyperparameter choice is therefore unstable at this sample size.",
        "",
        "Notebook section 29 walk-forward on the same 448 rows (notebook: 3M RF 0.356 vs persistence 0.295, High recall 0.44 vs "
        "0.19; 6M RF 0.431 vs 0.179):",
        "",
        _md_table(pd.DataFrame(report["gate"]["walk_forward_448"])),
        "",
    ]
    if "candidate" in report:
        c = report["candidate"]
        lines += [
            "## 2. Candidate training (550 keyed synthetic rows)",
            "",
            _md_table(pd.DataFrame(c["splits"])),
            "",
            "Model comparison on the final test month (all candidates as in the notebook; **only the Random Forest is saved**):",
            "",
            _md_table(pd.DataFrame(c["comparison"])),
            "",
            "## 3. Walk-forward: current vs candidate (mean over test months)",
            "",
            "Current = the deployed RF configuration retrained per fold on the original-category rows only. "
            "Candidate = the candidate RF configuration retrained per fold on all rows. Both are scored on the same test months.",
            "",
            _md_table(pd.DataFrame(c["walk_forward_summary"])),
            "",
            "Per fold (all test rows):",
            "",
            _md_table(pd.DataFrame(c["walk_forward_folds"])),
            "",
            "## 4. Promotion bar",
            "",
            _md_table(pd.DataFrame(c["promotion"]["rows"])),
            "",
            f"**Promotion bar (model metrics): {'MET' if c['promotion']['passed'] else 'NOT MET'}**. "
            f"Rule: gate passes; candidate walk-forward Macro-F1 >= current - {PROMOTION_MACRO_F1_MARGIN}; candidate High recall >= current "
            "(all test rows, mean over folds). All tests must also pass; that is checked separately with pytest.",
            "",
            "## 5. Does F_Months_Since_Grant's missing flag act as a proxy for the new categories?",
            "",
        ]
        for proxy in c["grant_proxy"]:
            perm = proxy["permutation_importance_test_macro_f1"]
            ind = proxy["shap_missing_indicator"]
            lines += [
                f"**{proxy['horizon']}** (candidate RF, {proxy['train_rows']} training rows, {proxy['shap_columns']} model columns)",
                "",
                f"- Missing rate: new categories {_fmt(proxy['missing_rate_new_categories'])}, original categories "
                f"{_fmt(proxy['missing_rate_original_categories'])}; share of missing rows that are new-category: "
                f"{_fmt(proxy['share_of_missing_rows_in_new_categories'])}.",
                f"- Permutation importance on the test month (drop in Macro-F1, 50 repeats): F_Months_Since_Grant "
                f"{perm['F_Months_Since_Grant']['mean']:+.4f} ± {perm['F_Months_Since_Grant']['sd']:.4f} (rank {perm['F_Months_Since_Grant']['rank_of_53']} of 53); "
                f"F_Category {perm['F_Category']['mean']:+.4f} ± {perm['F_Category']['sd']:.4f} (rank {perm['F_Category']['rank_of_53']}).",
            ]
            if ind:
                lines.append(
                    f"- SHAP (training rows), missing indicator: mean |SHAP| {ind['mean_abs_all_classes']:.4f} (rank {ind['rank']} of "
                    f"{proxy['shap_columns']}); mean contribution to P(High): new categories {ind['mean_high_contribution_new_categories']:+.4f}, "
                    f"original categories {ind['mean_high_contribution_original_categories']:+.4f}."
                )
            else:
                lines.append("- SHAP: no missing-indicator column in this model.")
            val = proxy["shap_value"]
            if val:
                lines.append(f"- SHAP, grant-months value column: mean |SHAP| {val['mean_abs_all_classes']:.4f} (rank {val['rank']}).")
            lines += [f"- SHAP, all F_Category one-hot columns together: mean |SHAP| {proxy['shap_F_Category_all_levels_mean_abs']:.4f}.",
                      f"- **Verdict: {proxy_verdict(proxy)}**", ""]
        lines += [
            "## 6. Candidate files (outside the repo)",
            "",
            *[f"- `{h}`: `$SUSTAIN_CANDIDATE_OUT/{h}/` (model.joblib, metadata.json, feature_schema.json)" for h in c["saved"]],
            "- `$SUSTAIN_CANDIDATE_OUT/training_report.json`: the same aggregates as this report",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")


# -------------------------------------------------------------------- main ----
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gate-only", action="store_true", help="run only the reproduction gate on the 448 original rows")
    parser.add_argument("--force", action="store_true", help="train the candidate even if the gate fails")
    parser.add_argument("--report", type=Path, help="write the aggregate Markdown report here")
    args = parser.parse_args(argv)

    cleaned_path = _env_path("SUSTAIN_CLEANED")
    combined_path = _env_path("SUSTAIN_COMBINED")
    out_dir = _outside_repo(_env_path("SUSTAIN_CANDIDATE_OUT", DEFAULT_CANDIDATE_OUT))

    print("Loading inputs (paths from environment variables) ...")
    cleaned = pd.read_csv(cleaned_path)
    sheets = read_xlsx(combined_path, sheets=["Training_Table_HH_Month", "Category_Month_Table"])
    hashes = {"cleaned": _sha256(cleaned_path), "combined": _sha256(combined_path)}

    panel, checks = fx.build_panel(cleaned, sheets["Training_Table_HH_Month"], sheets["Category_Month_Table"])
    features = fx.build_features(panel)
    differences, checked = fx.truncation_differences(panel, features)
    checks["leakage_truncation_test"] = f"{differences} differences in {checked} values"
    if differences:
        raise SystemExit(f"STOP: leakage truncation test failed ({differences} differences)")

    original = panel[panel.is_original]
    data_448 = fx.model_datasets(original, features.loc[original.index], fx.build_targets(original))
    data_all = fx.model_datasets(panel, features, fx.build_targets(panel))
    for name, data in (("448", data_448), ("550", data_all)):
        for h_name, dd in data.items():
            checks[f"eligible_{h_name}_{name}_rows"] = f"{len(dd)} {_class_counts(dd)}"

    current_meta = {h: json.loads((CURRENT_MODELS_DIR / h / "metadata.json").read_text(encoding="utf-8")) for h in fx.HORIZONS}
    report: dict[str, Any] = {"created": dt.datetime.now().isoformat(timespec="seconds"), "checks": checks}

    # 1. reproduction gate
    print("Reproduction gate on the 448 original rows ...")
    gate_rows, grid_rows, gate_ok = [], [], True
    wf_448 = pd.concat([walk_forward_original(data_448[h], h, current_meta[h]["best_params"]) for h in fx.HORIZONS])
    wf_448_summary = summarise(wf_448, ["Horizon", "Model"])
    for h_name in fx.HORIZONS:
        meta = current_meta[h_name]
        train, test, _ = final_split(data_448[h_name], fx.HORIZONS[h_name])
        refit = rf_pipeline(**meta["best_params"]).fit(train[fx.FEATURES], train.y)
        refit_metrics = metrics(test.y.values, refit.predict(test[fx.FEATURES]))
        stats_ok = _same_training_statistics(refit, h_name)
        expected_wf = WALK_FORWARD_448_EXPECTED[h_name]
        got_wf = wf_448_summary[(wf_448_summary.Horizon == h_name) & (wf_448_summary.Model == "Random Forest (current)")].iloc[0]
        persistence_wf = wf_448_summary[(wf_448_summary.Horizon == h_name) & (wf_448_summary.Model == "Persistence baseline")].iloc[0]
        wf_ok = (abs(got_wf.Macro_F1_mean - expected_wf["rf"]) < 5e-4 and abs(persistence_wf.Macro_F1_mean - expected_wf["persistence"]) < 5e-4)
        sizes_ok = len(train) == meta["train_n"] and len(test) == meta["test_n"]
        f1_ok = abs(refit_metrics["Macro_F1"] - meta["test_metrics"]["Macro_F1"]) <= GATE_TOLERANCE
        hr_ok = abs(refit_metrics["High_Recall"] - meta["test_metrics"]["High_Recall"]) <= GATE_TOLERANCE
        ok = sizes_ok and stats_ok and f1_ok and hr_ok and wf_ok
        gate_ok &= ok
        gate_rows.append({"Horizon": h_name, "Train/test": f"{len(train)}/{len(test)} (expected {meta['train_n']}/{meta['test_n']})",
                          "Training statistics = deployed pipeline": "yes" if stats_ok else "no",
                          "Test Macro-F1, deployed config": f"{refit_metrics['Macro_F1']:.4f} (expected {meta['test_metrics']['Macro_F1']})",
                          "Test High recall": f"{refit_metrics['High_Recall']:.4f} (expected {meta['test_metrics']['High_Recall']})",
                          "Section 29 walk-forward RF / persistence": f"{got_wf.Macro_F1_mean:.3f} / {persistence_wf.Macro_F1_mean:.3f} "
                                                                       f"(expected {expected_wf['rf']} / {expected_wf['persistence']})",
                          "Result": "PASS" if ok else "FAIL"})
        searched = fit_and_evaluate(data_448[h_name], h_name)
        grid_rows.append({"Horizon": h_name, "Grid-selected RF params here": json.dumps(searched["rf_params"]),
                          "Notebook (Colab) params": json.dumps(meta["best_params"]),
                          "Same": "yes" if searched["rf_params"] == meta["best_params"] else "no",
                          "Test Macro-F1 with params selected here": round(searched["rf_metrics"]["Macro_F1"], 4)})
    report["gate"] = {"passed": bool(gate_ok), "rows": gate_rows, "grid_selection": grid_rows,
                      "walk_forward_448": wf_448_summary.round(3).to_dict("records")}
    print(f"Gate: {'PASS' if gate_ok else 'FAIL'}")

    if not args.gate_only:
        if not gate_ok and not args.force:
            raise SystemExit("STOP: reproduction gate failed; candidate not trained (use --force to override)")
        # 2. candidate on all keyed rows
        print("Training candidate on all keyed rows ...")
        candidate: dict[str, Any] = {"splits": [], "comparison": [], "saved": {}, "grant_proxy": []}
        results = {}
        for h_name in fx.HORIZONS:
            result = fit_and_evaluate(data_all[h_name], h_name)
            results[h_name] = result
            candidate["splits"].append({"Horizon": h_name, "Design": result["design"], "Train_n": len(result["train"]),
                                        "Test_n": len(result["test"]), "Train classes": json.dumps(_class_counts(result["train"])),
                                        "Test classes": json.dumps(_class_counts(result["test"]))})
            for row in result["table"].to_dict("records"):
                candidate["comparison"].append({"Horizon": h_name, "Model": row["Model"],
                                                "Params": json.dumps(row["Best_params"]) if isinstance(row["Best_params"], dict) else row["Best_params"],
                                                "CV Macro-F1 (train)": round(row["CV_Macro_F1_mean"], 3),
                                                "Test Macro-F1": round(row["Macro_F1"], 3), "Test High recall": round(row["High_Recall"], 3),
                                                "Test High precision": round(row["High_Precision"], 3),
                                                "Selected by CV": row["Model"] == result["selected_by_cv"],
                                                "Saved": row["Model"] == SAVED_ALGORITHM})
            metadata = build_metadata(result, current_meta[h_name], hashes)
            candidate["saved"][h_name] = str(save_candidate(out_dir, h_name, result["rf"], metadata))
            candidate["grant_proxy"].append(grant_proxy_analysis(result))

        # 3. walk-forward comparison
        print("Walk-forward comparison current vs candidate ...")
        folds = pd.concat([walk_forward_compare(data_all[h], h, current_meta[h]["best_params"], results[h]["rf_params"])
                           for h in fx.HORIZONS])
        summary = summarise(folds, ["Horizon", "Scope", "Model"])
        candidate["walk_forward_summary"] = summary.round(3).to_dict("records")
        candidate["walk_forward_folds"] = (folds[folds.Scope == "all test rows"]
                                           [["Horizon", "Test_month", "Design", "Model", "Train_n_current", "Train_n_candidate", "Test_n", "Macro_F1", "High_Recall"]]
                                           .round(3).to_dict("records"))

        promotion_rows, promotion_ok = [], bool(gate_ok)
        for h_name in fx.HORIZONS:
            s = summary[(summary.Horizon == h_name) & (summary.Scope == "all test rows")].set_index("Model")
            cur, cand = s.loc["Current RF (original 448-row panel)"], s.loc["Candidate RF (550-row panel)"]
            f1_ok = cand.Macro_F1_mean >= cur.Macro_F1_mean - PROMOTION_MACRO_F1_MARGIN
            hr_ok = cand.High_Recall_mean >= cur.High_Recall_mean
            promotion_ok &= bool(f1_ok and hr_ok)
            promotion_rows.append({"Horizon": h_name, "Current Macro-F1": round(cur.Macro_F1_mean, 3), "Candidate Macro-F1": round(cand.Macro_F1_mean, 3),
                                   f"Macro-F1 within {PROMOTION_MACRO_F1_MARGIN}": "yes" if f1_ok else "no",
                                   "Current High recall": round(cur.High_Recall_mean, 3), "Candidate High recall": round(cand.High_Recall_mean, 3),
                                   "High recall not lower": "yes" if hr_ok else "no"})
        candidate["promotion"] = {"passed": promotion_ok, "rows": promotion_rows}
        report["candidate"] = candidate

    (out_dir / "training_report.json").parent.mkdir(parents=True, exist_ok=True)
    (out_dir / "training_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    if args.report:
        write_report(report, args.report)
        print(f"Report written to {args.report}")
    print(f"Aggregate JSON report: {out_dir / 'training_report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
