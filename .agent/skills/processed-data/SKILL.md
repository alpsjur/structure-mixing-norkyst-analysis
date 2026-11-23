---
name: processed-data
description: Precomputed quantities. Use these instead of recomputing from raw avg files when possible.
---

# Precomputed files

Location: `/lustre/storeB/project/nwp/havvind/structure_mixing/processed/` (sibling of `experiments/`). Open as described in `norkyst-data`.

## Monthly anomaly files: `anom_<run>_<YYYY-MM>.nc`
- Live in subfolder `anom/` within the processed data directory.
- Made by `scripts/computations/make_monthly_anomalies.py`: mean over the month of the daily `run - wakeref` (avg files paired by `ocean_time`, grouped by calendar month; Feb starts 2 Feb, so 27 files). ~1.3 GB each.
- Vars `temp, salt, u, v, w, zeta, ubar, vbar`; one record (`ocean_time` = mean of used stamps); float32, NaN on land, zlib. Same staggered grid and `lon/lat_*` coords as avg files.
- Attributes: `n_days`, `first_ocean_time`, `last_ocean_time`, `source_files`, `reference_files`.
- No grid/vertical-transform variables and no `his`-only fields (`tke`, `AKs`, `gls`).

## Monthly mean files: `mean_<run>_<YYYY-MM>.nc`
- Live in subfolder `mean/` within the processed data directory.
- Made by `scripts/computations/make_monthly_mean.py` (typically `wakeref`): mean of all avg files in the calendar month (all available timestamps, not matched to other runs).
- Same variables and attributes as anomaly files, plus static grid variables (`mask_rho/u/v`, `h`, `Vtransform`, `Vstretching`, `theta_s`, `theta_b`, `Tcline`, `hc`, `Cs_r`, `Cs_w`), so depths can be computed from this file.

## PEA files: `pea_<run>_<YYYY-MM>.nc`
- Whole column: subfolder `pea/` within the processed data directory. Upper-ocean PEA (integrated from the surface down to 50, 100 or 150 m; where shallower, the whole column): subfolders `pea50/`, `pea100/`, `pea150/`, same file names (`zmin` = -50/-100/-150, `zmax` = surface).
- Made by `scripts/computations/make_pea.py` using `analysis/pea.py`, one file per run and month.
- Var `pea` (J m-3), dims `(ocean_time, eta_rho, xi_rho)`, one record per day. Attributes: `n_days`, `zmin`, `zmax` (default whole column), `ref` (`ts` default; files made earlier or with `--ref rho` use mean-density reference, the latter named `pea_<run>_<YYYY-MM>_rhoref.nc`), `source_files`. The `ocean_time` coordinate covers the days in the month.
- The anomaly can be computed afterwards: `pea_run.pea - pea_wakeref.pea`, aligned on `ocean_time`. Then average over time, weighting by number of days. 


## Daily depth-range mean current files: `current_<run>_<YYYY-MM>.nc`
- Live in subfolder `current/` within the processed data directory.
- Made by `scripts/computations/make_current.py` using `analysis/current.py`, one file per run (incl. wakeref) and month.
- Two depth ranges below the surface: `0_25` (semisub extent) and `25_130` (down to spar extent). Per range: `ubar_<r>`, `vbar_<r>` (mean u, v at rho points, not rotated), `speed_<r>` (mean of sqrt(u2+v2)), `H_<r>` (water thickness inside the range, m; 0 where shallower, then means are NaN). Dims `(ocean_time, eta_rho, xi_rho)`, one record per day. Attributes: `n_days`, `ranges`, `source_files`. Available for all runs for 2022-02 to 2022-08 (Feb starts 2 Feb), like the PEA files. To get the spar range (0-130 m) combine the two ranges weighted by `H` (see `metrics`).


## Daily depth-range mean turbulence files: `turbulence_<run>_<YYYY-MM>.nc`
- Subfolder `turbulence/` within the processed data directory (not yet generated on the HPC; only a test file exists in `files/test/`).
- Made by `scripts/computations/make_turbulence.py` using `analysis/turbulence.py`, one file per run (incl. wakeref) and month, from the 3-hourly `his` files.
- Same depth ranges as the current files (`0_25`, `25_130`). Per range: `tke_<r>` (m2 s-2), `gls_<r>` (mean psi), `eps_<r>` (mean of `gls**1.5` per record, i.e. dissipation, m2 s-3), `H_<r>` (m). Daily value = mean of the 8 records 03:00-24:00 (the 00:00 record of file 0001 is skipped), each depth-averaged first. `ocean_time` is the mean of those records (about 13:30, not 12:00), so pair runs by day, not by exact stamp with avg files.
- Combine ranges with `H` weights as for the current files. Monthly means and anomalies can be made by averaging/differencing the daily fields (linear).
