---
name: processed-data
description: Precomputed monthly mean-anomaly files (anom_<run>_<YYYY-MM>.nc), monthly mean files (mean_<run>_<YYYY-MM>.nc), and daily resolution PEA files, grouped in months (pea_<run>_<YYYY-MM>.nc). Use these instead of recomputing from raw avg files when possible.
---

# Precomputed monthly files

Location: `/lustre/storeB/project/nwp/havvind/hav/structure_mixing/processed/` (sibling of `experiments/`). Open as described in `norkyst-data` (`HDF5_USE_FILE_LOCKING=FALSE`).

## Anomaly files: `anom_<run>_<YYYY-MM>.nc`
- Live in subfolder `anom/` within the processed data directory.
- Made by `scripts/make_monthly_anomalies.py`: mean over the month of the daily `run - wakeref` (avg files paired by `ocean_time`, grouped by calendar month; Feb starts 2 Feb, so 27 files). ~1.3 GB each.
- Vars `temp, salt, u, v, w, zeta, ubar, vbar`; one record (`ocean_time` = mean of used stamps); float32, NaN on land, zlib. Same staggered grid and `lon/lat_*` coords as avg files.
- Attributes: `n_days`, `first_ocean_time`, `last_ocean_time`, `source_files`, `reference_files`.
- No grid/vertical-transform variables and no `his`-only fields (`tke`, `AKs`, `gls`).

## Mean files: `mean_<run>_<YYYY-MM>.nc`
- Live in subfolder `mean/` within the processed data directory.
- Made by `scripts/make_monthly_mean.py` (typically `wakeref`): mean of all avg files in the calendar month (all available timestamps, not matched to other runs).
- Same variables and attributes as anomaly files, plus static grid variables (`mask_rho/u/v`, `h`, `Vtransform`, `Vstretching`, `theta_s`, `theta_b`, `Tcline`, `hc`, `Cs_r`, `Cs_w`), so depths can be computed from this file.

-## Daily PEA files: `pea_<run>_<YYYY-MM>.nc`
- Live in subfolder `pea/` within the processed data directory.
- Made by `scripts/make_monthly_pea.py` using `analysis/pea.py`, one file per run and month.
- Var `pea` (J m-3), dims `(ocean_time, eta_rho, xi_rho)`, one record per day. Attributes: `n_days`, `zmin`, `zmax` (default whole column), `source_files`. The `ocean_time` coordinate covers the days in the month.
- The anomaly can be computed afterwards: `pea_run.pea - pea_wakeref.pea`, aligned on `ocean_time`. Then average over time, weighting by number of days. 



## Daily depth-range mean current files: `current_<run>_<YYYY-MM>.nc`
- Live in subfolder `current/` within the processed data directory.
- Made by `scripts/make_monthly_current.py` using `analysis/current.py`, one file per run (incl. wakeref) and month.
- Two depth ranges below the surface: `0_25` (semisub extent) and `25_130` (down to spar extent). Per range: `ubar_<r>`, `vbar_<r>` (mean u, v at rho points, not rotated), `speed_<r>` (mean of sqrt(u2+v2)), `H_<r>` (water thickness inside the range, m; 0 where shallower, then means are NaN). Dims `(ocean_time, eta_rho, xi_rho)`, one record per day. Attributes: `n_days`, `ranges`, `source_files`.
- Mean over 0-130 m: `(m1*H1 + m2*H2) / (H1 + H2)`. Anomalies of `speed` (nonlinear): difference per day vs wakeref, then average.
