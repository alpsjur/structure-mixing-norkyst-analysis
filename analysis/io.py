"""Paths and file helpers shared by the scripts."""
import glob

import numpy as np
import xarray as xr

ROOT = "/lustre/storeB/project/nwp/havvind/structure_mixing"
BASE = f"{ROOT}/experiments"
OUTDIR = f"{ROOT}/processed"
MASKS = f"{ROOT}/masks/windfarm_masks.nc"


def file_times(run):
    """Return {ocean_time (s): path} for all avg files of a run."""
    out = {}
    for f in sorted(glob.glob(f"{BASE}/{run}/norkyst_avg_*.nc")):
        with xr.open_dataset(f, decode_times=False) as ds:
            out[float(ds.ocean_time.values[0])] = f
    return out


def month_of(t):
    return str(np.datetime64(int(t), "s").astype("datetime64[M]"))


def eta_dim(da):
    return next(d for d in da.dims if d.startswith("eta_"))
