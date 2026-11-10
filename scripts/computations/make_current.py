"""Daily depth-range mean current of one run for one month, from the daily avg files.

Two depth ranges by default: 0-25 m (semisub extent) and 25-130 m (down to spar extent).
Per range: ubar, vbar (mean u, v at rho points, not rotated), speed (mean of sqrt(u2+v2)),
H (water thickness inside the range, m). Combine ranges with thickness weights:
    (m1*H1 + m2*H2) / (H1 + H2)

Output: <outdir>/current_<run>_<YYYY-MM>.nc with dims (ocean_time, eta_rho, xi_rho).
Works for any run, including wakeref.

Usage (repo root):
    python scripts/computations/make_current.py wakeref 2022-02 --max-files 2 --outdir files/test
"""
import argparse
import os
import sys

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
sys.path.insert(0, ".")
sys.path.insert(0, "scripts")

import numpy as np
import xarray as xr

from analysis.current import current
from scripts.computations.make_monthly_anomalies import OUTDIR, file_times, month_of

# ---- settings (override on the command line) -------------------------------
ETA_SLAB = 400  # eta rows per slab; increase on HPC
SEMISUB_DEPTH = 25.0  # m
SPAR_DEPTH = 130.0  # m
# -----------------------------------------------------------------------------


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("run", help="wakeref, spar or semisub")
    p.add_argument("month", help="YYYY-MM")
    p.add_argument("--semisub-depth", type=float, default=SEMISUB_DEPTH)
    p.add_argument("--spar-depth", type=float, default=SPAR_DEPTH)
    p.add_argument("--max-files", type=int, default=None,
                   help="use only the first N files of the month (testing)")
    p.add_argument("--eta-slab", type=int, default=ETA_SLAB)
    p.add_argument("--outdir", default=OUTDIR + "/current")
    a = p.parse_args()

    d1, d2 = a.semisub_depth, a.spar_depth
    names = {f"0_{d1:g}": (-d1, 0.0), f"{d1:g}_{d2:g}": (-d2, -d1)}

    run_t = file_times(a.run)
    times = sorted(t for t in run_t if month_of(t) == a.month)
    if a.max_files:
        times = times[: a.max_files]
    if not times:
        raise SystemExit(f"No files for {a.run} in {a.month}")
    n = len(times)
    print(f"{a.run} {a.month}: {n} files, "
          f"{np.datetime64(int(times[0]), 's')} to {np.datetime64(int(times[-1]), 's')}")

    days = []
    for i, t in enumerate(times):
        with xr.open_dataset(run_t[t]) as ds:
            days.append(current(ds, names, slab=a.eta_slab).astype("float32").load())
        print(f"  {i + 1}/{n} done", end="\r")
    print()

    res = xr.concat(days, dim="ocean_time")
    res = res.assign_coords(ocean_time=("ocean_time", np.array(times, dtype="float64"),
                                        {"units": "seconds since 1970-01-01 00:00:00",
                                         "calendar": "proleptic_gregorian"}))
    res.attrs.update({
        "title": f"Daily depth-range mean current, {a.run}, {a.month}",
        "n_days": n,
        "ranges": " ".join(f"{k}: {v[0]:g} to {v[1]:g} m" for k, v in names.items()),
        "source_files": " ".join(os.path.basename(run_t[t]) for t in times),
    })
    os.makedirs(a.outdir, exist_ok=True)
    fname = f"{a.outdir}/current_{a.run}_{a.month}.nc"
    enc = {v: {"zlib": True, "complevel": 4, "dtype": "float32", "_FillValue": np.float32(np.nan)}
           for v in res.data_vars}
    res.to_netcdf(fname, encoding=enc)
    print("wrote", fname)


if __name__ == "__main__":
    main()
