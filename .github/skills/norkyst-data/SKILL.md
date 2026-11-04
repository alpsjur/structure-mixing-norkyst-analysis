---
name: norkyst-data
description: Open, subset and interpret Norkyst ROMS output from the offshore wind farm mixing experiments (runs wakeref, spar, semisub). Use when reading avg/his netCDF files, choosing variables, handling ROMS grids/time, or setting up xarray/dask for these files.
---

# Norkyst wind-farm mixing output

## Runs
Base path: `/lustre/storeB/project/nwp/havvind/hav/structure_mixing/experiments/<run>/`
(read-only for Copilot; analysis scripts later run on HPC).

| Run | Meaning |
|---|---|
| `wakeref` | Reference: atmospheric wake effect in the surface forcing, but no wind-farm mixing parametrization in the ocean. Baseline for anomalies |
| `spar` | Atmospheric wake forcing plus the ocean mixing parametrization for spar structures |
| `semisub` | Atmospheric wake forcing plus the ocean mixing parametrization for semisubmersible structures |

All three runs include the atmospheric wake. Differences from `wakeref` therefore isolate the ocean mixing parametrization only, not the wake.

Runs have different numbers of files (some may still be running). Check with
`ls` and use the common time range before comparing runs.

## Files
- `norkyst_avg_NNNN.nc`: 1 time record per file, ~3.6 GB. Vars: `u, v, w, omega, temp, salt, zeta, ubar, vbar`. No turbulence fields.
- `norkyst_his_NNNN.nc`: 9 records per file (3-hourly), ~35-39 GB. Adds `AKs, tke, gls, Uwind, Vwind`. Use for TKE/mixing.
- Match records by `ocean_time` (seconds since 1970, proleptic_gregorian), not by file number.

## Grid (ROMS, staggered)
- Size: eta_rho=1148, xi_rho=2747, 40 `s_rho` levels, 41 `s_w` levels.
- `u` is on (eta_u, xi_u), `v` on (eta_v, xi_v). Interpolate to rho points before computing speed.
- `tke, AKs, gls, w` are on `s_w` (interfaces); `temp, salt, u, v` on `s_rho`.
- Depths are terrain-following. Compute z from `Vtransform, Vstretching, theta_s, theta_b, Tcline, hc, Cs_r, Cs_w, h, zeta` (all in the files); never assume fixed depths.
- Use `mask_rho` to exclude land.

## Gotchas
- **Always set `HDF5_USE_FILE_LOCKING=FALSE`** before opening files. The read-only filesystem otherwise gives a misleading `NetCDF: HDF error`.
- Files are huge: open lazily (`xr.open_dataset` / `xr.open_mfdataset` with chunks), select variables and subregions early, never `.load()` full 3D fields. In Copilot sessions (about 15 GB RAM) this is a hard limit; on HPC it is a performance concern only.
- Use `decode_times=False` and decode `ocean_time` manually if decoding is slow.

## Environment
Use the `structure-mixing-norkyst-analysis` mamba environment (`mamba env create -f environment.yml` in the repo root; activate with `mamba activate structure-mixing-norkyst-analysis`). Install additional packages with `mamba install`, and add them to `environment.yml`.
