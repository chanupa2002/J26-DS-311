
"""SUSTAIN 3M/6M risk model loader with input validation."""
import json, os, warnings
import joblib, numpy as np, pandas as pd

def load_model(folder):
    with open(os.path.join(folder, "metadata.json")) as f: meta = json.load(f)
    model = joblib.load(os.path.join(folder, "model.joblib"))
    if meta.get("deployment_status") != "READY":
        warnings.warn(f"Model status is {meta.get('deployment_status')}: {meta.get('deployment_reason')}")
    return model, meta

def validate_input(df, meta):
    req = meta["feature_names_in_order"]; issues = []
    missing = [c for c in req if c not in df.columns]
    if missing: raise ValueError(f"Missing required columns: {missing}")
    X = df[req].copy()
    for c in meta["numeric_features"]:
        before = X[c].notna().sum(); X[c] = pd.to_numeric(X[c], errors="coerce")
        if X[c].notna().sum() < before: issues.append(f"{c}: non-numeric values set to missing")
    for c, allowed in meta["categorical_levels"].items():
        X[c] = X[c].astype(object).where(X[c].notna(), np.nan)
        unk = sorted(set(X[c].dropna()) - set(allowed))
        if unk: issues.append(f"{c}: unseen categories {unk} -> encoded as all-zero (handle_unknown='ignore')")
    for i in issues: warnings.warn(i)
    return X, issues

def predict(df, folder):
    model, meta = load_model(folder)
    X, issues = validate_input(df, meta)
    proba = model.predict_proba(X)
    out = pd.DataFrame(proba, columns=[f"P_{c}" for c in meta["classes"]], index=df.index)
    out["Predicted_Risk"] = [meta["classes"][i] for i in proba.argmax(axis=1)]
    out["Model_Status"] = meta["deployment_status"]
    return out
