# CLAUDE.md – J26-DS-311 (read this every session)

Project: SUSTAIN livelihood programme, SLIIT IT4010, group J26-DS-311.
My component (IT23234970, Member 4): **explainable market-risk monitoring of livelihood projects after the Samurdhi grant**
(current risk by rule, 3-/6-month future risk by ML, SHAP explanations, 25-district market pressure).
My code lives in `backend/app/components/market_risk/`. Do not change other members' components unless I ask.

## Hard rules
- **Never run git commands** (no add, commit, push, branch, checkout, reset). I run git myself.
- **Never read, print, copy or edit `.env`** or any secret (SUPABASE_KEY, GEMINI_API_KEY, …). Secrets come only from environment variables. Never put a secret in frontend code or in `.env` files of the frontend.
- **Never commit or create in tracked folders**: datasets, CSV/XLSX files, `*.joblib` models, notebooks with outputs, `node_modules`. Model artifacts live in `backend/app/components/market_risk/artifacts_v2/`, which must be in `.gitignore`.
- **Real monitoring data is under an NDA** (`is_synthetic == False` rows in `artifacts_v2/`). Never print, log or quote real rows, and never copy them into test files, fixtures, docs or commits. Tests may read them from `artifacts_v2/` but report only counts and pass/fail. Example rows in code and docs are synthetic (`SIM-HH-…`).
- **Synthetic data must stay labelled**: every API response that comes from a simulated household carries `is_synthetic: true`; the UI shows "Simulated".
- **No hand-typed risk thresholds.** Thresholds come from `artifacts_v2/model_meta.json` and `artifacts_v2/threshold_register.json` (DCS poverty line, FAO / SDG 2.c.1 cut-offs 0.5 / 1.0, Youden alert thresholds).
- **Training–serving parity:** feature code must give the same values as the notebook `SUSTAIN_FE_and_Model_Training.ipynb`. Any change to feature logic needs a parity test.
- Keep the old (viva) endpoints working until I say they can be removed. New work goes under `/v2`.
- **Pull Requests go to `dev`** (the default branch), never to `main`. I open PRs myself.
- **Library versions must match `backend/requirements.txt` exactly.** The v2 models were trained with scikit-learn 1.6.1 and shap 0.54.1. Never change a version pin other members use without asking me; re-training in the backend `.venv` is the safe alternative.
- Before a large change, show me a short plan and wait for my OK.
