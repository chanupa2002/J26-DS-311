# Rules for the shared backend/requirements.txt

1. One file only: backend/requirements.txt. Nobody creates their own
   requirements file or installs packages that are not listed in it.
2. Pin every version: use "lightgbm==4.5.0", never "lightgbm" or
   "lightgbm>=4".
3. Add, do not change: add one new line in your own component's section. Never
   edit, upgrade, or downgrade someone else's line. If you need a different
   version of an existing package, ask the group first.
4. The core section (FastAPI, uvicorn, pydantic, pydantic-settings, supabase,
   httpx, and pytest) is edited only by the leader.
5. Test before opening a PR: in a fresh virtual environment, run
   "pip install -r requirements.txt" and start the server. If either fails, do
   not open the PR.
6. If a PR changes requirements.txt, write which package changed and why in the
   PR description. The leader rejects PRs that change it without saying so.
7. Remove a package only if you added it and your folder no longer uses it.
8. Always use a virtual environment and never commit venv/.
9. Everyone uses the same Python version: 3.11.
10. Never use "pip freeze > requirements.txt"; it overwrites everyone's lines
    and adds sub-dependencies.

## Model files

Rules for model files, notebooks and datasets are in docs/DATA_AND_MODELS_RULES.md.
Train in Colab with the same library versions pinned in this requirements file.
