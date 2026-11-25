"""Monthly mean TKE and GLS: experiment | wakeref | experiment - wakeref.

Run from the repo root. One 3-panel figure per month, experiment and variable, for all months with a wakeref
turbulence file (and the run's file) -> figures/tke_map/, figures/gls_map/.
Depth range matches the structure: semisub 0-25 m, spar 0-130 m (stored 0_25 and 25_130 combined, weighted by H).
The difference is taken per day (paired by day), then averaged.
Usage: python scripts/plotting/turbulence_monthly_maps.py [semisub|spar ...]  (default: both)
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
TURB_DIR = Path(OUTDIR) / "turbulence"
SETS = {"semisub": (["0_25"], "0-25 m"), "spar": (["0_25", "25_130"], "0-130 m")}
VARS = {"tke": ("TKE", "m$^2$ s$^{-2}$", cmo.thermal), "gls": ("GLS (mean $\\psi$)", "", cmo.haline)}


def load_range(run, month, ranges):
    ds = xr.open_dataset(TURB_DIR / f"turbulence_{run}_{month}.nc", chunks={"ocean_time": 1})
    if len(ranges) == 1:
        out = {v: ds[f"{v}_{ranges[0]}"] for v in VARS}
    else:
        H = sum(ds[f"H_{r}"] for r in ranges)
        out = {v: sum(ds[f"{v}_{r}"].fillna(0) * ds[f"H_{r}"] for r in ranges) / H.where(H > 0) for v in VARS}
    out = xr.Dataset(out)
    out["ocean_time"] = out.ocean_time.dt.floor("D")
    return out, ds


def prep(ds, lon, lat):
    return ds.load().assign_coords(lon_rho=lon, lat_rho=lat)


for run in sys.argv[1:] or list(SETS):
    ranges, label = SETS[run]
    months = sorted(f.stem.split("_")[-1] for f in TURB_DIR.glob("turbulence_wakeref_????-??.nc"))
    for month in months:
        if not (TURB_DIR / f"turbulence_{run}_{month}.nc").exists():
            continue
        wake, wds = load_range("wakeref", month, ranges)
        exp, _ = load_range(run, month, ranges)
        lon, lat = wds.lon_rho.load(), wds.lat_rho.load()
        wake, exp = xr.align(wake, exp, join="inner")
        n_days = wake.sizes["ocean_time"]
        diff = prep((exp - wake).mean("ocean_time"), lon, lat)
        mean_exp = prep(exp.mean("ocean_time"), lon, lat)
        mean_wake = prep(wake.mean("ocean_time"), lon, lat)
        for var, (name, unit, cmap) in VARS.items():
            u = f" ({unit})" if unit else ""
            vmax = float(np.nanpercentile(np.concatenate([mean_exp[var].values.ravel(),
                                                         mean_wake[var].values.ravel()]), 99))
            dmax = float(np.nanpercentile(np.abs(diff[var]), 99))
            fig, axes = plt.subplots(1, 3, figsize=(24, 10), subplot_kw={"projection": ccrs.NorthPolarStereo()},
                                     layout="constrained")
            pcm = draw_map(axes[0], mean_exp[var], cmap=cmap, vmin=0, vmax=vmax)
            draw_map(axes[1], mean_wake[var], cmap=cmap, vmin=0, vmax=vmax)
            pcm_diff = draw_map(axes[2], diff[var], cmap=cmo.balance, vmin=-dmax, vmax=dmax)
            for ax in axes:
                add_farm_outlines(ax)
            axes[0].set_title(run)
            axes[1].set_title("wakeref")
            axes[2].set_title(f"{run} - wakeref")
            fig.colorbar(pcm, ax=axes[:2], orientation="vertical", label=f"Mean {name}{u}", extend="max", shrink=0.8)
            fig.colorbar(pcm_diff, ax=axes[2], orientation="vertical", label=f"Mean {name} difference{u}", shrink=0.8)
            fig.suptitle(f"Monthly mean {name}, {label}, {month} ({n_days} days)")
            save_fig(fig, f"{var}_{run}_{month}", f"{var}_map")
            plt.close(fig)
            print(run, var, month, n_days, "days; vmax", f"{vmax:.3g}", "dmax", f"{dmax:.3g}", flush=True)
