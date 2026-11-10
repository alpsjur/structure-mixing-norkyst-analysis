"""Maps of SSH (zeta) spar - wakeref for the first N matched time steps of a month. Run from the repo root."""
import os
import sys

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
sys.path.insert(0, ".github/skills/figure-style")
sys.path.insert(0, "scripts")

from pathlib import Path

import cmocean.cm as cmo
import numpy as np
import xarray as xr

import map_example
from scripts.computations.make_monthly_anomalies import file_times, month_of
from map_example import add_farm_outlines, plot_map

map_example.MASKS = Path("/lustre/storeB/project/nwp/havvind/hav/structure_mixing/masks/windfarm_masks.nc")

# ---- settings --------------------------------------------------------------
MONTH = "2022-02"
N_STEPS = 3
# -----------------------------------------------------------------------------

spar_t, wake_t = file_times("spar"), file_times("wakeref")
times = sorted(t for t in spar_t if t in wake_t and month_of(t) == MONTH)[:N_STEPS]

for t in times:
    with xr.open_dataset(spar_t[t]) as s, xr.open_dataset(wake_t[t]) as w:
        diff = (s.zeta.isel(ocean_time=0) - w.zeta.isel(ocean_time=0)).load()
        date = str(s.ocean_time.values[0])[:10]
    vmax = float(np.nanpercentile(np.abs(diff), 99))
    fname = f"ssh_spar-minus-wakeref_{date}"
    fig, ax = plot_map(diff, "SSH spar - wakeref (m)", fname, cmap=cmo.balance, vmin=-vmax, vmax=vmax)
    add_farm_outlines(ax)
    fig.savefig(f"figures/{fname}.png", dpi=300, bbox_inches="tight")
    fig.savefig(f"figures/{fname}.pdf", bbox_inches="tight")
    print(date, "vmax", vmax)
