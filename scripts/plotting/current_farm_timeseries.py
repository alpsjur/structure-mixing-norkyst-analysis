"""Daily wind-farm mean current speed time series: experiment and wakeref (left), experiment - wakeref (right).

Run from the repo root. One figure per run (6 farm rows sharing the time axis) -> figures/current_timeseries/.
Daily mean = mean of the daily depth-range mean speed over the mask cells of each farm (NaN cells skipped).
Depth range matches the structure: semisub 0-25 m, spar 0-130 m (stored 0_25 and 25_130 combined, weighted by H).
Usage: python scripts/plotting/current_farm_timeseries.py [semisub|spar ...]  (default: both)
"""
import os
import sys

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
sys.path.insert(0, ".github/skills/figure-style")
sys.path.insert(0, ".")

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from analysis.io import MASKS, OUTDIR
from map_example import save_fig

CURRENT_DIR = Path(OUTDIR) / "current"
SETS = {"semisub": (["0_25"], "0-25 m"), "spar": (["0_25", "25_130"], "0-130 m")}
masks = xr.open_dataset(MASKS)
FARMS = [v for v in masks.data_vars if not v.endswith("_sectors")]


def farm_slices(mask):
    eta, xi = np.nonzero(mask)
    return slice(eta.min(), eta.max() + 1), slice(xi.min(), xi.max() + 1)


FARM_SEL = {}
for farm in FARMS:
    m = masks[farm].values > 0
    FARM_SEL[farm] = farm_slices(m) + (m,)


def farm_means(run, month, ranges):
    """DataFrame-like dict: farm -> DataArray of daily mean speed over the farm cells."""
    ds = xr.open_dataset(CURRENT_DIR / f"current_{run}_{month}.nc")
    out = {}
    for farm, (es, xs, m) in FARM_SEL.items():
        sub = ds.isel(eta_rho=es, xi_rho=xs)
        w = xr.DataArray(m[es, xs], dims=("eta_rho", "xi_rho"))
        if len(ranges) == 1:
            speed = sub[f"speed_{ranges[0]}"]
        else:
            H = sum(sub[f"H_{r}"] for r in ranges)
            speed = sum(sub[f"speed_{r}"].fillna(0) * sub[f"H_{r}"] for r in ranges) / H.where(H > 0)
        out[farm] = speed.where(w).mean(("eta_rho", "xi_rho")).load()
    return out


def series(run, ranges, months):
    parts = [farm_means(run, month, ranges) for month in months]
    return {farm: xr.concat([p[farm] for p in parts], "ocean_time") for farm in FARMS}


months = sorted(f.stem.split("_")[-1] for f in CURRENT_DIR.glob("current_wakeref_????-??.nc"))
for run in sys.argv[1:] or list(SETS):
    ranges, label = SETS[run]
    exp, wake = series(run, ranges, months), series("wakeref", ranges, months)
    fig, axes = plt.subplots(len(FARMS), 2, figsize=(16, 2.4 * len(FARMS)), sharex=True, layout="constrained")
    for row, farm in zip(axes, FARMS):
        e, w = xr.align(exp[farm], wake[farm], join="inner")
        row[0].plot(w.ocean_time, w, color="tab:gray", label="wakeref")
        row[0].plot(e.ocean_time, e, color="tab:blue", label=run)
        row[1].plot(e.ocean_time, e - w, color="tab:red")
        row[1].axhline(0, color="black", linewidth=0.5)
        row[0].set_ylabel(farm.replace("_", " ") + "\n(m s$^{-1}$)")
        for ax in row:
            ax.grid(alpha=0.3)
    axes[0, 0].legend(loc="upper right", ncol=2)
    axes[0, 0].set_title(f"Daily mean current speed ({label})")
    axes[0, 1].set_title(f"{run} - wakeref")
    axes[-1, 0].xaxis.set_major_formatter(mdates.ConciseDateFormatter(mdates.AutoDateLocator()))
    save_fig(fig, f"current_{run}_timeseries", "current_timeseries")
    plt.close(fig)
    print(run, "done", flush=True)
