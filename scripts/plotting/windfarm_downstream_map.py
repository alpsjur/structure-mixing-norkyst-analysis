"""Map of the wind-farm + downstream-extension masks over the whole-period mean current.

One 6-panel figure (one per farm), zoomed to the farm + extension bounding box: background =
whole-period mean current speed (0-25 m, wakeref, weighted by n_days), quiver = mean current
direction, farm outline (black) and farm+downstream extension outline (red), see
scripts/computations/make_windfarm_downstream_masks.py and docs/notes.md.

Usage: python scripts/plotting/windfarm_downstream_map.py
Output: figures/grid/windfarm_downstream_masks.png
"""
import os
import sys

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
sys.path.insert(0, ".github/skills/figure-style")
sys.path.insert(0, ".")

from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cmocean.cm as cmo
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from map_example import farm_outline, save_fig
from analysis.io import BASE, MASKS, OUTDIR

DOWNSTREAM_MASKS = Path("files/windfarm_downstream_masks.nc")  # VM test copy; Lustre masks/ once finalised
CURRENT_DIR = Path(OUTDIR) / "current"
PAD = 15  # extra rho cells around the farm+extension bounding box
QUIVER_STRIDE = 8  # plot every Nth grid cell for the quiver
ARROW_KM = 10.0  # length of the big mean-direction arrows, for display only

masks = xr.open_dataset(MASKS)
ext = xr.open_dataset(DOWNSTREAM_MASKS)
FARMS = [v for v in masks.data_vars if not v.endswith("_sectors")]

with xr.open_dataset(f"{BASE}/wakeref/norkyst_avg_0001.nc") as g:
    angle = g.angle.load()

# whole-period mean current (0-25 m, wakeref), weighted by n_days
months = sorted(f.stem.split("_")[-1] for f in CURRENT_DIR.glob("current_wakeref_????-??.nc"))
u_sum = v_sum = n_total = 0
for month in months:
    ds = xr.open_dataset(CURRENT_DIR / f"current_wakeref_{month}.nc")
    n_days = float(ds.attrs["n_days"])
    u_sum = u_sum + n_days * ds["ubar_0_25"].fillna(0).mean("ocean_time")
    v_sum = v_sum + n_days * ds["vbar_0_25"].fillna(0).mean("ocean_time")
    n_total += n_days
    ds.close()
u_mean = (u_sum / n_total).load()
v_mean = (v_sum / n_total).load()
east = u_mean * np.cos(angle) - v_mean * np.sin(angle)
north = u_mean * np.sin(angle) + v_mean * np.cos(angle)
speed = np.hypot(east, north)

lon_rho, lat_rho = masks.lon_rho, masks.lat_rho

fig, axes = plt.subplots(2, 3, figsize=(18, 12), subplot_kw={"projection": ccrs.NorthPolarStereo()},
                          layout="constrained")
for ax, farm in zip(axes.ravel(), FARMS):
    farm_mask = masks[farm].values > 0
    ext_mask = ext[f"{farm}_extended"].values > 0
    eta, xi = np.nonzero(ext_mask)
    e0, e1 = max(eta.min() - PAD, 0), eta.max() + PAD
    x0, x1 = max(xi.min() - PAD, 0), xi.max() + PAD
    sl = dict(eta_rho=slice(e0, e1), xi_rho=slice(x0, x1))

    sp = speed.isel(**sl).assign_coords(lon_rho=lon_rho.isel(**sl), lat_rho=lat_rho.isel(**sl))
    pcm = ax.pcolormesh(sp["lon_rho"], sp["lat_rho"], sp, cmap=cmo.thermal, vmin=0,
                         transform=ccrs.PlateCarree(), zorder=1, rasterized=True)
    ax.add_feature(cfeature.LAND, facecolor="lightgray", zorder=2)
    ax.add_feature(cfeature.COASTLINE, zorder=3)

    e_sub = east.isel(**sl).values[::QUIVER_STRIDE, ::QUIVER_STRIDE]
    n_sub = north.isel(**sl).values[::QUIVER_STRIDE, ::QUIVER_STRIDE]
    lon_sub = lon_rho.isel(**sl).values[::QUIVER_STRIDE, ::QUIVER_STRIDE]
    lat_sub = lat_rho.isel(**sl).values[::QUIVER_STRIDE, ::QUIVER_STRIDE]
    ax.quiver(lon_sub, lat_sub, e_sub, n_sub, transform=ccrs.PlateCarree(), zorder=4,
              color="black", width=0.004)

    ax.add_geometries([farm_outline(ext_mask, lon_rho.values, lat_rho.values)], crs=ccrs.PlateCarree(),
                       facecolor="none", edgecolor="red", linewidth=1.2, zorder=5)
    ax.add_geometries([farm_outline(farm_mask, lon_rho.values, lat_rho.values)], crs=ccrs.PlateCarree(),
                       facecolor="none", edgecolor="black", linewidth=1.5, zorder=6)

    # big arrow(s): the mean current direction(s) used to build the corridor/circle mask,
    # read back from the attributes written by make_windfarm_downstream_masks.py
    attrs = ext[f"{farm}_extension"].attrs
    deg2rad = np.pi / 180.0
    R_EARTH = 6_371_000.0

    def draw_arrow(lon0, lat0, direction_deg):
        theta = np.radians(direction_deg)
        dx = ARROW_KM * 1000.0 * np.sin(theta)
        dy = ARROW_KM * 1000.0 * np.cos(theta)
        dlon = dx / (R_EARTH * np.cos(lat0 * deg2rad) * deg2rad)
        dlat = dy / (R_EARTH * deg2rad)
        ax.annotate(
            "", xy=(lon0 + dlon, lat0 + dlat), xytext=(lon0, lat0),
            xycoords=ccrs.PlateCarree()._as_mpl_transform(ax),
            textcoords=ccrs.PlateCarree()._as_mpl_transform(ax),
            arrowprops=dict(arrowstyle="-|>", color="deepskyblue", linewidth=3, mutation_scale=25), zorder=7,
        )

    if attrs["shape"] == "circle":
        feta, fxi = np.nonzero(farm_mask)
        lon0, lat0 = lon_rho.values[feta, fxi].mean(), lat_rho.values[feta, fxi].mean()
        draw_arrow(lon0, lat0, attrs["mean_current_direction_deg"])
    else:
        labels = masks[f"{farm}_sectors"].values
        for i, direction_deg in enumerate(attrs["sector_direction_deg"], start=1):
            seta, sxi = np.nonzero(labels == i)
            lon0, lat0 = lon_rho.values[seta, sxi].mean(), lat_rho.values[seta, sxi].mean()
            draw_arrow(lon0, lat0, direction_deg)

    xyz = ax.projection.transform_points(ccrs.PlateCarree(), sp["lon_rho"].values, sp["lat_rho"].values)
    ax.set_extent([np.nanmin(xyz[..., 0]), np.nanmax(xyz[..., 0]),
                   np.nanmin(xyz[..., 1]), np.nanmax(xyz[..., 1])], crs=ax.projection)
    gl = ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False,
                       linewidth=0.5, color="gray", alpha=0.5, linestyle="--")
    gl.top_labels = False
    gl.right_labels = False
    ax.set_title(farm.replace("_", " "))

fig.colorbar(pcm, ax=axes, orientation="vertical", label="Mean current speed (m s$^{-1}$), 0-25 m, wakeref",
             shrink=0.8)
fig.suptitle("Wind-farm masks (black) and farm+downstream extension (red) over the whole-period mean current")
save_fig(fig, "windfarm_downstream_masks", "grid")
print("done")
