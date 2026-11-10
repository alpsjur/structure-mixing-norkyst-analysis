"""Daily PEA of one run for one month, from the daily avg files.

Anomalies relative to wakeref, monthly/seasonal means and noise estimates are then
simple operations on these small files, e.g.
    dpea = pea_spar.pea - pea_wakeref.pea   (align on ocean_time)

Output: <outdir>/pea_<run>_<YYYY-MM>.nc with dims (ocean_time, eta_rho, xi_rho),
variable pea in J m-3. Works for any run, including wakeref.

Usage (repo root):
    python scripts/make_monthly_pea.py wakeref 2022-02 --max-files 2 --outdir files/test
"""
import argparse
import os
import sys

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
sys.path.insert(0, ".")
sys.path.insert(0, "scripts")

import numpy as np
import xarray as xr

from analysis.pea import pea
from scripts.computations.make_monthly_anomalies import OUTDIR, file_times, month_of

# ---- settings (override on the command line) -------------------------------
ETA_SLAB = 400  # eta rows per PEA slab; increase on HPC
# -----------------------------------------------------------------------------


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("run", help="wakeref, spar or semisub")
    p.add_argument("month", help="YYYY-MM")
    p.add_argument("--zmin", type=float, default=None, help="lower integration limit (m, negative down)")
    p.add_argument("--zmax", type=float, default=None, help="upper integration limit (m, relative to surface)")
    p.add_argument("--max-files", type=int, default=None,
                   help="use only the first N files of the month (testing)")
    p.add_argument("--eta-slab", type=int, default=ETA_SLAB)
    p.add_argument("--outdir", default=OUTDIR+"/pea")
    a = p.parse_args()

    run_t = file_times(a.run)
    times = sorted(t for t in run_t if month_of(t) == a.month)
    if a.max_files:
        times = times[: a.max_files]
    if not times:
        raise SystemExit(f"No files for {a.run} in {a.month}")
    n = len(times)
    print(f"{a.run} {a.month}: {n} files, "
          f"{np.datetime64(int(times[0]), 's')} to {np.datetime64(int(times[-1]), 's')}")

    fields = []
    for i, t in enumerate(times):
        with xr.open_dataset(run_t[t]) as ds:
            fields.append(pea(ds, zmin=a.zmin, zmax=a.zmax, slab=a.eta_slab).values.astype("float32"))
            lon, lat = ds.lon_rho.load(), ds.lat_rho.load()
        print(f"  {i + 1}/{n} done", end="\r")
    print()

    res = xr.Dataset(
        {"pea": (("ocean_time", "eta_rho", "xi_rho"), np.stack(fields),
                 {"units": "J m-3", "long_name": f"potential energy anomaly, {a.run}"})},
        coords={"lon_rho": lon, "lat_rho": lat,
                "ocean_time": ("ocean_time", np.array(times, dtype="float64"),
                               {"units": "seconds since 1970-01-01 00:00:00", "calendar": "proleptic_gregorian"})},
        attrs={
            "title": f"Daily PEA, {a.run}, {a.month}",
            "n_days": n,
            "zmin": "bottom" if a.zmin is None else a.zmin,
            "zmax": "surface" if a.zmax is None else a.zmax,
            "source_files": " ".join(os.path.basename(run_t[t]) for t in times),
        },
    )
    os.makedirs(a.outdir, exist_ok=True)
    fname = f"{a.outdir}/pea_{a.run}_{a.month}.nc"
    enc = {"pea": {"zlib": True, "complevel": 4, "dtype": "float32", "_FillValue": np.float32(np.nan)}}
    res.to_netcdf(fname, encoding=enc)
    print("wrote", fname)


if __name__ == "__main__":
    main()
