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

## Precomputed products
Monthly mean-anomaly and mean files live in `.../structure_mixing/processed/`; see the `processed-data` skill and use them instead of recomputing from raw avg files when possible.

## Grid (ROMS, staggered)
- Size: eta_rho=1148, xi_rho=2747, 40 `s_rho` levels, 41 `s_w` levels.
- `u` is on (eta_u, xi_u), `v` on (eta_v, xi_v). Interpolate to rho points before computing speed.
- `tke, AKs, gls, w` are on `s_w` (interfaces); `temp, salt, u, v` on `s_rho`.
- Depths are terrain-following. Compute z from `Vtransform, Vstretching, theta_s, theta_b, Tcline, hc, Cs_r, Cs_w, h, zeta` (all in the files); never assume fixed depths.
- Use `mask_rho` to exclude land.

## Wind farm masks
- `files/windfarm_masks.nc` (repo root; git-ignored like all `*.nc`, so regenerate it rather than committing it) holds, for each farm, on `(eta_rho, xi_rho)` with `lon_rho`/`lat_rho`:
  - `<farm>`: int8 0/1 union of the farm's sectors.
  - `<farm>_sectors`: int8 sector labels 1..n (0 outside), ordered south to north by mean eta.
  Farms: `Nordavind_C` (2 sectors), `Nordavind_D` (2), `Nordvest_C` (4), `Sorvest_F` (3), `Vestavind_B` (4), `Vestavind_F` (5). Use e.g. `da.where(masks["Nordvest_C"] == 1)`.
- Regenerate with `scripts/make_windfarm_masks.py`. It reads turbine coordinates and `norkyst_grd_v31.nc` from `~/structure-mixing-grid-utils/` (`turbine_coordinates/`, `grid_files/`).
- Method: each turbine is snapped to the nearest wet rho cell. Turbine cells are grouped into sectors by single-linkage clustering (linked if closer than 5 cells). Each sector is made cohesive with binary closing (smallest size giving one region) plus hole filling, so no mask bridges the gaps between sectors.
- Exceptions: up to 2 stray turbine cells per sector that closing cannot join are dropped (3 turbines in total: 1 in Sorvest_F, 2 in Vestavind_B). The first Vestavind_F sector is a diagonal line of turbines that closing cannot connect, so its cells are joined by lines along a minimum spanning tree and widened by 1 cell. Both are recorded in the `<farm>_sectors` attributes.
- `Nordavind_CD.txt` holds two sub-areas, split at 71.45 N: north = C, south = D.

## Gotchas
- When running in Copilot sessions,  set `HDF5_USE_FILE_LOCKING=FALSE` before opening files. The read-only filesystem otherwise gives a misleading `NetCDF: HDF error`. This does not apply when running on HPC.
- Files are huge: open lazily (`xr.open_dataset` / `xr.open_mfdataset` with chunks), select variables and subregions early, never `.load()` full 3D fields. In Copilot sessions (about 15 GB RAM) this is a hard limit; on HPC it is a performance concern only.
- Use `decode_times=False` and decode `ocean_time` manually if decoding is slow.

## Environment
Use the `structure-mixing-norkyst-analysis` mamba environment (`mamba env create -f environment.yml` in the repo root; activate with `mamba activate structure-mixing-norkyst-analysis`). Install additional packages with `mamba install`, and add them to `environment.yml`.
