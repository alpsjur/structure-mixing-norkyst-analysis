"""Daily depth-range mean TKE, GLS and dissipation of one run for one month, from the his files.

Two depth ranges by default: 0-25 m (semisub extent) and 25-130 m (down to spar extent).
Per range: tke (m2 s-2), gls (mean psi), eps (mean of gls**1.5 per 3-hourly record, GEN closure),
H (water thickness inside the range, m). Daily value = mean of the 3-hourly records of the his
file (the 00:00 record of the first file, which belongs to the previous day, is skipped).
Combine ranges with thickness weights: (m1*H1 + m2*H2) / (H1 + H2)

Output: <outdir>/turbulence_<run>_<YYYY-MM>.nc with dims (ocean_time, eta_rho, xi_rho).
Works for any run, including wakeref.

Usage (repo root):
    python scripts/computations/make_turbulence.py wakeref 2022-02 --max-files 1 --outdir files/test
"""
import argparse
import glob
import os
import sys

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
sys.path.insert(0, ".")

import numpy as np
import xarray as xr

from analysis.io import BASE, OUTDIR, month_of
from analysis.turbulence import turbulence

# ---- settings (override on the command line) -------------------------------
ETA_SLAB = 100  # eta rows per slab; increase on HPC
SEMISUB_DEPTH = 25.0  # m
SPAR_DEPTH = 130.0  # m
# -----------------------------------------------------------------------------


def his_times(run):
    """{day ocean_time (s, mean of the records used): (path, record indices)} for all his files."""
    out = {}
    for f in sorted(glob.glob(f"{BASE}/{run}/norkyst_his_*.nc")):
        with xr.open_dataset(f, decode_times=False) as ds:
            t = ds.ocean_time.values.astype("float64")
        idx = list(range(len(t) - 8, len(t)))  # last 8 records: 03:00 to 24:00
        out[float(t[idx].mean())] = (f, idx)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("run", help="wakeref, spar or semisub")
    p.add_argument("month", help="YYYY-MM")
    p.add_argument("--semisub-depth", type=float, default=SEMISUB_DEPTH)
    p.add_argument("--spar-depth", type=float, default=SPAR_DEPTH)
    p.add_argument("--max-files", type=int, default=None,
                   help="use only the first N files of the month (testing)")
    p.add_argument("--eta-slab", type=int, default=ETA_SLAB)
    p.add_argument("--outdir", default=OUTDIR + "/turbulence")
    a = p.parse_args()

    d1, d2 = a.semisub_depth, a.spar_depth
    names = {f"0_{d1:g}": (-d1, 0.0), f"{d1:g}_{d2:g}": (-d2, -d1)}

    run_t = his_times(a.run)
    times = sorted(t for t in run_t if month_of(t) == a.month)
    if a.max_files:
        times = times[: a.max_files]
    if not times:
        raise SystemExit(f"No files for {a.run} in {a.month}")
    n = len(times)
    print(f"{a.run} {a.month}: {n} files")

    days = []
    for t in times:
        f, idx = run_t[t]
        with xr.open_dataset(f) as ds:
            days.append(turbulence(ds, names, tidxs=idx, slab=a.eta_slab).astype("float32").load())

    res = xr.concat(days, dim="ocean_time")
    res = res.assign_coords(ocean_time=("ocean_time", np.array(times, dtype="float64"),
                                        {"units": "seconds since 1970-01-01 00:00:00",
                                         "calendar": "proleptic_gregorian"}))
    res.attrs.update({
        "title": f"Daily depth-range mean turbulence, {a.run}, {a.month}",
        "n_days": n,
        "ranges": " ".join(f"{k}: {v[0]:g} to {v[1]:g} m" for k, v in names.items()),
        "source_files": " ".join(os.path.basename(run_t[t][0]) for t in times),
    })
    os.makedirs(a.outdir, exist_ok=True)
    fname = f"{a.outdir}/turbulence_{a.run}_{a.month}.nc"
    enc = {v: {"zlib": True, "complevel": 4, "dtype": "float32", "_FillValue": np.float32(np.nan)}
           for v in res.data_vars}
    res.to_netcdf(fname, encoding=enc)
    print("wrote", fname)


if __name__ == "__main__":
    main()
