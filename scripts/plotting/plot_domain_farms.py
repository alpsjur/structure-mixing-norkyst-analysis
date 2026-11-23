"""Domain map with bathymetry and labelled wind farms -> figures/grid/."""
import os
import sys

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
sys.path.insert(0, ".github/skills/figure-style")
sys.path.insert(0, ".")

import cartopy.crs as ccrs
import cmocean.cm as cmo
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

import map_example
from analysis.io import BASE, MASKS
from map_example import add_farm_outlines, draw_map, save_fig

map_example.MASKS = MASKS
GRID_FILE = f"{BASE}/wakeref/norkyst_avg_0001.nc"  # only used for the static grid (h, mask_rho)
# Label offsets in map units (m) from the farm centre, to avoid overlaps
OFFSETS = {"Nordavind_C": (-250e3, 150e3), "Nordavind_D": (-250e3, -150e3), "Nordvest_C": (-250e3, 0),
           "Sorvest_F": (250e3, -100e3), "Vestavind_B": (-250e3, 0), "Vestavind_F": (-250e3, -100e3)}

grid = xr.open_dataset(GRID_FILE, decode_times=False)
h = grid.h.where(grid.mask_rho > 0).load()
masks = xr.open_dataset(MASKS)

fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={"projection": ccrs.NorthPolarStereo()})
pcm = draw_map(ax, h, cmap=cmo.deep, vmin=0, vmax=float(np.nanpercentile(h, 99.9)))
add_farm_outlines(ax)
fig.colorbar(pcm, ax=ax, orientation="vertical", label="Depth (m)", shrink=0.8)

for name in [v for v in masks.data_vars if not v.endswith("_sectors")]:
    m = masks[name].values > 0
    lon, lat = masks.lon_rho.values[m].mean(), masks.lat_rho.values[m].mean()
    x, y = ax.projection.transform_point(lon, lat, ccrs.PlateCarree())
    dx, dy = OFFSETS.get(name, (200e3, 0))
    ax.annotate(name.replace("_", " "), (x, y), xytext=(x + dx, y + dy), fontsize=9, zorder=6,
                ha="right" if dx < 0 else "left", va="center",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8),
                arrowprops=dict(arrowstyle="-", color="black", lw=0.6))

save_fig(fig, "domain_windfarms", "grid")
