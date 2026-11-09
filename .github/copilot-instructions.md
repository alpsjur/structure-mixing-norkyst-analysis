# Copilot instructions

Analysis of Norkyst ROMS output from offshore wind-farm ocean mixing experiments (runs `wakeref`, `spar`, `semisub`). No build, test, or lint tooling exists; the repo is Python scripts plus project skills.

## Setup and running
- Environment: `mamba env create -f environment.yml`, then `mamba activate structure-mixing-norkyst-analysis`. Add new packages with `mamba install` and also to `environment.yml`.
- Scripts run from the repo root, e.g. `python scripts/pea_map_test.py` or `python scripts/windfarm_map_test.py` (scripts insert `.` and `.github/skills/figure-style` into `sys.path` to import `map_example`).

## Copilot VM vs HPC
- Scripts are developed and tested on the Copilot VM (~15 GB RAM, read-only access to the data filesystem), then run for the heavy calculations on an HPC (much more memory, write access to the data filesystem).
- When running in a Copilot session, set `HDF5_USE_FILE_LOCKING=FALSE` before opening data files (the read-only Lustre filesystem otherwise gives a misleading `NetCDF: HDF error`).
- Write scripts so they work in both: keep memory-related choices (slab/chunk size, dask use, time range) and output locations as parameters or top-level settings, with defaults that fit the VM. Don't hard-code VM limits, and don't write outputs into the data directories on the VM. On the VM, write only small files (test figures, small intermediate results) into the repo: figures in `figures/`, data/netCDF outputs in `files/` (both git-ignored); the user syncs them to their local computer. Large outputs belong on the HPC.

## Architecture
- `analysis/` holds reusable computations (e.g. `analysis/pea.py`: `pea(ds, tidx, zmin, zmax)`); `scripts/` holds runnable drivers that produce figures in `figures/`. Reuse `analysis/` functions rather than rewriting them.
- Data live outside the repo at `/lustre/storeB/project/nwp/havvind/hav/structure_mixing/experiments/<run>/` (read-only). Grid files and turbine coordinates come from `~/structure-mixing-grid-utils/`.
- `files/windfarm_masks.nc` (git-ignored with all `*.nc`; regenerate with `scripts/make_windfarm_masks.py`) has per-farm masks `<farm>` and `<farm>_sectors`.
- Domain knowledge is in `.github/skills/` (`norkyst-data`, `processed-data`, `metrics`, `figure-style`). Consult them before computing or plotting; `figure-style/map_example.py` is the reference map implementation (`plot_map`, farm outline and turbine helpers).
