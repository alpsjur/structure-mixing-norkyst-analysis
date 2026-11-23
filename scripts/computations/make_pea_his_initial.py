"""PEA per his record for the first N_FILES his files of a run (initialization transient).

Writes <outdir>/pea150_his_<run>_initial.nc (var `pea`, dims ocean_time, eta_rho, xi_rho).
On the VM pass --outdir files and a small --max-records. Run from the repo root.
"""
import argparse
import os
import sys

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
sys.path.insert(0, ".")

from pathlib import Path

import xarray as xr

from analysis.io import BASE, OUTDIR
from analysis.pea import pea

p = argparse.ArgumentParser()
p.add_argument("--run", default="spar")
p.add_argument("--n-files", type=int, default=2, help="number of his files, from 0001")
p.add_argument("--max-records", type=int, default=None, help="max records in total")
p.add_argument("--zmin", type=float, default=-150)
p.add_argument("--slab", type=int, default=100, help="eta-slab size")
p.add_argument("--outdir", default=f"{OUTDIR}/pea150_his")
a = p.parse_args()

out, times = [], []
for n in range(1, a.n_files + 1):
    with xr.open_dataset(f"{BASE}/{a.run}/norkyst_his_{n:04d}.nc") as ds:
        for i in range(ds.sizes["ocean_time"]):
            if a.max_records is not None and len(out) >= a.max_records:
                break
            out.append(pea(ds, i, zmin=a.zmin, slab=a.slab).astype("float32"))
            times.append(ds.ocean_time.values[i])
            print(a.run, n, i, times[-1], flush=True)

da = xr.concat(out, dim=xr.DataArray(times, dims="ocean_time", name="ocean_time"))
da.attrs.update(zmin=a.zmin, zmax=0.0, ref="ts")
Path(a.outdir).mkdir(parents=True, exist_ok=True)
da.to_dataset().to_netcdf(Path(a.outdir) / f"pea150_his_{a.run}_initial.nc",
                          encoding={"pea": {"zlib": True}})
