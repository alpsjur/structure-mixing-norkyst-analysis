"""Reference map plot. Copy and adapt; keep the conventions in SKILL.md."""
from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cmocean.cm as cmo
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from shapely.geometry import Polygon
from shapely.ops import unary_union

MASKS = Path("files/windfarm_masks.nc")
TURBINES = Path.home() / "structure-mixing-grid-utils" / "turbine_coordinates"


def farm_outline(mask, lon_rho, lat_rho):
    """Exact outline of the mask cells as a shapely (Multi)Polygon in lon/lat.

    Cell corners are the mean of the four surrounding rho points, so neighbouring cells share
    identical corners and the union has no slivers.
    """
    eta, xi = np.nonzero(mask)
    e0, e1, x0, x1 = eta.min(), eta.max(), xi.min(), xi.max()
    sl = (slice(e0 - 1, e1 + 2), slice(x0 - 1, x1 + 2))
    lon, lat = lon_rho[sl], lat_rho[sl]
    clon = 0.25 * (lon[:-1, :-1] + lon[1:, :-1] + lon[:-1, 1:] + lon[1:, 1:])
    clat = 0.25 * (lat[:-1, :-1] + lat[1:, :-1] + lat[:-1, 1:] + lat[1:, 1:])
    # clon[i, j] is the lower corner of rho cell (e0 + i, x0 + j); the upper corner is clon[i + 1, j + 1]
    polys = []
    for i, j in zip(eta - e0, xi - x0):
        ring = [(clon[i + di, j + dj], clat[i + di, j + dj]) for di, dj in ((0, 0), (0, 1), (1, 1), (1, 0))]
        polys.append(Polygon(ring))
    return unary_union(polys)


def add_farm_outlines(ax, farms=None):
    """Outline wind-farm masks (all if farms is None); call after the land/coastline layers.

    Draws the exact boundary of the masked rho cells as polygons (no smoothing).
    """
    masks = xr.open_dataset(MASKS)
    lon_rho, lat_rho = masks["lon_rho"].values, masks["lat_rho"].values
    for name in farms or [v for v in masks.data_vars if not v.endswith("_sectors")]:
        ax.add_geometries(
            [farm_outline(masks[name].values > 0, lon_rho, lat_rho)], crs=ccrs.PlateCarree(),
            facecolor="none", edgecolor="black", linewidth=0.8, zorder=4,
        )


def add_turbines(ax, files=None):
    """Plot individual turbines at their actual lon/lat (not snapped to grid cells)."""
    for path in files or sorted(TURBINES.glob("*.txt")):
        rows = [ln.split() for ln in Path(path).read_text().splitlines()
                if ln.strip() and not ln.startswith("[")]
        lon, lat = np.array(rows, dtype=float).T
        ax.scatter(lon, lat, s=2, marker=".", color="black",
                   transform=ccrs.PlateCarree(), zorder=5)


def plot_map(da, label, fname, cmap=cmo.deep, vmin=None, vmax=None):
    """da: 2D DataArray with lon_rho/lat_rho coordinates (NaN on land)."""
    fig, ax = plt.subplots(
        figsize=(10, 10), subplot_kw={"projection": ccrs.NorthPolarStereo()}
    )
    pcm = ax.pcolormesh(
        da["lon_rho"], da["lat_rho"], da,
        cmap=cmap, vmin=vmin, vmax=vmax, shading="auto",
        transform=ccrs.PlateCarree(), zorder=1, rasterized=True,
    )
    ax.add_feature(cfeature.LAND, facecolor="lightgray", zorder=2)
    ax.add_feature(cfeature.COASTLINE, zorder=3)

    # Set extent from the projected grid; a lon/lat box would not fit a rotated domain
    xyz = ax.projection.transform_points(
        ccrs.PlateCarree(), da["lon_rho"].values, da["lat_rho"].values
    )
    ax.set_extent(
        [np.nanmin(xyz[..., 0]), np.nanmax(xyz[..., 0]),
         np.nanmin(xyz[..., 1]), np.nanmax(xyz[..., 1])],
        crs=ax.projection,
    )

    gl = ax.gridlines(
        draw_labels=True, dms=True, x_inline=False, y_inline=False,
        linewidth=0.5, color="gray", alpha=0.5, linestyle="--",
    )
    gl.top_labels = False
    gl.right_labels = False

    fig.colorbar(pcm, ax=ax, orientation="vertical", label=label)

    out = Path("figures")
    out.mkdir(exist_ok=True)
    fig.savefig(out / f"{fname}.png", dpi=300, bbox_inches="tight")
    fig.savefig(out / f"{fname}.pdf", bbox_inches="tight")
    return fig, ax
