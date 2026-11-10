"""Monthly mean anomalies (run - wakeref) from the daily avg files.

Files are grouped into calendar months by ocean_time (not file number), and
matched with wakeref on identical ocean_time. Mean of daily anomalies is
accumulated slab by slab, so memory stays bounded. Partial months (simulation
still running) are processed from the files available; n_days records how many
were used.

Usage (repo root):
    python scripts/make_monthly_anomalies.py spar 2022-02 --max-files 3 --outdir files/test
"""
import argparse
import glob
import os
import re

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")

import numpy as np
import xarray as xr

# ---- settings (override on the command line) -------------------------------
BASE = "/lustre/storeB/project/nwp/havvind/hav/structure_mixing/experiments"
OUTDIR = "/lustre/storeB/project/nwp/havvind/hav/structure_mixing/processed"  
VARIABLES = ["temp", "salt", "u", "v", "w", "zeta", "ubar", "vbar"]
ETA_SLAB = 400  # eta rows read at once; increase on HPC
# -----------------------------------------------------------------------------


def file_times(run):
    """Return {ocean_time (s): path} for all avg files of a run."""
    out = {}
    for f in sorted(glob.glob(f"{BASE}/{run}/norkyst_avg_*.nc")):
        with xr.open_dataset(f, decode_times=False, drop_variables=None) as ds:
            out[float(ds.ocean_time.values[0])] = f
    return out


def month_of(t):
    return str(np.datetime64(int(t), "s").astype("datetime64[M]"))


def eta_dim(da):
    return next(d for d in da.dims if d.startswith("eta_"))


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("run", help="spar or semisub")
    p.add_argument("month", help="YYYY-MM")
    p.add_argument("--ref", default="wakeref")
    p.add_argument("--variables", nargs="+", default=VARIABLES)
    p.add_argument("--max-files", type=int, default=None,
                   help="use only the first N files of the month (testing)")
    p.add_argument("--eta-slab", type=int, default=ETA_SLAB)
    p.add_argument("--outdir", default=OUTDIR+"/anom")
    a = p.parse_args()

    run_t, ref_t = file_times(a.run), file_times(a.ref)
    times = sorted(t for t in run_t if t in ref_t and month_of(t) == a.month)
    if a.max_files:
        times = times[: a.max_files]
    if not times:
        raise SystemExit(f"No common {a.run}/{a.ref} files in {a.month}")
    n = len(times)
    print(f"{a.run} {a.month}: {n} common files, "
          f"{np.datetime64(int(times[0]), 's')} to {np.datetime64(int(times[-1]), 's')}")

    run_ds = [xr.open_dataset(run_t[t], decode_times=False) for t in times]
    ref_ds = [xr.open_dataset(ref_t[t], decode_times=False) for t in times]

    out = {}
    for var in a.variables:
        tmpl = run_ds[0][var].isel(ocean_time=0)
        ed = eta_dim(tmpl)
        neta = tmpl.sizes[ed]
        mean = np.empty(tmpl.shape, dtype=np.float32)
        ax = tmpl.dims.index(ed)
        for s in range(0, neta, a.eta_slab):
            sl = slice(s, min(s + a.eta_slab, neta))
            acc = 0.0
            for r, w in zip(run_ds, ref_ds):
                acc = acc + (r[var].isel(ocean_time=0, **{ed: sl}).values.astype(np.float64)
                             - w[var].isel(ocean_time=0, **{ed: sl}).values)
            idx = [slice(None)] * mean.ndim
            idx[ax] = sl
            mean[tuple(idx)] = acc / n
            print(f"  {var}: {sl.stop}/{neta}", end="\r")
        print()
        attrs = {k: v for k, v in tmpl.attrs.items() if k != "_FillValue"}
        attrs["long_name"] = f"monthly mean anomaly ({a.run} - {a.ref}) of " + attrs.get("long_name", var)
        out[var] = xr.DataArray(mean[None], dims=("ocean_time",) + tmpl.dims,
                                coords={k: v for k, v in tmpl.coords.items() if k != "ocean_time"},
                                attrs=attrs)

    tmid = np.mean(times)
    res = xr.Dataset(out).assign_coords(ocean_time=("ocean_time", [tmid], run_ds[0].ocean_time.attrs))
    res.attrs = {
        "title": f"Monthly mean anomalies {a.run} - {a.ref}, {a.month}",
        "n_days": n,
        "first_ocean_time": times[0],
        "last_ocean_time": times[-1],
        "source_files": " ".join(os.path.basename(run_t[t]) for t in times),
        "reference_files": " ".join(os.path.basename(ref_t[t]) for t in times),
    }
    os.makedirs(a.outdir, exist_ok=True)
    fname = f"{a.outdir}/anom_{a.run}_{a.month}.nc"
    enc = {v: {"zlib": True, "complevel": 4, "dtype": "float32", "_FillValue": np.float32(np.nan)}
           for v in res.data_vars}
    res.to_netcdf(fname, encoding=enc)
    print("wrote", fname)


if __name__ == "__main__":
    main()
