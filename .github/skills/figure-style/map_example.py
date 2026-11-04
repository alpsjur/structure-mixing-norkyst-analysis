"""Reference map plot. Copy and adapt; keep the conventions in SKILL.md."""
from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cmocean.cm as cmo
import matplotlib.pyplot as plt
import numpy as np


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
