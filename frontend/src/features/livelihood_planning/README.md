# Livelihood Planning frontend

## Pages

- `/livelihood/beneficiaries` lists beneficiary summaries and opens assessments.
- `/livelihood/assess` and `/livelihood/assess/:beneficiaryId` run and save draft assessments.
- `/livelihood/recommend` runs Model 1 recommendations without saving.
- `/livelihood/swot` runs recommendations, SWOT, and viability without saving.
- `/livelihood/history` shows saved assessments for a beneficiary.
- Plan remains disabled and has no route.

## Endpoints used

- `GET /api/livelihood/beneficiaries`
- `POST /api/livelihood/assess/{beneficiary_id}`
- `GET /api/livelihood/assessments/{beneficiary_id}`
- `POST /api/livelihood/recommend`
- `POST /api/livelihood/swot`

The shared API helper reads the backend address from `VITE_API_URL`.
The beneficiaries response supplies `female_headed`, `disability`,
`aswesuma_category`, and `is_demo` in addition to the existing profile fields.
Boolean values display as Yes or No, and nullable values display as `—`.

## Test locally

Start the backend on port 8000, then run:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173`, sign in, and use the Livelihood Planning menu.
Run `npm run lint` and `npm run build` before submitting changes.
