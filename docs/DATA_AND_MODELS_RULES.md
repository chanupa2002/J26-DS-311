# Rules for data, notebooks and model files

## 1. What goes in the repo and what does not

| In the repo | NOT in the repo |
|---|---|
| Notebooks (.ipynb) with all outputs cleared | Original or processed datasets (CSV, Excel, Parquet, and similar files) |
| Small trained model files | Notebook outputs that show real rows |
| ml/model_info.json | Large model files |
| ml/DATA_DESCRIPTION.md with column names, types, and meanings, but no real values | .env files and secrets |
| Tiny anonymised sample_data/*.json files | |

## 2. Notebooks

- Store notebooks in backend/app/components/<your_component>/notebooks/.
- Before every commit, clear all outputs. In Colab, use Edit > Clear all
  outputs. In VS Code, use Clear All Outputs. Notebook outputs can contain real
  beneficiary rows.
- Do not paste real records into Markdown cells.
- Do not hard-code private file paths or private links.
- Suggested names are 01_data_exploration.ipynb, 02_training.ipynb, and
  03_evaluation.ipynb.

## 3. Model files

- Small classical models, up to about 25 MB per file, may be committed inside
  your ml/ folder. GitHub rejects any file over 100 MB.
- Large files such as LoRA adapters, LLM weights, and large vector indexes must
  not be committed. Store them in Supabase Storage or a shared drive and write
  the download location in ml/model_info.json under "download_location".
- Prefer native formats such as LightGBM .txt and CatBoost .cbm. If you use
  pickle or joblib, train in Colab with the same library versions pinned in
  backend/requirements.txt. Never load a pickle file from someone you do not
  trust.
- Update ml/model_info.json for every model with the training date, metrics, and
  library versions.

## 4. NDA check

- Models, indexes, or files built from the NDA dataset may count as derived
  data. Anything that stores or reveals real records, such as kNN-type models or
  a RAG index built from real text, needs extra care.
- Confirm with the supervisor that trained models may be stored in this private
  repo. Record the decision here:

[ ] Confirmed on ____ by ____

## 5. Sample data

- sample_data/ holds JSON only. It must be anonymised or synthetic and very
  small, for example under 50 records. Do not put CSV files there.

## 6. Before you commit (checklist)

- [ ] Notebook outputs are cleared.
- [ ] No CSV, Excel, or Parquet files appear in git status.
- [ ] Model files are small and are in your own ml/ folder.
- [ ] model_info.json and DATA_DESCRIPTION.md are updated.
- [ ] .env is not committed.
