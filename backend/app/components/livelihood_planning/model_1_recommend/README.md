# Model 1: livelihood recommendation

Recommends suitable livelihood categories from approved household features.
The model is trained once in Google Colab and loaded lazily from a saved artifact.
Its approved training data is documented in DATA_DESCRIPTION.md; no real data belongs here.

## Required package versions

- model_v1.joblib was trained in Google Colab with scikit-learn 1.6.1.
- The backend must run scikit-learn==1.6.1, tested together with numpy 2.0.2,
  pandas 2.2.3, joblib 1.4.2, and scipy 1.14.1 on Python 3.11. Otherwise,
  the model file may not load.
- If scikit-learn is upgraded, retrain in Colab and replace the model file.

## Explanations

- Reasons come from the Logistic Regression itself: input value x learned
  weight, grouped by the original input feature.
- They show what the model weighted for a recommendation, not proven causes.
- Confidence is low when the top score is below 0.30 or the gap between the
  first two scores is below 0.05. These rules can be tuned with
  `LOW_CONFIDENCE_TOP_SCORE` and `LOW_CONFIDENCE_GAP` in `predict.py`.

## Experiments and extra files

- `notebooks/Model1_Training.ipynb` trains the model and also contains
  experiments: algorithm comparison, input ablation, per-category results,
  learning curve, cross-district test, and BRIGHT district-mix adjustment test.
- `notebooks/District_Livelihood_Shares_generating.ipynb` builds
  `artifacts/district_livelihood_shares.csv` from the BRIGHT survey.
- The BRIGHT district-mix adjustment was tested and did not help consistently,
  so `district_livelihood_shares.csv` is not used by the API. It is kept as
  evidence of the experiment.
- To retrain, use scikit-learn 1.6.1 (the same version as
  `backend/requirements.txt`), then copy `model_v1.joblib` and
  `model_v1_info.json` into `artifacts/`.
