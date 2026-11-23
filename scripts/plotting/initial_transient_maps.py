"""Initialization transient: one figure per his record (spar vs wakeref), 1x4 maps.

Panels left to right: SSH and PEA150 spar - wakeref, then SSH and PEA150 spar (1x4).
PEA from scripts/computations/make_pea_his_initial.py. Also a boundary time series.
Run from the repo root.
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
from analysis.io import BASE, MASKS
from map_example import add_farm_outlines, draw_map, save_fig

map_example.MASKS = MASKS

# ---- settings --------------------------------------------------------------
RUN = "spar"
N_FILES = 4
PEA_DIR = Path("files/pea150_his")
SUBFOLDER = f"initial_{RUN}"
KATTEGAT_XI = (359, 509)  # xi range of the Kattegat opening on the southern edge (eta=0)
KATTEGAT_BOX = [9.5, 13.5, 55.0, 58.0]  # lon0, lon1, lat0, lat1 for zoomed maps
BOUNDARY_WIDTH = 10  # cells from the open boundary used for the time series
# -----------------------------------------------------------------------------


def read_zeta(run):
    out = []
    for n in range(1, N_FILES + 1):
        with xr.open_dataset(f"{BASE}/{run}/norkyst_his_{n:04d}.nc") as ds:
            out.append(ds[["zeta", "mask_rho", "lon_rho", "lat_rho"]].load())
    return xr.concat(out, dim="ocean_time")


s, w = read_zeta(RUN), read_zeta("wakeref")
pea_s = xr.open_dataset(PEA_DIR / f"pea150_his_{RUN}_initial.nc").pea.load()
pea_w = xr.open_dataset(PEA_DIR / "pea150_his_wakeref_initial.nc").pea.load()
n = pea_s.sizes["ocean_time"]

land = s.mask_rho.isel(ocean_time=0, drop=True) == 0
dssh = (s.zeta - w.zeta).where(~land).isel(ocean_time=slice(n))
ssh = s.zeta.where(~land).isel(ocean_time=slice(n))
dpea = pea_s - pea_w
coords = {"lon_rho": s.lon_rho, "lat_rho": s.lat_rho}

# fixed scales over all frames so frames are comparable when flicking through
vssh = float(np.nanpercentile(np.abs(dssh.values[1:]), 99.5))
vpea = float(np.nanpercentile(np.abs(dpea.values[1:]), 99.5))
vfull = float(np.nanpercentile(np.abs(ssh.values), 99.5))
norm = LogNorm(vmin=1, vmax=1000)
t0 = s.ocean_time.values[0]

def make_figs(subfolder, extent=None):
    """One 1x4 figure per record; extent = [lon0, lon1, lat0, lat1] zooms the maps."""
    for i in range(n):
        hours = int((s.ocean_time.values[i] - t0) / np.timedelta64(1, "h"))
        fig, axs = plt.subplots(1, 4, figsize=(32, 9), subplot_kw={"projection": ccrs.NorthPolarStereo()})
        panels = [
            (axs[0], dssh.isel(ocean_time=i), dict(cmap=cmo.balance, vmin=-vssh, vmax=vssh), "SSH spar - wakeref (m)"),
            (axs[2], ssh.isel(ocean_time=i), dict(cmap=cmo.balance, vmin=-vfull, vmax=vfull), "SSH spar (m)"),
            (axs[1], dpea.isel(ocean_time=i), dict(cmap=cmo.balance, vmin=-vpea, vmax=vpea), "PEA150 spar - wakeref (J m$^{-3}$)"),
            (axs[3], pea_s.isel(ocean_time=i).clip(min=1), dict(cmap=cmo.matter, norm=norm), "PEA150 spar (J m$^{-3}$)"),
        ]
        for ax, da, kw, label in panels:
            da = da.drop_vars([c for c in da.coords if c not in ("lon_rho", "lat_rho")]).assign_coords(**coords)
            pcm = draw_map(ax, da, **kw)
            if extent is not None:
                ax.set_extent(extent, crs=ccrs.PlateCarree())
            add_farm_outlines(ax)
            ax.set_title(label)
            fig.colorbar(pcm, ax=ax, orientation="vertical", shrink=0.6, pad=0.02,
                         extend="both" if "norm" in kw else "neither")
        fig.suptitle(f"{RUN}: t = {hours} h after initialization ({str(s.ocean_time.values[i])[:16]})", y=0.97)
        save_fig(fig, f"initial_{RUN}_t{hours:03d}h", subfolder)
        plt.close(fig)
        print("saved", subfolder, hours, flush=True)


if "--no-maps" not in sys.argv:
    make_figs(SUBFOLDER)
    make_figs(f"{SUBFOLDER}_kattegat", KATTEGAT_BOX)

# time series of |difference| in a strip along the boundary (ocean cells only):
# Kattegat (southern boundary, xi range below) and all domain edges
ny, nx = land.shape
b = BOUNDARY_WIDTH
edge = np.zeros((ny, nx), bool)
edge[:b, :] = edge[-b:, :] = edge[:, :b] = edge[:, -b:] = True
kattegat = np.zeros((ny, nx), bool)
kattegat[:b, KATTEGAT_XI[0]:KATTEGAT_XI[1] + 1] = True
regions = {"Kattegat boundary": kattegat & ~land.values, "all domain edges": edge & ~land.values}
hrs = (s.ocean_time.values[:n] - t0) / np.timedelta64(1, "h")
fig, axs = plt.subplots(2, 2, figsize=(12, 6), sharex=True, sharey="row")
for col, (name, sel) in enumerate(regions.items()):
    for ax, d, label in [(axs[0, col], dssh, "SSH (m)"), (axs[1, col], dpea, "PEA150 (J m$^{-3}$)")]:
        v = np.abs(d.values)[:, sel]
        ax.plot(hrs, np.nanmean(v, axis=1), label="mean |spar - wakeref|")
        ax.plot(hrs, np.nanmax(v, axis=1), label="max |spar - wakeref|")
        ax.set_ylabel(label)
    axs[0, col].set_title(f"{RUN}: {name} ({b} cells)")
    axs[1, col].set_xlabel("hours since initialization")
axs[0, 0].legend()
save_fig(fig, f"initial_{RUN}_boundary_timeseries", SUBFOLDER)
