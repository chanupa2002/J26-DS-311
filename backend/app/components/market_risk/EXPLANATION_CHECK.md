# market_risk: explanation sanity check (SHAP direction)

Checked 2026-10-22 on the deployed version 2.0 models. **Data basis: SYNTHETIC panel (70 households, 9 categories). Not real-world evidence.**

## Purpose

The Future Risk page showed "No profit last month: Yes – pushes away from High" and "No profit at previous visit: No – pushes towards High". This looks inverted. The check answers one question: does the direction come from **(A) a label bug** in the frontend, or **(B) the model itself**?

## Method

1. **Labels:** each of the 53 frontend labels and value wordings was compared with the backend feature descriptions (`schemas.py`, `feature_schema.json`) and the training code (`ml/training/features.py`): what 1, 0 and a higher number mean.
2. **Model:** 4 features were tested with the 3M and 6M models and the existing explainer (`ml/explainer.py`), read-only:
   - **Inputs:** 7 inline synthetic inputs. The base rows were the sample request, the sample with another category, district or current risk class, an all-zero row, and an all-zero row with visit history.
   - **Change:** each feature was set low, then high, with all other values unchanged.
   - **Recorded:** the feature's mean SHAP value towards High at the low and high value, and the mean change in the model's P(High).
3. **Context:** the share of training rows whose label 3 or 6 months later is High, by feature value. These are aggregates only; no rows were printed.

## Results

**Labels:** correct for all 53 features. In the backend descriptions and the training code, 1 means the label's statement is true, and the frontend shows 1 as "Yes". The two features from the sample:
- `F_No_Profit_Last_Month_t`: training code `T = 1 − profit`, so 1 = no profit.
- `F_Prev_No_Profit_Last_Month`: the previous visit's no-profit signal.

One wording was misleading and was fixed in the frontend: "Average risk, last 3 months" now shows its scale, e.g. "0 (Low)".

**Model** (7 inline inputs, feature low → high, all else unchanged):

| Feature (low → high) | Model | Mean SHAP → High at low | at high | Mean change in P(High) | Inputs where P(High) rose |
|---|---|---|---|---|---|
| No profit last month (0 → 1) | 3M | −0.0042 | +0.0059 | +0.0093 | 7 of 7 |
| No profit last month (0 → 1) | 6M | +0.0158 | −0.0172 | **−0.0334** | 0 of 7 |
| No profit at previous visit (0 → 1) | 3M | +0.0031 | −0.0014 | **−0.0049** | 0 of 7 |
| No profit at previous visit (0 → 1) | 6M | +0.0094 | −0.0028 | **−0.0133** | 0 of 7 |
| Average risk, last 3 months (0 → 2) | 3M | −0.0046 | +0.0023 | +0.0061 | 7 of 7 |
| Average risk, last 3 months (0 → 2) | 6M | +0.0113 | −0.0050 | **−0.0161** | 0 of 7 |
| No-profit share, last 3 months (0 → 1) | 3M | −0.0107 | +0.0093 | +0.0223 | 7 of 7 |
| No-profit share, last 3 months (0 → 1) | 6M | +0.0390 | −0.0407 | **−0.0813** | 0 of 7 |

**Training labels** (550-row synthetic panel; share of rows whose label 3 or 6 months later is High; n = rows):

| Feature | Horizon | Value 0 / low | Value 1 / high |
|---|---|---|---|
| No profit last month | 3M | 0.30 (n=155) | 0.42 (n=104) |
| No profit last month | 6M | 0.68 (n=74) | 0.31 (n=59) |
| No profit at previous visit | 3M | 0.43 (n=124) | 0.33 (n=87) |
| No profit at previous visit | 6M | 0.78 (n=51) | 0.28 (n=36) |
| Average risk, last 3 months (≤0.5 / >1.5) | 3M | 0.34 (n=116) | 0.42 (n=26) |
| Average risk, last 3 months (≤0.5 / >1.5) | 6M | 0.63 (n=54) | 0.38 (n=16) |
| No-profit share, last 3 months (≤0.34 / >0.67) | 3M | 0.34 (n=148) | 0.32 (n=78) |
| No-profit share, last 3 months (≤0.34 / >0.67) | 6M | 0.70 (n=74) | 0.20 (n=55) |

Blank values and middle bins are left out of this table.

## Conclusion

**(B) the model, not a label bug.**
- **Labels:** correct.
- **6M model:** reverses all four no-profit and risk-history features, on every input tried: "no profit" lowers P(High) 6 months ahead. It reproduces the synthetic training labels, where households with no profit were *less* often High 6 months later (31% vs 68%). It also has only **91 training rows**.
- **3M model:** mostly as expected. "No profit last month", "Average risk, last 3 months" and "No-profit share, last 3 months" raise P(High). Only "No profit at previous visit" is reversed, matching its training labels (33% vs 43%).
- **Frontend:** no extra logic was added. The Why card shows the model's direction with the note that these are the model's reasons, not proven real-world causes.

## Action

Before any use, **re-check these directions with real data** (a stable household ID, at least 12 months) **and expert review**. A model whose explanations say "no profit lowers future risk" should not be used for decisions. Repeat this check after every retraining.
