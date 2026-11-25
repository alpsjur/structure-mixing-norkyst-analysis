"""Daily wind-farm mean TKE and GLS time series: experiment and wakeref (left), experiment - wakeref (right).

Run from the repo root. One figure per run and variable (6 farm rows sharing the time axis)
-> figures/tke_timeseries/, figures/gls_timeseries/.
Depth range matches the structure: semisub 0-25 m, spar 0-130 m (stored 0_25 and 25_130 combined, weighted by H).
Months are those with a wakeref turbulence file; a run is only plotted over the months it has.
Usage: python scripts/plotting/turbulence_farm_timeseries.py [semisub|spar ...]  (default: both)
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

TURB_DIR = Path(OUTDIR) / "turbulence"
SETS = {"semisub": (["0_25"], "0-25 m"), "spar": (["0_25", "25_130"], "0-130 m")}
VARS = {"tke": ("TKE", "m$^2$ s$^{-2}$"), "gls": ("GLS (mean $\\psi$)", "")}
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
    """dict: (var, farm) -> DataArray of daily mean over the farm cells."""
    ds = xr.open_dataset(TURB_DIR / f"turbulence_{run}_{month}.nc")
    out = {}
    for farm, (es, xs, m) in FARM_SEL.items():
        sub = ds.isel(eta_rho=es, xi_rho=xs)
        w = xr.DataArray(m[es, xs], dims=("eta_rho", "xi_rho"))
        for var in VARS:
            if len(ranges) == 1:
                f = sub[f"{var}_{ranges[0]}"]
            else:
                H = sum(sub[f"H_{r}"] for r in ranges)
                f = sum(sub[f"{var}_{r}"].fillna(0) * sub[f"H_{r}"] for r in ranges) / H.where(H > 0)
            out[var, farm] = f.where(w).mean(("eta_rho", "xi_rho")).load()
    return out


def series(run, ranges, months):
    months = [m for m in months if (TURB_DIR / f"turbulence_{run}_{m}.nc").exists()]
    parts = [farm_means(run, month, ranges) for month in months]
    return {k: xr.concat([p[k] for p in parts], "ocean_time") for k in parts[0]}


months = sorted(f.stem.split("_")[-1] for f in TURB_DIR.glob("turbulence_wakeref_????-??.nc"))
for run in sys.argv[1:] or list(SETS):
    ranges, label = SETS[run]
    exp, wake = series(run, ranges, months), series("wakeref", ranges, months)
    for var, (name, unit) in VARS.items():
        fig, axes = plt.subplots(len(FARMS), 2, figsize=(16, 2.4 * len(FARMS)), sharex=True, layout="constrained")
        for row, farm in zip(axes, FARMS):
            e, w = xr.align(exp[var, farm], wake[var, farm], join="inner")
            # pair by day: stamps are ~13:30 for both runs, align on date
            row[0].plot(w.ocean_time, w, color="tab:gray", label="wakeref")
            row[0].plot(e.ocean_time, e, color="tab:blue", label=run)
            row[1].plot(e.ocean_time, e - w, color="tab:red")
            row[1].axhline(0, color="black", linewidth=0.5)
            row[0].set_ylabel(farm.replace("_", " ") + (f"\n({unit})" if unit else ""))
            for ax in row:
                ax.grid(alpha=0.3)
        axes[0, 0].legend(loc="upper right", ncol=2)
        axes[0, 0].set_title(f"Daily mean {name} ({label})")
        axes[0, 1].set_title(f"{run} - wakeref")
        axes[-1, 0].xaxis.set_major_formatter(mdates.ConciseDateFormatter(mdates.AutoDateLocator()))
        save_fig(fig, f"{var}_{run}_timeseries", f"{var}_timeseries")
        plt.close(fig)
    print(run, "done", flush=True)
