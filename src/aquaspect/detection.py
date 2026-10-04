"""
aquaspect.detection
===================
Water-body and anomaly detection for AQUASPECT.

Functions
---------
apply_water_mask          Apply water mask + minimum component filter.
spatial_stats             Compute per-indicator statistics within water pixels.
build_baseline            Compute pixel-wise mean/std from a temporal stack.
detect_anomalies          Produce spatial anomaly map from baseline + new obs.
summarise_detections      Aggregate anomaly pixels into a detection report.
"""

from __future__ import annotations

import logging

import numpy as np
import numpy.typing as npt
from scipy import ndimage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Water-body refinement
# ---------------------------------------------------------------------------

def apply_water_mask(
    water_mask: npt.NDArray[np.bool_],
    min_pixels: int = 100,
    pixel_area_m2: float | None = None,
) -> tuple[npt.NDArray[np.bool_], dict]:
    """
    Remove small connected components from a water mask.

    Parameters
    ----------
    water_mask : 2-D bool array
    min_pixels : int
        Minimum connected component size (pixels) to retain.
    pixel_area_m2 : float, optional
        Pixel area in square metres (for area estimation).
        Provide only when the raster is in a projected CRS.
        Do NOT use degree-based approximations.

    Returns
    -------
    refined_mask : bool array
    stats : dict
        total_water_pixels, retained_water_pixels, removed_pixels,
        estimated_area_km2 (if pixel_area_m2 supplied).
    """
    labelled, n_components = ndimage.label(water_mask)
    sizes = ndimage.sum(water_mask, labelled, range(1, n_components + 1))

    refined = np.zeros_like(water_mask)
    kept = 0
    for comp_id, size in enumerate(sizes, start=1):
        if size >= min_pixels:
            refined |= labelled == comp_id
            kept += 1

    stats: dict = {
        "total_components":    n_components,
        "retained_components": kept,
        "total_water_pixels":  int(water_mask.sum()),
        "retained_water_pixels": int(refined.sum()),
        "removed_pixels":      int(water_mask.sum()) - int(refined.sum()),
    }

    if pixel_area_m2 is not None:
        area_km2 = int(refined.sum()) * pixel_area_m2 / 1e6
        stats["estimated_area_km2"] = round(area_km2, 3)
        logger.info("Estimated water area: %.3f km²", area_km2)

    logger.info("Water mask refined: %s", stats)
    return refined, stats


# ---------------------------------------------------------------------------
# Spatial statistics
# ---------------------------------------------------------------------------

def spatial_stats(
    index_arr: npt.NDArray[np.float32],
    mask: npt.NDArray[np.bool_],
    name: str = "index",
) -> dict:
    """
    Compute spatial summary statistics for *index_arr* within *mask*.

    Parameters
    ----------
    index_arr : 2-D float array
    mask : 2-D bool array — True = pixels to include
    name : str — label for the returned dict keys

    Returns
    -------
    stats : dict with keys:
        {name}_count, {name}_mean, {name}_median,
        {name}_std, {name}_p5, {name}_p25, {name}_p75, {name}_p95,
        {name}_min, {name}_max
    """
    values = index_arr[mask & np.isfinite(index_arr)]
    if values.size == 0:
        logger.warning("No valid pixels for '%s' stats.", name)
        return {f"{name}_{k}": np.nan for k in
                ["count", "mean", "median", "std", "p5", "p25", "p75", "p95", "min", "max"]}

    p5, p25, p50, p75, p95 = np.percentile(values, [5, 25, 50, 75, 95])
    return {
        f"{name}_count":  int(values.size),
        f"{name}_mean":   float(np.mean(values)),
        f"{name}_median": float(p50),
        f"{name}_std":    float(np.std(values)),
        f"{name}_p5":     float(p5),
        f"{name}_p25":    float(p25),
        f"{name}_p75":    float(p75),
        f"{name}_p95":    float(p95),
        f"{name}_min":    float(np.min(values)),
        f"{name}_max":    float(np.max(values)),
    }


# ---------------------------------------------------------------------------
# Temporal baseline
# ---------------------------------------------------------------------------

def build_baseline(
    stack: list[npt.NDArray[np.float32]],
    robust: bool = False,
) -> tuple[npt.NDArray[np.float32], npt.NDArray[np.float32]]:
    """
    Compute pixel-wise baseline (central tendency + spread) from a stack.

    Parameters
    ----------
    stack : list of 2-D float32 arrays (same shape, NaN = invalid)
    robust : bool
        If True, use median / MAD instead of mean / std.
        Recommended when the stack is small (< ~5 dates) or may contain
        residual cloud contamination.

    Returns
    -------
    baseline_mean : float32 array — pixel-wise mean or median
    baseline_std  : float32 array — pixel-wise std or MAD
    """
    if not stack:
        raise ValueError("Stack must contain at least one array.")

    cube = np.stack(stack, axis=0)  # (n_dates, rows, cols)

    if robust:
        baseline_mean = np.nanmedian(cube, axis=0).astype(np.float32)
        # Median absolute deviation (MAD) — more outlier-resistant than std
        baseline_std  = np.nanmedian(
            np.abs(cube - baseline_mean[np.newaxis, ...]), axis=0
        ).astype(np.float32)
    else:
        baseline_mean = np.nanmean(cube, axis=0).astype(np.float32)
        baseline_std  = np.nanstd(cube, axis=0).astype(np.float32)

    n_valid = np.sum(~np.isnan(cube), axis=0)
    if np.any(n_valid < 3):
        logger.warning(
            "Some pixels have fewer than 3 valid baseline observations. "
            "Baseline variability estimates may be unreliable."
        )

    return baseline_mean, baseline_std


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------

def detect_anomalies(
    observation: npt.NDArray[np.float32],
    baseline_mean: npt.NDArray[np.float32],
    baseline_std: npt.NDArray[np.float32],
    water_mask: npt.NDArray[np.bool_],
    z_threshold_high: float = 2.0,
    z_threshold_extreme: float = 3.0,
    min_std: float = 1e-4,
) -> tuple[npt.NDArray[np.float32], npt.NDArray[np.uint8], dict]:
    """
    Produce a standardised anomaly map and detection classes.

    Parameters
    ----------
    observation        : 2-D float32 — new observation to test
    baseline_mean      : 2-D float32 — pixel-wise baseline mean
    baseline_std       : 2-D float32 — pixel-wise baseline std/MAD
    water_mask         : 2-D bool   — restrict analysis to water pixels
    z_threshold_high   : float — z ≥ this → HIGH anomaly class
    z_threshold_extreme: float — z ≥ this → EXTREME anomaly class
    min_std            : float — minimum std to avoid /0

    Returns
    -------
    z_map        : float32 array — standardised anomaly (z-score)
    anomaly_class: uint8 array  — 0=normal, 1=elevated, 2=high, 3=extreme
    summary      : dict — pixel counts per class and area (if available)
    """
    from .indices import z_score

    z_map = np.full_like(observation, np.nan, dtype=np.float32)
    z_map[water_mask] = z_score(
        observation[water_mask],
        baseline_mean[water_mask],
        baseline_std[water_mask],
        min_std=min_std,
    )

    aclass = np.zeros(observation.shape, dtype=np.uint8)
    aclass[water_mask & (z_map >= 1.0)]                 = 1  # elevated
    aclass[water_mask & (z_map >= z_threshold_high)]    = 2  # high
    aclass[water_mask & (z_map >= z_threshold_extreme)] = 3  # extreme

    summary = {
        "anomaly_normal_px":   int(np.sum(water_mask & (aclass == 0))),
        "anomaly_elevated_px": int(np.sum(water_mask & (aclass == 1))),
        "anomaly_high_px":     int(np.sum(water_mask & (aclass == 2))),
        "anomaly_extreme_px":  int(np.sum(water_mask & (aclass == 3))),
        "z_threshold_elevated": 1.0,
        "z_threshold_high":    z_threshold_high,
        "z_threshold_extreme": z_threshold_extreme,
    }
    return z_map, aclass, summary
