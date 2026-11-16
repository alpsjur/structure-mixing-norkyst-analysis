"""Whole-period mean maps (all available months): experiment | wakeref | experiment - wakeref.

Run from the repo root. Monthly means are dominated by eddies; averaging over the whole period brings out
the persistent signal. The difference is taken per day, then averaged; all means are weighted by number of days.
  PEA: one figure per run and PEA range -> figures/<range>_map/pea_<run>_whole.png (pea, pea50, pea100, pea150)
  Current speed: semisub over 0-25 m and spar over 0-130 m -> figures/current_map/
With --first, plot only the first time step (day) instead of the period mean; file names end in `_first` (the date is in the figure title).
Usage: python scripts/plotting/period_mean_maps.py [--first] [pea50 pea100 pea150 pea current_semisub current_spar ...]
       (default: all)
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
from matplotlib.colors import LogNorm

import map_example
from analysis.io import MASKS, OUTDIR
from map_example import add_farm_outlines, draw_map, save_fig

map_example.MASKS = MASKS
LOG_NORM = LogNorm(vmin=1, vmax=1000)  # J m-3; same as in the monthly PEA maps
CURRENT_RANGES = {"semisub": (["0_25"], "0-25 m"), "spar": (["0_25", "25_130"], "0-130 m")}


def load_pea(rng):
    def load(run, month):
        ds = xr.open_dataset(Path(OUTDIR) / rng / f"pea_{run}_{month}.nc")
        return ds.pea, ds
    return load


def load_current(ranges):
    def load(run, month):
        ds = xr.open_dataset(Path(OUTDIR) / "current" / f"current_{run}_{month}.nc", chunks={"ocean_time": 1})
        if len(ranges) == 1:
            return ds[f"speed_{ranges[0]}"], ds
        H = sum(ds[f"H_{r}"] for r in ranges)
        speed = sum(ds[f"speed_{r}"].fillna(0) * ds[f"H_{r}"] for r in ranges) / H.where(H > 0)
        return speed, ds
    return load


def period_means(load, directory, pattern, run, first=False):
    """Return (mean exp, mean wakeref, mean of daily diff, n_days, first month, last month).

    With first=True only the first time step is used; first/last month are then both its date.
    """
    months = sorted(f.stem.split("_")[-1] for f in Path(OUTDIR, directory).glob(pattern))
    if first:
        months = months[:1]
    sums = {"exp": 0, "wake": 0, "diff": 0}
    n_days = 0
    for month in months:
        wake, wds = load("wakeref", month)
        exp, _ = load(run, month)
        exp, wake = xr.align(exp, wake, join="inner")
        if first:
            exp, wake = exp.isel(ocean_time=slice(0, 1)), wake.isel(ocean_time=slice(0, 1))
            months = [str(wake.ocean_time.values[0])[:10]]
        sums["exp"] = sums["exp"] + exp.sum("ocean_time").load()
        sums["wake"] = sums["wake"] + wake.sum("ocean_time").load()
        sums["diff"] = sums["diff"] + (exp - wake).sum("ocean_time").load()
        n_days += wake.sizes["ocean_time"]
        lon, lat = wds.lon_rho.load(), wds.lat_rho.load()
    out = [(sums[k] / n_days).assign_coords(lon_rho=lon, lat_rho=lat) for k in ("exp", "wake", "diff")]
    return *out, n_days, months[0], months[-1]


def plot(run, load, directory, pattern, folder, name, label, quantity, pea, first_step=False):
    mean_exp, mean_wake, diff, n_days, first, last = period_means(load, directory, pattern, run, first_step)
    dmax = float(np.nanpercentile(np.abs(diff), 99))
    fig, axes = plt.subplots(1, 3, figsize=(24, 10), subplot_kw={"projection": ccrs.NorthPolarStereo()},
                             layout="constrained")
    if pea:
        # clip noise (PEA < 1 J m-3) so the log scale has no holes
        pcm = draw_map(axes[0], mean_exp.clip(min=1), cmap=cmo.matter, norm=LOG_NORM)
        draw_map(axes[1], mean_wake.clip(min=1), cmap=cmo.matter, norm=LOG_NORM)
        cbar_kw = {"extend": "both"}
    else:
        vmax = float(np.nanpercentile(np.concatenate([mean_exp.values.ravel(), mean_wake.values.ravel()]), 99))
        pcm = draw_map(axes[0], mean_exp, cmap=cmo.thermal, vmin=0, vmax=vmax)
        draw_map(axes[1], mean_wake, cmap=cmo.thermal, vmin=0, vmax=vmax)
        cbar_kw = {"extend": "max"}
    pcm_diff = draw_map(axes[2], diff, cmap=cmo.balance, vmin=-dmax, vmax=dmax)
    for ax in axes:
        add_farm_outlines(ax)
    axes[0].set_title(run)
    axes[1].set_title("wakeref")
    axes[2].set_title(f"{run} - wakeref")
    fig.colorbar(pcm, ax=axes[:2], orientation="vertical", label=quantity if first_step else f"Mean {quantity}", shrink=0.8, **cbar_kw)
    fig.colorbar(pcm_diff, ax=axes[2], orientation="vertical", label=f"{quantity} difference" if first_step else f"Mean {quantity} difference", shrink=0.8)
    if first_step:
        fig.suptitle(f"{quantity}, {label}, first time step ({first})")
        save_fig(fig, f"{name}_{run}_first", folder)
    else:
        fig.suptitle(f"Mean {quantity}, {label}, {first} to {last} ({n_days} days)")
        save_fig(fig, f"{name}_{run}_whole", folder)
    plt.close(fig)
    print(folder, run, first, last, n_days, "days; diff vmax", round(dmax, 3), flush=True)


first_step = "--first" in sys.argv
jobs = [a for a in sys.argv[1:] if a != "--first"] or ["pea", "pea50", "pea100", "pea150", "current_semisub", "current_spar"]
for job in jobs:
    if job.startswith("current_"):
        run = job.split("_")[1]
        ranges, label = CURRENT_RANGES[run]
        plot(run, load_current(ranges), "current", "current_wakeref_????-??.nc", "current_map", "current", label,
             "current speed (m s$^{-1}$)", pea=False, first_step=first_step)
    else:
        for run in ["spar", "semisub"]:
            plot(run, load_pea(job), job, "pea_wakeref_????-??.nc", f"{job}_map", "pea", f"PEA range {job}",
                 "PEA (J m$^{-3}$)", pea=True, first_step=first_step)
