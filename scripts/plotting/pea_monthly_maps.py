"""Monthly mean PEA: experiment | wakeref (log, shared colorbar) | experiment - wakeref -> figures/pea/.

Run from the repo root. One 3-panel figure per month and experiment.
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
PEA_DIR = Path(OUTDIR) / "pea"
MONTHS = ["2022-02", "2022-03", "2022-04", "2022-05"]
RUNS = ["spar", "semisub"]
LOG_NORM = LogNorm(vmin=1, vmax=1000)  # J m-3; same for all runs and months

for month in MONTHS:
    wake = xr.open_dataset(PEA_DIR / f"pea_wakeref_{month}.nc")
    lon, lat = wake.lon_rho, wake.lat_rho
    for run in RUNS:
        exp = xr.open_dataset(PEA_DIR / f"pea_{run}_{month}.nc")
        pea_exp, pea_wake = xr.align(exp.pea, wake.pea, join="inner")
        n_days = pea_wake.sizes["ocean_time"]

        def coords(da):
            return da.load().assign_coords(lon_rho=lon, lat_rho=lat)

        # Log scale needs positive values; clip noise (PEA < 1 J m-3) to the lower limit
        mean_exp = coords(pea_exp.mean("ocean_time")).clip(min=1)
        mean_wake = coords(pea_wake.mean("ocean_time")).clip(min=1)
        # PEA is nonlinear: difference per day, then average
        diff = coords((pea_exp - pea_wake).mean("ocean_time"))
        vmax = float(np.nanpercentile(np.abs(diff), 99))

        fig, axes = plt.subplots(1, 3, figsize=(24, 10), subplot_kw={"projection": ccrs.NorthPolarStereo()},
                                 layout="constrained")
        pcm_pea = draw_map(axes[0], mean_exp, cmap=cmo.matter, norm=LOG_NORM)
        draw_map(axes[1], mean_wake, cmap=cmo.matter, norm=LOG_NORM)
        pcm_diff = draw_map(axes[2], diff, cmap=cmo.balance, vmin=-vmax, vmax=vmax)
        for ax in axes:
            add_farm_outlines(ax)
        axes[0].set_title(f"{run}")
        axes[1].set_title("wakeref")
        axes[2].set_title(f"{run} - wakeref")
        fig.colorbar(pcm_pea, ax=axes[:2], orientation="vertical", label="Mean PEA (J m$^{-3}$)",
                     extend="both", shrink=0.8)
        fig.colorbar(pcm_diff, ax=axes[2], orientation="vertical", label="Mean PEA difference (J m$^{-3}$)",
                     shrink=0.8)
        fig.suptitle(f"Monthly mean PEA, {month} ({n_days} days)")
        save_fig(fig, f"pea_{run}_{month}", "pea")
        plt.close(fig)
        print(run, month, n_days, "days; diff vmax", round(vmax, 1))
