"""
aquaspect.indices
=================
Spectral water-quality indices for AQUASPECT.

All functions operate on 2-D band arrays (rows × cols) and return
float32 arrays of the same shape.  NaN is propagated from inputs.

IMPORTANT — interpretation notes
---------------------------------
These are SPECTRAL PROXIES / SCREENING INDICATORS unless independently
calibrated against in-situ measurements.  Do not label outputs as
physical units (e.g. NTU, mg/L) without a documented calibration.

Index sources
-------------
NDWI  : McFeeters (1996), Remote Sensing of Environment
NDVI  : Tucker (1979), Remote Sensing of Environment
NDCI  : Mishra & Mishra (2012), Remote Sensing of Environment
        (NDCI as chlorophyll-a screening indicator for inland water)
FAI   : Hu (2009), Journal of Applied Remote Sensing
        (Floating Algae Index — requires 3 bands)
Turb  : Simple red/green ratio proxy; not calibrated to NTU
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

_eps = np.float32(1e-6)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _norm_diff(a: npt.NDArray, b: npt.NDArray) -> npt.NDArray[np.float32]:
    """Normalised difference (a - b) / (a + b + eps), both float32."""
    a = a.astype(np.float32)
    b = b.astype(np.float32)
    return (a - b) / (a + b + _eps)


# ---------------------------------------------------------------------------
# Water indices
# ---------------------------------------------------------------------------

def ndwi(green: npt.NDArray, nir: npt.NDArray) -> npt.NDArray[np.float32]:
    """
    Normalised Difference Water Index.

    NDWI = (Green − NIR) / (Green + NIR)

    Positive values broadly indicate open water.
    Threshold selection must be documented and validated per scene.
    Source: McFeeters (1996).
    """
    return _norm_diff(green, nir)


def water_mask(
    ndwi_arr: npt.NDArray[np.float32],
    threshold: float = 0.0,
) -> npt.NDArray[np.bool_]:
    """
    Binary water mask from NDWI.

    Parameters
    ----------
    ndwi_arr : 2-D float array
    threshold : float
        Pixels with NDWI > threshold are labelled water.
        Default 0.0 (McFeeters 1996); validate for each scene.

    Returns
    -------
    mask : bool array, True = water pixel
    """
    return ndwi_arr > threshold


# ---------------------------------------------------------------------------
# Vegetation
# ---------------------------------------------------------------------------

def ndvi(nir: npt.NDArray, red: npt.NDArray) -> npt.NDArray[np.float32]:
    """
    Normalised Difference Vegetation Index.

    NDVI = (NIR − Red) / (NIR + Red)

    Included as a consistency check: strongly positive NDVI pixels
    in a water-masked scene indicate aquatic vegetation or emergent
    macrophytes, not open water.
    Source: Tucker (1979).
    """
    return _norm_diff(nir, red)


# ---------------------------------------------------------------------------
# Chlorophyll / algal-bloom screening
# ---------------------------------------------------------------------------

def ndci(
    red_edge: npt.NDArray,
    red: npt.NDArray,
) -> npt.NDArray[np.float32]:
    """
    Normalised Difference Chlorophyll Index.

    NDCI = (Red-edge − Red) / (Red-edge + Red)

    Bands:
        Red-edge ≈ 708 nm  (chlorophyll fluorescence shoulder)
        Red      ≈ 665 nm  (chlorophyll absorption trough)

    INTERPRETATION:
    - Positive NDCI → elevated red-edge reflectance relative to red →
      potential chlorophyll-a signal.
    - Screening thresholds (e.g. > 0.05 elevated, > 0.2 high) are
      EMPIRICAL SCREEN VALUES, not calibrated bloom detectors.
    - Only meaningful inside a validated water mask.
    Source: Mishra & Mishra (2012).
    """
    return _norm_diff(red_edge, red)


def chlorophyll_screen(
    ndci_arr: npt.NDArray[np.float32],
    water_msk: npt.NDArray[np.bool_],
    threshold_elevated: float = 0.05,
    threshold_high: float = 0.20,
) -> npt.NDArray[np.uint8]:
    """
    Three-class chlorophyll screening map (water pixels only).

    Returns
    -------
    screen : uint8 array
        0 = non-water or low chlorophyll indicator
        1 = elevated chlorophyll indicator  (NDCI > threshold_elevated)
        2 = high chlorophyll indicator      (NDCI > threshold_high)

    Both thresholds are EMPIRICAL SCREENS — not validated bloom detectors.
    """
    screen = np.zeros(ndci_arr.shape, dtype=np.uint8)
    screen[water_msk & (ndci_arr > threshold_elevated)] = 1
    screen[water_msk & (ndci_arr > threshold_high)]     = 2
    return screen


# ---------------------------------------------------------------------------
# Turbidity / suspended-material proxy
# ---------------------------------------------------------------------------

def turbidity_proxy(
    red: npt.NDArray,
    green: npt.NDArray,
) -> npt.NDArray[np.float32]:
    """
    Simple turbidity / suspended-sediment proxy.

    Proxy = (Red − Green) / (Red + Green)

    Higher values → elevated red reflectance relative to green →
    potential suspended particulates.

    INTERPRETATION:
    - This is a dimensionless spectral ratio, NOT turbidity in NTU.
    - Calibration to NTU requires in-situ measurements.
    - Only meaningful inside a validated water mask.
    """
    return _norm_diff(red, green)


# ---------------------------------------------------------------------------
# Spatial anomaly (z-score) for temporal analysis
# ---------------------------------------------------------------------------

def z_score(
    observation: npt.NDArray[np.float32],
    baseline_mean: npt.NDArray[np.float32],
    baseline_std: npt.NDArray[np.float32],
    min_std: float = 1e-4,
) -> npt.NDArray[np.float32]:
    """
    Standardised anomaly: z = (obs − mean) / max(std, min_std).

    Parameters
    ----------
    observation : 2-D float array
        New observation to compare with the baseline.
    baseline_mean, baseline_std : 2-D float arrays
        Pixel-wise baseline statistics from the temporal stack.
    min_std : float
        Floor applied to baseline_std to avoid division by near-zero.
        Prevents spurious high-z scores in low-variability pixels.

    Returns
    -------
    z : float32 array, same shape as observation
    """
    obs  = observation.astype(np.float32)
    mu   = baseline_mean.astype(np.float32)
    sig  = np.maximum(baseline_std.astype(np.float32), np.float32(min_std))
    return (obs - mu) / sig
