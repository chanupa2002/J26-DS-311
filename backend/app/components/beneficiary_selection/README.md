# Component 1 local scored-model API

Research output - not an eligibility determination

This API is implemented inside the existing `beneficiary_selection` backend component and uses the repository's existing backend environment and dependencies. It does not read or modify `.env` values. The API router is registered in the shared backend app, so the endpoints and candidate page are available when the project backend runs. From `backend/`, start the shared app locally with `uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log`. Open `/` for the candidate page, `/docs` for the shared OpenAPI UI, or `/openapi.yaml` for this component's contract. For isolated component development, use `uvicorn app.components.beneficiary_selection.run_model_dev:app --host 127.0.0.1 --port 8001 --no-access-log`. Set `COMPONENT1_API_SYNTHETIC=1` in the process environment to force fake data; the default loads Stage 5 files when available and falls back to generated synthetic records.

Routes: `GET /households` (paged, filtered), `GET /households/{row_id}`, `GET /summary`, `POST /whatif`, `GET /sensitivity`, `GET /spec`, `GET /model-info`, and `GET /health`. Every API response carries the research label, model/spec versions, manifest SHA-256, and data mode. Household codes are not returned. Aggregate cells below 10 are suppressed.

`/whatif` converts supplied degrees with the fuzzy engine's existing `soft_levels` and calls the existing `bn_v0_1.score` using `config_v02_interim()`. The candidate page inserts the result in a temporary comparison against saved baseline scores and reports a rank and percentile; nothing is persisted or recomputed for saved sensitivity scenarios. No score is validated for decision use.

From `backend/`, run the component tests with `python -B -m pytest -q -p no:cacheprovider app/components/beneficiary_selection/tests`.
