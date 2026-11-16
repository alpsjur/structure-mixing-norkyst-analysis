"""Compare PEA definitions: wakeref PEA averaged over the whole period, one panel per definition.

Run from the repo root -> figures/pea_comparison_map/. Ranges: whole column (pea) and surface to 50/100/150 m.
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
import xarray as xr
from matplotlib.colors import LogNorm

import map_example
from analysis.io import MASKS, OUTDIR
from map_example import add_farm_outlines, draw_map, save_fig

map_example.MASKS = MASKS
RUN = "wakeref"
RANGES = {"pea": "Whole column", "pea50": "0-50 m", "pea100": "0-100 m", "pea150": "0-150 m"}
LOG_NORM = LogNorm(vmin=1, vmax=1000)  # J m-3; shared so panels are comparable

fig, axes = plt.subplots(1, len(RANGES), figsize=(8 * len(RANGES), 10),
                         subplot_kw={"projection": ccrs.NorthPolarStereo()}, layout="constrained")
for ax, (rng, label) in zip(axes, RANGES.items()):
    files = sorted((Path(OUTDIR) / rng).glob(f"pea_{RUN}_????-??.nc"))
    total, n_days = 0, 0
    for f in files:
        with xr.open_dataset(f) as ds:
            n = ds.pea.sizes["ocean_time"]
            total = total + ds.pea.sum("ocean_time").load() * 1.0
            n_days += n
            lon, lat = ds.lon_rho.load(), ds.lat_rho.load()
    mean = (total / n_days).assign_coords(lon_rho=lon, lat_rho=lat).clip(min=1)  # clip noise for log scale
    pcm = draw_map(ax, mean, cmap=cmo.matter, norm=LOG_NORM)
    add_farm_outlines(ax)
    ax.set_title(f"{label} ({len(files)} months, {n_days} days)")
    print(rng, len(files), "months", n_days, "days")

fig.colorbar(pcm, ax=axes, orientation="vertical", label="Mean PEA (J m$^{-3}$)", extend="both", shrink=0.8)
fig.suptitle(f"{RUN}: PEA averaged over the whole period, by PEA definition")
save_fig(fig, f"pea_definitions_{RUN}", "pea_comparison_map")
