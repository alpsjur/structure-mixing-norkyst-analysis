"""Farm temperature-salinity data on fixed depths from monthly mean_wakeref + anom_<run> files.

One small netCDF per farm, run and month: ts_<farm>_<run>_<YYYY-MM>.nc with, per farm cell and fixed depth,
the wakeref (`*_ref`) and run (`*_run` = mean_wakeref + anomaly) potential temperature and practical salinity,
and the anomaly (`dtemp`, `dsalt`, run - wakeref). See analysis/ts.py.

Usage (repo root; on the Copilot VM):
    python scripts/computations/make_ts_farm.py --runs spar --months 2022-05 --farms Nordvest_C --outdir files/ts
"""
import argparse
import os
import sys

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
sys.path.insert(0, ".")

from pathlib import Path

import xarray as xr

from analysis.io import MASKS, OUTDIR
from analysis.ts import farm_bbox, farm_ts, to_dataset, zgrid

MONTHS = [f"2022-{m:02d}" for m in range(2, 9)]


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--runs", nargs="+", default=["spar", "semisub"])
    p.add_argument("--months", nargs="+", default=MONTHS)
    p.add_argument("--farms", nargs="+", default=None, help="default: all farms")
    p.add_argument("--zmax", type=float, default=150.0, help="depth range (m)")
    p.add_argument("--dz", type=float, default=5.0, help="fixed-depth spacing (m)")
    p.add_argument("--processed", default=OUTDIR, help="directory with mean/ and anom/")
    p.add_argument("--masks", default=MASKS)
    p.add_argument("--outdir", default=OUTDIR + "/ts")
    a = p.parse_args()

    masks = xr.open_dataset(a.masks)
    farms = a.farms or [v for v in masks.data_vars if not v.endswith("_sectors")]
    zfix = zgrid(a.zmax, a.dz)
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)

    for month in a.months:
        mean_ds = xr.open_dataset(f"{a.processed}/mean/mean_wakeref_{month}.nc")
        for run in a.runs:
            anom_ds = xr.open_dataset(f"{a.processed}/anom/anom_{run}_{month}.nc")
            for farm in farms:
                m = masks[farm].values > 0
                es, xs = farm_bbox(m)
                msub = m[es, xs]
                fields = farm_ts(mean_ds, anom_ds, es, xs, msub, zfix)
                lon = mean_ds.lon_rho.isel(eta_rho=es, xi_rho=xs).values[msub]
                lat = mean_ds.lat_rho.isel(eta_rho=es, xi_rho=xs).values[msub]
                attrs = {"farm": farm, "run": run, "month": month, "n_days_anom": anom_ds.attrs["n_days"],
                         "n_days_mean": mean_ds.attrs["n_days"],
                         "note": "run = mean_wakeref + anom; d* = anomaly on wakeref depths"}
                to_dataset(fields, zfix, lon, lat, attrs).to_netcdf(out / f"ts_{farm}_{run}_{month}.nc")
                print(run, month, farm, flush=True)


if __name__ == "__main__":
    main()
