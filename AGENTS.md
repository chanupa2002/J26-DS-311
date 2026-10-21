# Rules for AI coding agents in this repo

This repo is a team research project (FastAPI backend, four component folders, one owner per component). These rules apply to every AI coding agent (such as Codex) used by any team member.

## 1. Stay inside your component folder
- Ask the user which component they own if it is not already clear from the conversation. The four components are:
  - beneficiary_selection
  - livelihood_planning
  - evidence_trust
  - market_risk
  (all under backend/app/components/)
- You may create, edit and delete files ONLY inside the folder of the component the user owns.
- You may READ any file in the repo.
- Never create, edit or delete files inside another component's folder.

## 2. Do not touch shared files without the leader's approval
These are shared: backend/app/main.py, backend/app/core/, backend/requirements.txt, docs/, .github/, README.md, .gitignore, AGENTS.md, and everything in frontend/.
If a task needs a change in one of these, STOP and tell the user exactly what change is needed and why. Do not make it unless the user says the project leader has approved it.

## 3. Using another component
To use another component, import and call its public function from its services.py. Never edit its code.

## 4. Secrets and data
- Never create, print, read the contents of, or commit backend/.env, API keys, passwords or any secret.
- Never commit datasets (CSV, Excel, parquet and similar). The dataset is under an NDA.
- Clear notebook outputs before committing notebooks.
- Large model files must not be committed. See docs/DATA_AND_MODELS_RULES.md.

## 5. Git
- Never commit or push directly to main or dev.
- Work on the user's own personal branch and let the user open a Pull Request into dev.
- Do not run git commit or git push unless the user asks.

## 6. Dependencies
- Add new libraries to backend/requirements.txt only by following docs/REQUIREMENTS_RULES.md, and tell the user, because it is a shared file.

## 7. Before finishing any task
List every file you created, changed or deleted, so the user can confirm all of them are inside their own component folder.
