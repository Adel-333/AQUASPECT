"""
aquaspect.visualization
========================
Reproducible map and chart functions for AQUASPECT.

All functions save output to disk AND return the figure object so they
can be called in the notebook with inline display.

Design rules:
  - All colour maps are chosen for accessibility (colorblind-safe where possible).
  - Every map includes a title, colourbar, and scale/CRS annotation.
  - NaN / masked pixels are shown in a neutral colour (light grey).
  - No hard-coded absolute paths.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import numpy.typing as npt

# Ensure consistent style
plt.rcParams.update({
    "figure.dpi": 150,
    "axes.titlesize": 11,
    "axes.labelsize": 9,
    "font.family": "DejaVu Sans",
})

_NAN_COLOUR = "#d0d0d0"


# ---------------------------------------------------------------------------
# Generic 2-D map
# ---------------------------------------------------------------------------

def plot_index_map(
    arr: npt.NDArray,
    mask: npt.NDArray[np.bool_] | None = None,
    title: str = "Spectral index",
    cmap: str = "RdYlBu",
    vmin: float | None = None,
    vmax: float | None = None,
    cbar_label: str = "",
    save_path: str | Path | None = None,
    figsize: tuple = (8, 6),
) -> plt.Figure:
    """
    Plot a 2-D spectral index map.

    Parameters
    ----------
    arr       : 2-D float array
    mask      : 2-D bool array — if provided, pixels outside mask shown in grey
    title     : figure title
    cmap      : matplotlib colourmap name
    vmin/vmax : colour scale limits (auto if None)
    cbar_label: colourbar label
    save_path : if given, save the figure to this path (PNG)
    figsize   : (width, height) in inches
    """
    display = arr.astype(np.float32).copy()
    if mask is not None:
        display[~mask] = np.nan

    cmap_obj = plt.get_cmap(cmap).copy()
    cmap_obj.set_bad(color=_NAN_COLOUR)

    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(display, cmap=cmap_obj, vmin=vmin, vmax=vmax,
                   interpolation="nearest")
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(cbar_label, fontsize=9)
    ax.set_title(title, fontweight="bold")
    ax.set_xlabel("Column (pixel)")
    ax.set_ylabel("Row (pixel)")
    ax.tick_params(labelsize=8)
    fig.tight_layout()

    if save_path is not None:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


# ---------------------------------------------------------------------------
# Classified / categorical map (water mask, screening map, anomaly class)
# ---------------------------------------------------------------------------

def plot_classified_map(
    arr: npt.NDArray[np.uint8],
    classes: dict,  # {value: (label, colour)}
    title: str = "Classification map",
    save_path: str | Path | None = None,
    figsize: tuple = (8, 6),
) -> plt.Figure:
    """
    Plot a discrete classification map with a legend.

    Parameters
    ----------
    arr     : 2-D uint8 array of class values
    classes : mapping {int_value: (label_str, hex_colour_str)}
              e.g. {0: ("Non-water", "#d0d0d0"), 1: ("Water", "#2166ac")}
    """
    values  = sorted(classes.keys())
    colours = [classes[v][1] for v in values]
    labels  = [classes[v][0] for v in values]

    cmap = mcolors.ListedColormap(colours)
    norm = mcolors.BoundaryNorm(
        boundaries=[v - 0.5 for v in values] + [values[-1] + 0.5],
        ncolors=len(values),
    )

    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(arr, cmap=cmap, norm=norm, interpolation="nearest")
    cbar = fig.colorbar(im, ax=ax, ticks=values, fraction=0.046, pad=0.04)
    cbar.set_ticklabels(labels)
    cbar.ax.tick_params(labelsize=8)
    ax.set_title(title, fontweight="bold")
    ax.set_xlabel("Column (pixel)")
    ax.set_ylabel("Row (pixel)")
    ax.tick_params(labelsize=8)
    fig.tight_layout()

    if save_path is not None:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


# ---------------------------------------------------------------------------
# Time series
# ---------------------------------------------------------------------------

def plot_time_series(
    dates: list[str],
    values: list[float],
    baseline_mean: float | None = None,
    baseline_std: float | None = None,
    ylabel: str = "Index value",
    title: str = "Water-quality indicator time series",
    highlight_dates: list[str] | None = None,
    save_path: str | Path | None = None,
    figsize: tuple = (10, 4),
) -> plt.Figure:
    """
    Plot a temporal index series with optional baseline band.

    Parameters
    ----------
    dates            : list of ISO date strings
    values           : corresponding mean index values
    baseline_mean    : scalar baseline reference (horizontal line)
    baseline_std     : scalar — drawn as ±1 std shaded band
    highlight_dates  : date strings to mark with a vertical dashed line
    """
    fig, ax = plt.subplots(figsize=figsize)

    ax.plot(dates, values, "o-", color="#2166ac", linewidth=1.8,
            markersize=6, label="Observed mean")

    if baseline_mean is not None:
        ax.axhline(baseline_mean, color="#b2182b", linestyle="--",
                   linewidth=1.2, label=f"Baseline mean ({baseline_mean:.3f})")
        if baseline_std is not None:
            ax.axhspan(baseline_mean - baseline_std,
                       baseline_mean + baseline_std,
                       alpha=0.15, color="#b2182b", label="±1 std")

    if highlight_dates:
        for hd in highlight_dates:
            if hd in dates:
                ax.axvline(hd, color="#f4a582", linestyle=":", linewidth=1.5)

    ax.set_xlabel("Acquisition date")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontweight="bold")
    ax.legend(fontsize=8)
    ax.tick_params(axis="x", rotation=30, labelsize=8)
    ax.tick_params(axis="y", labelsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if save_path is not None:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


# ---------------------------------------------------------------------------
# RGB composite
# ---------------------------------------------------------------------------

def plot_rgb(
    red: npt.NDArray,
    green: npt.NDArray,
    blue: npt.NDArray,
    title: str = "RGB composite",
    percentile_stretch: tuple = (2, 98),
    save_path: str | Path | None = None,
    figsize: tuple = (8, 6),
) -> plt.Figure:
    """
    Plot a linear-percentile-stretched RGB composite.

    Parameters
    ----------
    red, green, blue      : 2-D float arrays (reflectance, [0, 1])
    percentile_stretch    : (low_pct, high_pct) for normalisation
    """
    def _stretch(band):
        lo, hi = np.nanpercentile(band, percentile_stretch)
        return np.clip((band - lo) / (hi - lo + 1e-6), 0, 1)

    rgb = np.dstack([_stretch(red), _stretch(green), _stretch(blue)])
    # Replace NaN with grey
    nan_pix = ~np.isfinite(rgb).all(axis=-1)
    rgb[nan_pix] = 0.8

    fig, ax = plt.subplots(figsize=figsize)
    ax.imshow(rgb, interpolation="bilinear")
    ax.set_title(title, fontweight="bold")
    ax.set_xlabel("Column (pixel)")
    ax.set_ylabel("Row (pixel)")
    ax.tick_params(labelsize=8)
    fig.tight_layout()

    if save_path is not None:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


# ---------------------------------------------------------------------------
# Spectral signature
# ---------------------------------------------------------------------------

def plot_spectral_signature(
    wavelengths: npt.NDArray,
    mean_reflectance: npt.NDArray,
    std_reflectance: npt.NDArray | None = None,
    label: str = "Water pixels",
    keep_mask: npt.NDArray[np.bool_] | None = None,
    title: str = "Mean spectral signature",
    save_path: str | Path | None = None,
    figsize: tuple = (10, 4),
) -> plt.Figure:
    """
    Plot a mean ± std spectral signature.

    Parameters
    ----------
    wavelengths      : 1-D array of band centres in nm
    mean_reflectance : 1-D array of mean reflectance per band
    std_reflectance  : 1-D array of std per band (optional)
    keep_mask        : 1-D bool array — True = plot this band
                       (use to hide water-vapour windows)
    """
    wl = wavelengths.copy()
    mr = mean_reflectance.copy()
    sr = std_reflectance.copy() if std_reflectance is not None else None

    if keep_mask is not None:
        wl = wl[keep_mask]
        mr = mr[keep_mask]
        if sr is not None:
            sr = sr[keep_mask]

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(wl, mr, linewidth=1.5, color="#2166ac", label=label)
    if sr is not None:
        ax.fill_between(wl, mr - sr, mr + sr, alpha=0.2, color="#2166ac")

    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Surface reflectance")
    ax.set_title(title, fontweight="bold")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.tick_params(labelsize=8)
    fig.tight_layout()

    if save_path is not None:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig
