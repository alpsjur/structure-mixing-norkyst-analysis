"""Maps of February mean PEA for wakeref and of mean (spar - wakeref). Run from the repo root."""
import os
import sys

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
sys.path.insert(0, ".github/skills/figure-style")

import cmocean.cm as cmo
import numpy as np
import xarray as xr

from pathlib import Path

import map_example
from map_example import add_farm_outlines, plot_map

map_example.MASKS = Path("/lustre/storeB/project/nwp/havvind/hav/structure_mixing/masks/windfarm_masks.nc")
PEA_DIR = "/lustre/storeB/project/nwp/havvind/hav/structure_mixing/processed/pea"
MONTH = "2022-02"

wake = xr.open_dataset(f"{PEA_DIR}/pea_wakeref_{MONTH}.nc")
spar = xr.open_dataset(f"{PEA_DIR}/pea_spar_{MONTH}.nc")

# PEA is nonlinear: difference per day, then average
wake_aligned, spar_aligned = xr.align(wake.pea, spar.pea, join="inner")
mean_wake = wake_aligned.mean("ocean_time").load()
anom = (spar_aligned - wake_aligned).mean("ocean_time").load()
mean_wake = mean_wake.assign_coords(lon_rho=wake.lon_rho, lat_rho=wake.lat_rho)
anom = anom.assign_coords(lon_rho=wake.lon_rho, lat_rho=wake.lat_rho)
print("days used:", wake_aligned.sizes["ocean_time"])

def with_farms(da, label, fname, **kw):
    fig, ax = plot_map(da, label, fname, **kw)
    add_farm_outlines(ax)
    fig.savefig(f"figures/{fname}.png", dpi=300, bbox_inches="tight")
    fig.savefig(f"figures/{fname}.pdf", bbox_inches="tight")


with_farms(mean_wake, "Mean PEA wakeref (J m$^{-3}$)", f"pea_wakeref_{MONTH}",
           cmap=cmo.matter, vmin=0, vmax=float(np.nanpercentile(mean_wake, 99.5)))
vmax = float(np.nanpercentile(np.abs(anom), 99))
with_farms(anom, "Mean PEA spar - wakeref (J m$^{-3}$)", f"pea_spar-minus-wakeref_{MONTH}",
           cmap=cmo.balance, vmin=-vmax, vmax=vmax)

# Anomaly at selected daily records, each with its own symmetric colour scale
daily = (spar_aligned - wake_aligned).assign_coords(lon_rho=wake.lon_rho, lat_rho=wake.lat_rho)
snaps = {i: daily.isel(ocean_time=i).load() for i in (0, 1, 2, -1)}
for s in snaps.values():
    date = str(s.ocean_time.values)[:10]
    vmax_d = float(np.nanpercentile(np.abs(s), 99))
    with_farms(s, "PEA spar - wakeref (J m$^{-3}$)", f"pea_spar-minus-wakeref_{date}",
               cmap=cmo.balance, vmin=-vmax_d, vmax=vmax_d)
