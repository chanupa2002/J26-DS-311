# SWSS — Social Welfare Support System

SWSS is an AI-driven decision-support system for Sri Lanka's Community
Empowerment Program, a World Bank-funded livelihood pilot run by the Department
of Samurdhi Development. It supports officers across the beneficiary lifecycle:
prioritising vulnerable households, recommending suitable livelihoods and
family development plans, assessing the trustworthiness of progress evidence,
and identifying market risk. Outputs are designed to be explainable and to
support—not replace—human decisions.

The planned application uses a React.js frontend, a Python FastAPI backend, and
Supabase (PostgreSQL). Models are trained separately in Google Colab and exported
to the relevant backend component.

## Team and ownership

| Component | Folder | URL prefix | Owner GitHub |
|---|---|---|---|
| Beneficiary Selection Support | beneficiary_selection | /api/beneficiary | @wichitawolf |
| Livelihood Recommendation and Family Development Planning | livelihood_planning | /api/livelihood | @chanupa2002 |
| Explainable Evidence Trust Scoring and Recommendation Framework | evidence_trust | /api/trust | @Punsandali |
| Explainable Market-Risk Prediction, Recommendation and Decision Dashboard | market_risk | /api/risk | @Chamosithmini |

## Repository layout

    frontend/          React.js application (to be added later)
    backend/           FastAPI application and component placeholders
    docs/              Shared dependency rules and component contracts
    .github/           GitHub ownership configuration

## Quick start

See [backend/README.md](backend/README.md) for setup, local development, and test
commands.

## Git Workflow

1. Work on your personal branch: chanupa, ishini, chamoda, or punsandali. Edit
   only files inside your own component folder; you may read and use everything
   else.
2. Never push directly to main or dev.
3. While on your personal branch, regularly run `git pull origin dev` to stay up
   to date.
4. Open Pull Requests from your personal branch into `dev`, never into `main`.
5. Only the project leader (@chanupa2002) merges Pull Requests into `dev`.
6. At milestones, such as progress presentations, the leader merges `dev` into
   `main` using **Create a merge commit**, not squash.

## Confidentiality

Never commit the beneficiary dataset covered by the NDA, raw or private data,
credentials, environment files, or other secrets. Only small, anonymised sample
JSON may be placed in a component's sample_data/ folder.

## Shared project rules

- [Rules for backend dependencies](docs/REQUIREMENTS_RULES.md)
- [Rules for data, notebooks, and model files](docs/DATA_AND_MODELS_RULES.md)
- [API, service, and database contracts](docs/CONTRACTS.md)
