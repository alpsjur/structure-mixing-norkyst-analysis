"""Zoomed bathymetry maps per wind farm with mask outline and turbines. Run from the repo root."""
import os
import sys

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
sys.path.insert(0, ".github/skills/figure-style")

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cmocean.cm as cmo
import matplotlib.pyplot as plt
import xarray as xr
from pathlib import Path

from map_example import MASKS, TURBINES, add_farm_outlines, add_turbines

GRID = Path.home() / "structure-mixing-grid-utils" / "grid_files" / "norkyst_grd_v31.nc"
MARGIN = 0.15  # degrees around the mask

grid = xr.open_dataset(GRID)
h = grid.h.where(grid.mask_rho > 0)
masks = xr.open_dataset(MASKS)
Path("figures").mkdir(exist_ok=True)

for name in [v for v in masks.data_vars if not v.endswith("_sectors")]:
    m = masks[name] == 1
    lon, lat = masks.lon_rho.where(m), masks.lat_rho.where(m)
    extent = [float(lon.min()) - 2 * MARGIN, float(lon.max()) + 2 * MARGIN,
              float(lat.min()) - MARGIN, float(lat.max()) + MARGIN]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"projection": ccrs.NorthPolarStereo()})
    pcm = ax.pcolormesh(grid.lon_rho, grid.lat_rho, h, cmap=cmo.deep, shading="auto",
                        transform=ccrs.PlateCarree(), zorder=1, rasterized=True)
    ax.add_feature(cfeature.LAND, facecolor="lightgray", zorder=2)
    ax.add_feature(cfeature.COASTLINE, zorder=3)
    ax.set_extent(extent, crs=ccrs.PlateCarree())
    add_farm_outlines(ax, [name])
    add_turbines(ax, sorted(TURBINES.glob("*.txt")))
    gl = ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False,
                      linewidth=0.5, color="gray", alpha=0.5, linestyle="--")
    gl.top_labels = False
    gl.right_labels = False
    fig.colorbar(pcm, ax=ax, orientation="vertical", label="Depth (m)", shrink=0.8)
    ax.set_title(name)
    base = f"windfarm-outline_{name}"
    fig.savefig(f"figures/{base}.png", dpi=300, bbox_inches="tight")
    fig.savefig(f"figures/{base}.pdf", bbox_inches="tight")
    plt.close(fig)
    print("saved", base)
