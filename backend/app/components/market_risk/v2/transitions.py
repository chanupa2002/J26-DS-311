"""Monthly risk transitions: how often households move between Low, Medium and High.

A simple summary of past visits (a first-order Markov chain), not a machine-learning model.
It is estimated when the artifacts load, from the stored simulated visits only:
same household, consecutive visits exactly one month apart, both risk classes known.
Every cell gets +1 (Laplace smoothing) so no move has a chance of exactly 0.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

CLASSES = ("Low", "Medium", "High")
SMOOTHING = 1
MAX_MONTHS = 6
METHOD = "past monthly transitions"
NOTE = (
    "Summary of past visits: how often households in this class were High the next month. "
    "Not a machine-learning prediction."
)
UNKNOWN_NOTE = "Current risk unknown – complete the visit form."
EVIDENCE_TEXT = (
    "Next-month risk mostly stays the same; a simple summary of past visits is used, "
    "no machine-learning model for 1 month (no 1-month model was trained; for 3 months, "
    "the model is compared with assuming risk stays the same – see the table below)."
)


@dataclass(frozen=True)
class Transitions:
    counts: np.ndarray  # raw pair counts, rows = this month, columns = next month
    matrix: np.ndarray  # smoothed, each row sums to 1
    n_transitions: int

    def after(self, months: int) -> np.ndarray:
        return np.linalg.matrix_power(self.matrix, months)

    def next_month(self, current_class: str) -> dict:
        """The "1M" entry of the predictions block for a visit in `current_class`."""
        base = {"method": METHOD, "n_transitions": self.n_transitions, "alert": None}
        if current_class not in CLASSES:
            return {**base, "p_low": None, "p_medium": None, "p_high": None,
                    "predicted_class": None, "note": UNKNOWN_NOTE}
        row = self.matrix[CLASSES.index(current_class)]
        chances = {f"p_{name.lower()}": float(value) for name, value in zip(CLASSES, row)}
        return {**base, **chances, "predicted_class": CLASSES[int(row.argmax())], "note": NOTE}

    def row_summary(self, current_class: str) -> dict:
        """Short form for list rows and timeline points."""
        entry = self.next_month(current_class)
        return {"next_month_class": entry["predicted_class"], "next_month_p_high": entry["p_high"]}

    def evidence(self) -> dict:
        high = CLASSES.index("High")
        powers = {k: self.after(k) for k in range(1, MAX_MONTHS + 1)}
        return {
            "is_synthetic": True,
            "method": METHOD,
            "classes": list(CLASSES),
            "smoothing": SMOOTHING,
            "n_transitions": self.n_transitions,
            "counts": self.counts.astype(int).tolist(),
            "matrix": self.matrix.tolist(),
            "p_high_after": [
                {"months": k, **{name: float(powers[k][i, high]) for i, name in enumerate(CLASSES)}}
                for k in powers
            ],
            "text": EVIDENCE_TEXT,
        }


def pairs(features: pd.DataFrame) -> pd.DataFrame:
    """(from, to) classes of consecutive visits exactly one month apart, both classes known."""
    visits = features[["household_key", "month_index", "risk_class_t"]].sort_values(
        ["household_key", "month_index"], kind="stable"
    )
    following = visits.groupby("household_key", sort=False).shift(-1)
    pair = pd.DataFrame({
        "from_class": visits.risk_class_t,
        "to_class": following.risk_class_t,
        "gap": following.month_index - visits.month_index,
    })
    known = pair.from_class.isin(CLASSES) & pair.to_class.isin(CLASSES)
    return pair[known & (pair.gap == 1)][["from_class", "to_class"]]


def estimate(features: pd.DataFrame) -> Transitions:
    counts = np.zeros((len(CLASSES), len(CLASSES)))
    found = pairs(features)
    for (start, end), size in found.value_counts().items():
        counts[CLASSES.index(start), CLASSES.index(end)] = size
    smoothed = counts + SMOOTHING
    return Transitions(
        counts=counts,
        matrix=smoothed / smoothed.sum(axis=1, keepdims=True),
        n_transitions=len(found),
    )
