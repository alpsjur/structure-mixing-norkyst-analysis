"""Daily wind-farm mean PEA anomaly: farm-only vs farm+downstream-extension averaging.

Compares the noise level of the `run - wakeref` PEA anomaly when averaged over the farm mask
alone vs. the farm + downstream extension (`<farm>_extended`, see
scripts/computations/make_windfarm_downstream_masks.py and docs/notes.md). One figure per run
and PEA range (6 farm rows sharing the time axis) -> figures/<range>_timeseries/.
Daily mean = mean of the daily PEA over the mask cells (NaN cells skipped).

Usage: python scripts/plotting/pea_downstream_comparison_timeseries.py [pea pea50 pea100 pea150 ...]
(default: all)
"""
import os
import sys

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
sys.path.insert(0, ".github/skills/figure-style")
sys.path.insert(0, ".")

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from analysis.io import MASKS, OUTDIR
from map_example import save_fig

RUNS = ["spar", "semisub"]
LABELS = {"pea": "whole column", "pea50": "0-50 m", "pea100": "0-100 m", "pea150": "0-150 m"}
DOWNSTREAM_MASKS = Path("files/windfarm_downstream_masks.nc")  # VM test copy; Lustre masks/ once finalised

masks = xr.open_dataset(MASKS)
ext = xr.open_dataset(DOWNSTREAM_MASKS)
FARMS = [v for v in masks.data_vars if not v.endswith("_sectors")]


def mask_slices(mask):
    eta, xi = np.nonzero(mask)
    return slice(eta.min(), eta.max() + 1), slice(xi.min(), xi.max() + 1)


FARM_SEL = {}
EXT_SEL = {}
for farm in FARMS:
    m = masks[farm].values > 0
    FARM_SEL[farm] = mask_slices(m) + (m,)
    me = ext[f"{farm}_extended"].values > 0
    EXT_SEL[farm] = mask_slices(me) + (me,)


def means(pea_dir, run, month, sel):
    """farm -> DataArray of daily mean PEA over the mask cells, for the given selection dict."""
    ds = xr.open_dataset(pea_dir / f"pea_{run}_{month}.nc")
    out = {}
    for farm, (es, xs, m) in sel.items():
        w = xr.DataArray(m[es, xs], dims=("eta_rho", "xi_rho"))
        sub = ds.pea.isel(eta_rho=es, xi_rho=xs)
        out[farm] = sub.where(w).mean(("eta_rho", "xi_rho")).load()
    return out


def series(pea_dir, run, months, sel):
    parts = [means(pea_dir, run, month, sel) for month in months]
    return {farm: xr.concat([p[farm] for p in parts], "ocean_time") for farm in FARMS}


for rng in sys.argv[1:] or list(LABELS):
    pea_dir = Path(OUTDIR) / rng
    months = sorted(f.stem.split("_")[-1] for f in pea_dir.glob("pea_wakeref_????-??.nc"))
    wake_farm = series(pea_dir, "wakeref", months, FARM_SEL)
    wake_ext = series(pea_dir, "wakeref", months, EXT_SEL)
    for run in RUNS:
        exp_farm = series(pea_dir, run, months, FARM_SEL)
        exp_ext = series(pea_dir, run, months, EXT_SEL)
        fig, axes = plt.subplots(len(FARMS), 1, figsize=(12, 2.4 * len(FARMS)), sharex=True, layout="constrained")
        for ax, farm in zip(axes, FARMS):
            ef, wf = xr.align(exp_farm[farm], wake_farm[farm], join="inner")
            ee, we = xr.align(exp_ext[farm], wake_ext[farm], join="inner")
            ax.plot(wf.ocean_time, ef - wf, color="tab:gray", label="farm only")
            ax.plot(we.ocean_time, ee - we, color="tab:red", label="farm + downstream")
            ax.axhline(0, color="black", linewidth=0.5)
            ax.set_ylabel(farm.replace("_", " ") + "\n(J m$^{-3}$)")
            ax.grid(alpha=0.3)
        axes[0].legend(loc="upper right", ncol=2)
        axes[0].set_title(f"Daily mean PEA anomaly ({run} - wakeref, {rng}: {LABELS[rng]}): "
                           f"farm vs. farm+downstream averaging")
        axes[-1].xaxis.set_major_formatter(mdates.ConciseDateFormatter(mdates.AutoDateLocator()))
        save_fig(fig, f"pea_{run}_downstream_comparison", f"{rng}_timeseries")
        plt.close(fig)
        print(rng, run, "done", flush=True)
