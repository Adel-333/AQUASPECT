"""
aquaspect.validation
====================
Validation utilities for AQUASPECT.

These functions compute metrics for comparing AQUASPECT outputs against
independent reference data.

IMPORTANT — Honesty policy
----------------------------
Never use these functions with fabricated ground truth.
If no reference data is available, call `validation_not_possible()`
which returns a structured explanation of the limitation.
"""

from __future__ import annotations

import logging

import numpy as np
import numpy.typing as npt
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Binary mask metrics (water mask vs reference)
# ---------------------------------------------------------------------------

def binary_mask_metrics(
    predicted: npt.NDArray[np.bool_],
    reference: npt.NDArray[np.bool_],
    reference_source: str = "UNKNOWN — document this",
) -> dict:
    """
    Compute precision, recall, F1, and IoU for a binary mask.

    Parameters
    ----------
    predicted       : 2-D bool array — AQUASPECT water mask
    reference       : 2-D bool array — independent reference mask
                      (e.g. JRC Global Surface Water, Sentinel-2 NDWI,
                       government boundary polygon)
    reference_source: str — document where the reference came from

    Returns
    -------
    metrics : dict containing:
        precision, recall, f1, iou,
        true_pos, false_pos, false_neg, true_neg,
        reference_source
    """
    p_flat = predicted.ravel().astype(bool)
    r_flat = reference.ravel().astype(bool)

    tp = int(np.sum(p_flat & r_flat))
    fp = int(np.sum(p_flat & ~r_flat))
    fn = int(np.sum(~p_flat & r_flat))
    tn = int(np.sum(~p_flat & ~r_flat))

    precision = tp / (tp + fp + 1e-9)
    recall    = tp / (tp + fn + 1e-9)
    f1        = 2 * precision * recall / (precision + recall + 1e-9)
    iou       = tp / (tp + fp + fn + 1e-9)

    metrics = {
        "reference_source": reference_source,
        "true_pos":   tp,
        "false_pos":  fp,
        "false_neg":  fn,
        "true_neg":   tn,
        "precision":  round(precision, 4),
        "recall":     round(recall, 4),
        "f1":         round(f1, 4),
        "iou":        round(iou, 4),
    }
    logger.info("Binary mask metrics: %s", metrics)
    return metrics


# ---------------------------------------------------------------------------
# Continuous variable comparison
# ---------------------------------------------------------------------------

def continuous_metrics(
    predicted: npt.NDArray[np.float32],
    reference: npt.NDArray[np.float32],
    reference_source: str = "UNKNOWN — document this",
    unit: str = "dimensionless",
) -> dict:
    """
    Compute MAE, RMSE, and correlation for a continuous indicator.

    Parameters
    ----------
    predicted       : 1-D or 2-D float array
    reference       : same shape as predicted
    reference_source: str — document where the reference came from
    unit            : measurement unit (for labelling only)

    Returns
    -------
    metrics : dict with mae, rmse, pearson_r, spearman_r, n_pairs
    """
    from scipy.stats import pearsonr, spearmanr

    pred = predicted.ravel().astype(np.float64)
    ref  = reference.ravel().astype(np.float64)

    # Remove pairs where either value is NaN
    valid = np.isfinite(pred) & np.isfinite(ref)
    pred, ref = pred[valid], ref[valid]

    if pred.size < 3:
        logger.warning("Fewer than 3 valid pairs — metrics unreliable.")
        return {"reference_source": reference_source, "n_pairs": int(pred.size),
                "mae": np.nan, "rmse": np.nan, "pearson_r": np.nan, "spearman_r": np.nan}

    mae   = float(np.mean(np.abs(pred - ref)))
    rmse  = float(np.sqrt(np.mean((pred - ref) ** 2)))
    pearson_r, _  = pearsonr(pred, ref)
    spearman_r, _ = spearmanr(pred, ref)

    metrics = {
        "reference_source": reference_source,
        "unit":       unit,
        "n_pairs":    int(pred.size),
        "mae":        round(mae, 6),
        "rmse":       round(rmse, 6),
        "pearson_r":  round(float(pearson_r), 4),
        "spearman_r": round(float(spearman_r), 4),
    }
    logger.info("Continuous metrics: %s", metrics)
    return metrics


# ---------------------------------------------------------------------------
# Honest limitation statement (when validation data is unavailable)
# ---------------------------------------------------------------------------

def validation_not_possible(reason: str, attempted: list[str]) -> dict:
    """
    Return a structured limitation statement when validation cannot be done.

    Parameters
    ----------
    reason   : str — why full validation was not possible
    attempted: list[str] — what was tried / investigated

    Returns
    -------
    statement : dict — to be saved to validation_summary.csv
    """
    return {
        "validation_status": "INCOMPLETE",
        "reason": reason,
        "attempted": "; ".join(attempted),
        "recommendation": (
            "Future work should acquire in-situ measurements or use "
            "an authoritative satellite water-quality product as reference."
        ),
    }


# ---------------------------------------------------------------------------
# Save validation summary to CSV
# ---------------------------------------------------------------------------

def save_validation_summary(results: list[dict], out_path) -> None:
    """
    Write a list of validation result dicts to a CSV file.

    Parameters
    ----------
    results  : list of metric dicts (from the functions above)
    out_path : path-like
    """
    import csv
    import itertools

    all_keys = list(dict.fromkeys(
        itertools.chain.from_iterable(r.keys() for r in results)
    ))

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    logger.info("Validation summary saved to %s", out_path)
