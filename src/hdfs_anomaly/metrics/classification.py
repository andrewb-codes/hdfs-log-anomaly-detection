import numpy as np
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    precision_score,
    recall_score,
)


def find_threshold_for_max_f1(y_true, scores) -> tuple[float, float]:
    """Return the validation threshold with maximum F1.

    If several thresholds produce the same F1, the highest threshold is used.
    This makes the selected operating point slightly more conservative.
    """
    precision, recall, thresholds = precision_recall_curve(y_true, scores)
    if thresholds.size == 0:
        return float("inf"), 0.0

    precision = precision[:-1]
    recall = recall[:-1]
    f1 = np.divide(
        2 * precision * recall,
        precision + recall,
        out=np.zeros_like(precision),
        where=(precision + recall) > 0,
    )
    best_f1 = f1.max()
    best_threshold = thresholds[f1 == best_f1].max()
    return float(best_threshold), float(best_f1)


def classification_summary(
    name: str,
    y_true,
    y_pred,
    scores=None,
    threshold: float | None = None,
) -> dict:
    """Collect classification metrics for binary anomaly detection."""
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    fpr = 0.0 if fp + tn == 0 else fp / (fp + tn)

    return {
        "model": name,
        "threshold": threshold,
        "f1": f1,
        "precision": precision,
        "recall": recall,
        "fpr": fpr,
        "average_precision": np.nan if scores is None else average_precision_score(y_true, scores),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }
