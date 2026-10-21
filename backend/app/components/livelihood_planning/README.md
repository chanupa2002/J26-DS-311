# Livelihood planning

This FastAPI component recommends livelihood categories, builds a grounded
SWOT and viability summary, and saves beneficiary assessments as drafts.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/livelihood/health` | Component health check |
| POST | `/api/livelihood/recommend` | Return Model 1 top-three recommendations |
| POST | `/api/livelihood/swot` | Return recommendations, SWOT, viability, confidence, and notes |
| POST | `/api/livelihood/plan` | Return the current placeholder plan |
| GET | `/api/livelihood/beneficiaries` | List beneficiary profiles for assessment |
| POST | `/api/livelihood/assess/{beneficiary_id}` | Build and save a draft assessment |
| GET | `/api/livelihood/assessments/{beneficiary_id}` | List saved assessments, newest first |

The beneficiaries response includes `id`, `full_name`, `district`, `age`,
`gender`, `female_headed`, `disability`, `aswesuma_category`, and `is_demo`.
Nullable database values are returned as `null`.

## Data flow

1. Model 1 predicts the top livelihood categories from household and area inputs.
2. Model 2 retrieves grounded facts and viability data for the top category.
3. `/assess/{beneficiary_id}` saves the inputs, recommendations, SWOT,
   viability, notes, and confidence to `livelihood_assessments` with status
   `draft`. The beneficiary name is never stored in `input_snapshot`.

## Setup

From `backend/`, install the shared requirements, configure `backend/.env`, and
start the API with `uvicorn app.main:app --reload`. Keep the supplied Model 1
artifacts in `model_1_recommend/artifacts/`.

Environment variables:

- `SUPABASE_URL` and `SUPABASE_KEY`: beneficiary, fact, score, and assessment data.
- `GEMINI_API_KEY`: Model 2 embeddings and optional text rewriting.
- `GEMINI_TEXT_MODEL`: primary rewrite model.
- `GEMINI_FALLBACK_MODELS`: comma-separated rewrite fallback models.

## Tests

From `backend/` on Windows:

```powershell
.\.venv\Scripts\python.exe -B -m pytest app/components/livelihood_planning --basetemp="$env:TEMP\pt_livelihood" -p no:cacheprovider
```
