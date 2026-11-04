"""PEA map of spar minus wakeref for one time record. Run from the repo root."""
import os
import sys
from pathlib import Path

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
sys.path.insert(0, ".github/skills/figure-style")
sys.path.insert(0, ".")

import cmocean.cm as cmo
import numpy as np
import xarray as xr

from analysis.pea import pea
from map_example import plot_map

BASE = Path("/lustre/storeB/project/nwp/havvind/hav/structure_mixing/experiments")
fname = "norkyst_avg_0001.nc"

fields = {}
for run in ("wakeref", "spar"):
    ds = xr.open_dataset(BASE / run / fname)
    fields[run] = pea(ds)
    print(run, ds.ocean_time.values[0], float(fields[run].min()), float(fields[run].max()))

anom = fields["spar"] - fields["wakeref"]
vmax = float(np.nanpercentile(np.abs(anom), 99.9))
print("anomaly range", float(anom.min()), float(anom.max()), "vmax", vmax)
plot_map(anom, "PEA spar - wakeref (J m$^{-3}$)", "pea_spar-minus-wakeref_2022-02-02",
         cmap=cmo.balance, vmin=-vmax, vmax=vmax)
plot_map(fields["wakeref"], "PEA wakeref (J m$^{-3}$)", "pea_wakeref_2022-02-02",
         vmin=0, vmax=float(np.nanpercentile(fields["wakeref"], 99.5)))
