"""Monthly mean of a run's daily avg files (typically wakeref, to pair with the
anomaly files from make_monthly_anomalies.py, e.g. for PEA of the mean state).

Files are grouped into calendar months by ocean_time and all available
timestamps in the month are used (n_days records how many). Static
grid/vertical-transform variables are copied so depths can be computed from
the output alone.

Usage (repo root):
    python scripts/make_monthly_mean.py wakeref 2022-02 --max-files 3 --outdir files/test
"""
import argparse
import os

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")

import numpy as np
import xarray as xr

from make_monthly_anomalies import BASE, ETA_SLAB, OUTDIR, eta_dim, file_times, month_of

VARIABLES = ["temp", "salt", "u", "v", "w", "zeta", "ubar", "vbar"]
STATIC = ["mask_rho", "mask_u", "mask_v", "h", "Vtransform", "Vstretching",
          "theta_s", "theta_b", "Tcline", "hc", "Cs_r", "Cs_w"]


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("run", help="e.g. wakeref")
    p.add_argument("month", help="YYYY-MM")
    p.add_argument("--variables", nargs="+", default=VARIABLES)
    p.add_argument("--max-files", type=int, default=None,
                   help="use only the first N files of the month (testing)")
    p.add_argument("--eta-slab", type=int, default=ETA_SLAB)
    p.add_argument("--outdir", default=OUTDIR)
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

    dss = [xr.open_dataset(run_t[t], decode_times=False) for t in times]

    out = {}
    for var in a.variables:
        tmpl = dss[0][var].isel(ocean_time=0)
        ed = eta_dim(tmpl)
        neta = tmpl.sizes[ed]
        ax = tmpl.dims.index(ed)
        mean = np.empty(tmpl.shape, dtype=np.float32)
        for s in range(0, neta, a.eta_slab):
            sl = slice(s, min(s + a.eta_slab, neta))
            acc = 0.0
            for ds in dss:
                acc = acc + ds[var].isel(ocean_time=0, **{ed: sl}).values.astype(np.float64)
            idx = [slice(None)] * mean.ndim
            idx[ax] = sl
            mean[tuple(idx)] = acc / n
            print(f"  {var}: {sl.stop}/{neta}", end="\r")
        print()
        attrs = {k: v for k, v in tmpl.attrs.items() if k != "_FillValue"}
        attrs["long_name"] = f"monthly mean of " + attrs.get("long_name", var)
        out[var] = xr.DataArray(mean[None], dims=("ocean_time",) + tmpl.dims,
                                coords={k: v for k, v in tmpl.coords.items() if k != "ocean_time"},
                                attrs=attrs)

    for var in STATIC:
        if var in dss[0]:
            out[var] = dss[0][var].load()

    res = xr.Dataset(out).assign_coords(
        ocean_time=("ocean_time", [np.mean(times)], dss[0].ocean_time.attrs))
    res.attrs = {
        "title": f"Monthly mean of {a.run}, {a.month}",
        "n_days": n,
        "first_ocean_time": times[0],
        "last_ocean_time": times[-1],
        "source_files": " ".join(os.path.basename(run_t[t]) for t in times),
    }
    os.makedirs(a.outdir, exist_ok=True)
    fname = f"{a.outdir}/mean_{a.run}_{a.month}.nc"
    enc = {v: {"zlib": True, "complevel": 4, "dtype": "float32", "_FillValue": np.float32(np.nan)}
           for v in a.variables}
    res.to_netcdf(fname, encoding=enc)
    print("wrote", fname)


if __name__ == "__main__":
    main()
