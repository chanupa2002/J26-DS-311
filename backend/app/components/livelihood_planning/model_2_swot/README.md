# Model 2: SWOT and viability

Model 2 is a retrieval and scoring service, not a trained predictive model. It
uses approved Supabase facts and stored viability scores.

## Behaviour

1. Read matching livelihood, district, area, risk, and forecast facts from
   `livelihood_facts`. Semantic similarity is optional.
2. Rank facts with transparent adjustments and keep at most three per SWOT
   category. Weak risk facts are not shown as Opportunities.
3. Return `evidence` as the unchanged fact statement. `strength` is `weak` when
   it contains `(weak signal)` and `clear` otherwise.
4. Gemini may rewrite `text` for readability. Grounding rejects new numbers;
   failures and ungrounded output use the original statement.
5. Read scores from `livelihood_scores`. The matching district viability fact
   controls `estimated`; a missing district or fact means `estimated=true`,
   adds a monitoring note, and makes Model 2 confidence low.

Unknown districts still return a result with low confidence. Supabase failures
produce empty fact groups and estimated viability. Gemini retries 429/503
responses with short waits, skips unavailable models, tries configured fallback
models, and uses the original facts after the shared 15-second limit.

## Environment variables

- `SUPABASE_URL`, `SUPABASE_KEY`: facts and viability scores.
- `GEMINI_API_KEY`: embeddings and rewriting.
- `GEMINI_TEXT_MODEL`: primary text model; default `gemini-2.5-flash-lite`.
- `GEMINI_FALLBACK_MODELS`: comma-separated fallbacks; defaults to
  `gemini-3.5-flash-lite,gemini-flash-lite-latest`.

Embeddings use `gemini-embedding-001` with 768 dimensions.

## Limitations

- Output quality depends on fact-bank and monitoring coverage.
- Scores and confidence are decision support, not guaranteed outcomes.
- Rewrites explain retrieved evidence; they do not prove causes.
- Missing services reduce detail but do not invent evidence.
