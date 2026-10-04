"""
aquaspect.preprocessing
========================
Quality-control and preprocessing functions for Tanager hyperspectral data.

Steps implemented here:
    1. Build a valid-pixel mask from Tanager QA layers.
    2. Report QA statistics (total / valid / invalid pixel counts).
    3. Extract surface-reflectance array with invalid pixels set to NaN.
    4. Nearest-band lookup (match target wavelength to actual band centre).
    5. Extract a single-band 2-D array by wavelength.
    6. Spatial reprojection / AOI clipping utilities.

All functions are stateless and accept explicit arguments so they are
easily testable and usable from the notebook.
"""

from __future__ import annotations

import logging
from typing import Sequence

import h5py
import numpy as np
import numpy.typing as npt

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# QA / valid-pixel mask
# ---------------------------------------------------------------------------

def build_qa_mask(
    hdf_path: str,
    nodata_field: str = "nodata_pixels",
    cloud_field: str  = "beta_cloud_mask",
    cirrus_field: str = "beta_cirrus_mask",
) -> tuple[npt.NDArray[np.bool_], dict]:
    """
    Build a boolean valid-pixel mask from Tanager QA layers.

    Parameters
    ----------
    hdf_path : str
        Path to the Tanager HDF5 file.
    nodata_field, cloud_field, cirrus_field : str
        Dataset names inside the HDF5 file for each QA flag.
        Pass None to skip a particular layer.

    Returns
    -------
    valid_mask : np.ndarray of bool, shape (rows, cols)
        True where a pixel is usable.
    stats : dict
        Summary statistics: total_pixels, valid_pixels, invalid_pixels,
        nodata_pct, cloud_pct, cirrus_pct, valid_pct.
    """
    with h5py.File(hdf_path, "r") as f:
        def _load(field):
            if field is None:
                return None
            # Tanager QA layers may be stored at the root or under a group.
            for candidate in [field, f"HDFEOS/GRIDS/HYP/Data Fields/{field}"]:
                if candidate in f:
                    arr = f[candidate][:]
                    return arr.astype(bool)
            logger.warning("QA field %r not found in HDF5; ignoring.", field)
            return None

        nodata  = _load(nodata_field)
        cloud   = _load(cloud_field)
        cirrus  = _load(cirrus_field)

    # Reference shape from the first available mask
    ref = next(m for m in [nodata, cloud, cirrus] if m is not None)
    shape = ref.shape[:2]  # (rows, cols)

    invalid = np.zeros(shape, dtype=bool)
    if nodata  is not None: invalid |= nodata [..., 0] if nodata.ndim  == 3 else nodata
    if cloud   is not None: invalid |= cloud  [..., 0] if cloud.ndim   == 3 else cloud
    if cirrus  is not None: invalid |= cirrus [..., 0] if cirrus.ndim  == 3 else cirrus

    valid_mask = ~invalid
    total = valid_mask.size

    stats = {
        "total_pixels":   total,
        "valid_pixels":   int(valid_mask.sum()),
        "invalid_pixels": int(invalid.sum()),
        "valid_pct":      round(100.0 * valid_mask.sum() / total, 2),
        "nodata_pct":     round(100.0 * nodata.sum()  / total, 2) if nodata  is not None else None,
        "cloud_pct":      round(100.0 * cloud.sum()   / total, 2) if cloud   is not None else None,
        "cirrus_pct":     round(100.0 * cirrus.sum()  / total, 2) if cirrus  is not None else None,
    }
    logger.info("QA stats: %s", stats)
    return valid_mask, stats


# ---------------------------------------------------------------------------
# Surface reflectance array
# ---------------------------------------------------------------------------

def load_reflectance(
    hdf_path: str,
    reflectance_path: str = "HDFEOS/GRIDS/HYP/Data Fields/surface_reflectance",
    valid_mask: npt.NDArray[np.bool_] | None = None,
    scale_factor: float = 1e-4,
) -> tuple[npt.NDArray[np.float32], npt.NDArray[np.float64]]:
    """
    Load the full surface-reflectance cube from a Tanager HDF5 file.

    Parameters
    ----------
    hdf_path : str
    reflectance_path : str
        HDF5 internal path to the reflectance dataset.
    valid_mask : np.ndarray of bool, optional
        If provided, invalid pixels are set to NaN.
    scale_factor : float
        Divide raw integer values by this to get reflectance in [0, 1].
        Default 1e-4 (DN → reflectance); set to 1.0 if already float.

    Returns
    -------
    reflectance : np.ndarray, float32, shape (rows, cols, bands)
        Surface reflectance with invalid pixels as NaN.
    wavelengths : np.ndarray, float64, shape (bands,)
        Centre wavelength in nm for each band.
        Returned as NaN-filled array if not found in the file.
    """
    with h5py.File(hdf_path, "r") as f:
        raw = f[reflectance_path][:]  # shape: (bands, rows, cols) OR (rows, cols, bands)

        # Detect band axis: Tanager is typically (bands, rows, cols)
        if raw.ndim == 3 and raw.shape[0] < min(raw.shape[1], raw.shape[2]):
            raw = np.moveaxis(raw, 0, -1)  # → (rows, cols, bands)

        # Wavelengths — look for a 'wavelength' or 'Wavelength' dataset
        wavelengths = np.full(raw.shape[-1], np.nan)
        for candidate in ["wavelength", "Wavelength",
                          "HDFEOS/GRIDS/HYP/Data Fields/wavelength"]:
            if candidate in f:
                wavelengths = f[candidate][:].astype(np.float64)
                break

    reflectance = raw.astype(np.float32) * np.float32(scale_factor)

    # Clamp to physically plausible range
    reflectance = np.clip(reflectance, 0.0, 1.0)

    if valid_mask is not None:
        reflectance[~valid_mask] = np.nan

    return reflectance, wavelengths


# ---------------------------------------------------------------------------
# Spectral band utilities
# ---------------------------------------------------------------------------

def nearest_band_index(wavelengths: npt.NDArray, target_nm: float) -> int:
    """Return the index of the band centre closest to *target_nm* nm."""
    return int(np.argmin(np.abs(wavelengths - target_nm)))


def extract_band(
    reflectance: npt.NDArray,
    wavelengths: npt.NDArray,
    target_nm: float,
) -> tuple[npt.NDArray[np.float32], float]:
    """
    Extract a 2-D band slice nearest to *target_nm*.

    Returns
    -------
    band_2d : np.ndarray, shape (rows, cols)
    actual_nm : float
        Actual centre wavelength used.
    """
    idx = nearest_band_index(wavelengths, target_nm)
    actual_nm = float(wavelengths[idx])
    logger.debug("Requested %.1f nm → band %d (%.2f nm)", target_nm, idx, actual_nm)
    return reflectance[..., idx], actual_nm


def mask_water_vapour_windows(
    wavelengths: npt.NDArray,
    windows: Sequence[tuple[float, float]] = ((1350, 1450), (1800, 1950)),
    far_swir_cutoff: float = 2450.0,
) -> npt.NDArray[np.bool_]:
    """
    Return a boolean mask (True = keep) for spectral bands,
    excluding water-vapour absorption windows and the far-SWIR tail.
    """
    keep = np.ones(len(wavelengths), dtype=bool)
    for lo, hi in windows:
        keep &= ~((wavelengths >= lo) & (wavelengths <= hi))
    keep &= wavelengths <= far_swir_cutoff
    return keep
