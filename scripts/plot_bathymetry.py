"""Bathymetry map with wind-farm outlines -> figures/grid/. Run from the repo root."""
import os
import sys

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
sys.path.insert(0, ".github/skills/figure-style")

from pathlib import Path

import cartopy.crs as ccrs
import cmocean.cm as cmo
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

import map_example
from map_example import add_farm_outlines, draw_map, save_fig

BASE = Path("/lustre/storeB/project/nwp/havvind/hav/structure_mixing")
map_example.MASKS = BASE / "masks" / "windfarm_masks.nc"
MEAN_FILE = BASE / "processed" / "mean" / "mean_wakeref_2022-02.nc"  # only used for the static grid (h, mask_rho)

grid = xr.open_dataset(MEAN_FILE)
h = grid.h.where(grid.mask_rho > 0).load()

fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={"projection": ccrs.NorthPolarStereo()})
pcm = draw_map(ax, h, cmap=cmo.deep, vmin=0, vmax=float(np.nanpercentile(h, 99.9)))
add_farm_outlines(ax)
fig.colorbar(pcm, ax=ax, orientation="vertical", label="Depth (m)")
save_fig(fig, "bathymetry_windfarms", "grid")
