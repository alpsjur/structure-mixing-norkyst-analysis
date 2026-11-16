"""Monthly mean current speed: experiment | wakeref | experiment - wakeref.

Run from the repo root. One 3-panel figure per month and experiment, for all available months, for two
depth ranges (matching the structure): figures/current_map/ (semisub over 0-25 m, spar over 0-130 m).
Each run is only plotted over its own depth range.
The spar range combines the stored 0_25 and 25_130 ranges, weighted by thickness H.
The difference is taken per day, then averaged.
Usage: python scripts/plotting/current_monthly_maps.py [semisub|spar ...]  (default: both)
"""
import os
import sys

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
sys.path.insert(0, ".github/skills/figure-style")
sys.path.insert(0, ".")

from pathlib import Path

import cartopy.crs as ccrs
import cmocean.cm as cmo
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

import map_example
from analysis.io import MASKS, OUTDIR
from map_example import add_farm_outlines, draw_map, save_fig

map_example.MASKS = MASKS
CURRENT_DIR = Path(OUTDIR) / "current"
# run (= figure set) -> stored ranges combined into it, and a label for titles
SETS = {"semisub": (["0_25"], "0-25 m"), "spar": (["0_25", "25_130"], "0-130 m")}
VARS = ["speed"]


def load_range(run, month, ranges):
    """Daily thickness-weighted mean of speed over the combined ranges (ocean_time, eta, xi)."""
    ds = xr.open_dataset(CURRENT_DIR / f"current_{run}_{month}.nc", chunks={"ocean_time": 1})
    if len(ranges) == 1:
        return xr.Dataset({v: ds[f"{v}_{ranges[0]}"] for v in VARS}), ds
    H = sum(ds[f"H_{r}"] for r in ranges)
    out = {v: sum((ds[f"{v}_{r}"].fillna(0) * ds[f"H_{r}"]) for r in ranges) / H.where(H > 0) for v in VARS}
    return xr.Dataset(out), ds


def prep(ds, lon, lat):
    return ds.load().assign_coords(lon_rho=lon, lat_rho=lat)


for name in sys.argv[1:] or list(SETS):
    ranges, label = SETS[name]
    folder = "current_map"
    months = sorted(f.stem.split("_")[-1] for f in CURRENT_DIR.glob("current_wakeref_????-??.nc"))
    for month in months:
        wake, wds = load_range("wakeref", month, ranges)
        lon, lat = wds.lon_rho.load(), wds.lat_rho.load()
        for run in [name]:
            exp, _ = load_range(run, month, ranges)
            wake_a, exp_a = xr.align(wake, exp, join="inner")
            n_days = wake_a.sizes["ocean_time"]
            diff = prep((exp_a - wake_a).mean("ocean_time"), lon, lat)
            mean_exp = prep(exp_a.mean("ocean_time"), lon, lat)
            mean_wake = prep(wake_a.mean("ocean_time"), lon, lat)
            vmax = float(np.nanpercentile(np.concatenate([mean_exp.speed.values.ravel(),
                                                         mean_wake.speed.values.ravel()]), 99))
            dmax = float(np.nanpercentile(np.abs(diff.speed), 99))

            fig, axes = plt.subplots(1, 3, figsize=(24, 10), subplot_kw={"projection": ccrs.NorthPolarStereo()},
                                     layout="constrained")
            pcm = draw_map(axes[0], mean_exp.speed, cmap=cmo.thermal, vmin=0, vmax=vmax)
            draw_map(axes[1], mean_wake.speed, cmap=cmo.thermal, vmin=0, vmax=vmax)
            pcm_diff = draw_map(axes[2], diff.speed, cmap=cmo.balance, vmin=-dmax, vmax=dmax)
            for ax in axes:
                add_farm_outlines(ax)
            axes[0].set_title(run)
            axes[1].set_title("wakeref")
            axes[2].set_title(f"{run} - wakeref")
            fig.colorbar(pcm, ax=axes[:2], orientation="vertical", label="Mean current speed (m s$^{-1}$)",
                         extend="max", shrink=0.8)
            fig.colorbar(pcm_diff, ax=axes[2], orientation="vertical",
                         label="Mean current speed difference (m s$^{-1}$)", shrink=0.8)
            fig.suptitle(f"Monthly mean current speed, {label}, {month} ({n_days} days)")
            save_fig(fig, f"current_{run}_{month}", folder)
            plt.close(fig)
            print(name, run, month, n_days, "days; vmax", round(vmax, 3), "dmax", round(dmax, 3), flush=True)
