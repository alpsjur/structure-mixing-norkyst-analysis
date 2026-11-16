"""Daily wind-farm mean PEA time series: experiment and wakeref (left), experiment - wakeref (right).

Run from the repo root. One figure per run and PEA range (6 farm rows sharing the time axis)
-> figures/<range>_timeseries/pea_<run>_timeseries.png (pea = whole column, pea50, pea100, pea150).
Daily mean = mean of the daily PEA over the mask cells of each farm (NaN cells skipped).
Usage: python scripts/plotting/pea_farm_timeseries.py [pea pea50 pea100 pea150 ...]  (default: all)
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

RUNS = ["spar", "semisub"]
LABELS = {"pea": "whole column", "pea50": "0-50 m", "pea100": "0-100 m", "pea150": "0-150 m"}
masks = xr.open_dataset(MASKS)
FARMS = [v for v in masks.data_vars if not v.endswith("_sectors")]


def farm_slices(mask):
    eta, xi = np.nonzero(mask)
    return slice(eta.min(), eta.max() + 1), slice(xi.min(), xi.max() + 1)


FARM_SEL = {}
for farm in FARMS:
    m = masks[farm].values > 0
    FARM_SEL[farm] = farm_slices(m) + (m,)


def farm_means(pea_dir, run, month):
    """farm -> DataArray of daily mean PEA over the farm cells."""
    ds = xr.open_dataset(pea_dir / f"pea_{run}_{month}.nc")
    out = {}
    for farm, (es, xs, m) in FARM_SEL.items():
        w = xr.DataArray(m[es, xs], dims=("eta_rho", "xi_rho"))
        sub = ds.pea.isel(eta_rho=es, xi_rho=xs)
        out[farm] = sub.where(w).mean(("eta_rho", "xi_rho")).load()
    return out


def series(pea_dir, run, months):
    parts = [farm_means(pea_dir, run, month) for month in months]
    return {farm: xr.concat([p[farm] for p in parts], "ocean_time") for farm in FARMS}


for rng in sys.argv[1:] or list(LABELS):
    pea_dir = Path(OUTDIR) / rng
    months = sorted(f.stem.split("_")[-1] for f in pea_dir.glob("pea_wakeref_????-??.nc"))
    wake = series(pea_dir, "wakeref", months)
    for run in RUNS:
        exp = series(pea_dir, run, months)
        fig, axes = plt.subplots(len(FARMS), 2, figsize=(16, 2.4 * len(FARMS)), sharex=True, layout="constrained")
        for row, farm in zip(axes, FARMS):
            e, w = xr.align(exp[farm], wake[farm], join="inner")
            row[0].plot(w.ocean_time, w, color="tab:gray", label="wakeref")
            row[0].plot(e.ocean_time, e, color="tab:blue", label=run)
            row[1].plot(e.ocean_time, e - w, color="tab:red")
            row[1].axhline(0, color="black", linewidth=0.5)
            row[0].set_ylabel(farm.replace("_", " ") + "\n(J m$^{-3}$)")
            for ax in row:
                ax.grid(alpha=0.3)
        axes[0, 0].legend(loc="upper right", ncol=2)
        axes[0, 0].set_title(f"Daily mean PEA ({rng}: {LABELS[rng]})")
        axes[0, 1].set_title(f"{run} - wakeref")
        axes[-1, 0].xaxis.set_major_formatter(mdates.ConciseDateFormatter(mdates.AutoDateLocator()))
        save_fig(fig, f"pea_{run}_timeseries", f"{rng}_timeseries")
        plt.close(fig)
        print(rng, run, "done", flush=True)
