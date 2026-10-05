# SWSS Backend

Run all commands in this guide from the backend/ folder.

## Quick start on Windows PowerShell

    py -3.11 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    Copy-Item .env.example .env
    uvicorn app.main:app --reload

Open http://localhost:8000/docs.

## Quick start on macOS or Linux

    python3.11 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt
    cp .env.example .env
    uvicorn app.main:app --reload

Open http://localhost:8000/docs.

## Run one component

Each component can start alone so unfinished work elsewhere does not block local
development:

    uvicorn app.components.beneficiary_selection.run_dev:app --reload --port 8001
    uvicorn app.components.livelihood_planning.run_dev:app --reload --port 8002
    uvicorn app.components.evidence_trust.run_dev:app --reload --port 8003
    uvicorn app.components.market_risk.run_dev:app --reload --port 8004

Open the matching /docs URL on the selected port.

## Run tests

    python -m pytest

## Add an endpoint

Edit only your component's router.py, schemas.py, and services.py. Keep request
and response shapes in schemas.py, HTTP endpoints in router.py, and component
logic in services.py.

Before adding or changing a package, read
[the shared requirements rules](../docs/REQUIREMENTS_RULES.md).
