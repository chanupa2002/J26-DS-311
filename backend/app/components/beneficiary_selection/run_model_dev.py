"""Run the local Component 1 model API in the Beneficiary Selection component.

From backend/: uvicorn app.components.beneficiary_selection.run_model_dev:app
  --host 127.0.0.1 --port 8001 --no-access-log
"""
from app.components.beneficiary_selection.model_api import app
