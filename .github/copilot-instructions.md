# Copilot instructions

Analysis of Norkyst ROMS output from offshore wind-farm ocean mixing experiments (runs `wakeref`, `spar`, `semisub`). No build, test, or lint tooling exists; the repo is Python scripts plus project skills.

## Setup and running
- Environment: `mamba env create -f environment.yml`, then `mamba activate structure-mixing-norkyst-analysis`. Add new packages with `mamba install` and also to `environment.yml`.
- Scripts run from the repo root, e.g. `python scripts/plotting/plot_bathymetry.py` (scripts insert `.` and `.github/skills/figure-style` into `sys.path`). Computation scripts are in `scripts/computations/`, plots in `scripts/plotting/`.

## Copilot VM vs HPC
- Scripts are developed and tested on the Copilot VM (~15 GB RAM, read-only access to the data filesystem), then run for the heavy calculations on an HPC (much more memory, write access to the data filesystem).
- When running in a Copilot session, set `HDF5_USE_FILE_LOCKING=FALSE` before opening data files (the read-only Lustre filesystem otherwise gives a misleading `NetCDF: HDF error`).
- Write scripts so they work in both: keep memory-related choices (slab/chunk size, dask use, time range) and output locations as parameters or top-level settings. Don't hard-code VM limits. Computation scripts default `--outdir` to the Lustre `processed/` directory (for HPC); on the VM always pass `--outdir files/...` (and `--max-files`), never write into the data directories. On the VM, write only small files (test figures, small intermediate results) into the repo: figures in `figures/`, data/netCDF outputs in `files/` (both git-ignored); the user syncs them to their local computer. Large outputs belong on the HPC.

## Architecture
- `analysis/` holds reusable computations (e.g. `analysis/pea.py`: `pea(ds, tidx, zmin, zmax)`); `scripts/` holds runnable drivers (figures go in `figures/<topic>/`, see `figure-style`). Reuse `analysis/` functions rather than rewriting them.
- Data live outside the repo at `/lustre/storeB/project/nwp/havvind/hav/structure_mixing/experiments/<run>/` (read-only). Grid files and turbine coordinates come from `~/structure-mixing-grid-utils/`.
- Wind-farm masks (`<farm>`, `<farm>_sectors`): canonical copy `.../structure_mixing/masks/windfarm_masks.nc`; `files/windfarm_masks.nc` is a local test copy (git-ignored, regenerate with `scripts/computations/make_windfarm_masks.py`). `map_example.MASKS` defaults to the local copy; plotting scripts set it to the Lustre one.
- Domain knowledge is in `.github/skills/` (`norkyst-data`, `processed-data`, `metrics`, `figure-style`). Consult them before computing or plotting; `figure-style/map_example.py` is the reference map implementation (`plot_map`, farm outline and turbine helpers).
