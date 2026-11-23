"""Daily wind-farm mean current speed anomaly: farm-only vs farm+downstream-extension averaging.

Compares the noise level of the `run - wakeref` current speed anomaly when averaged over the
farm mask alone vs. the farm + downstream extension (`<farm>_extended`, see
scripts/computations/make_windfarm_downstream_masks.py and docs/notes.md). One figure per run
(6 farm rows sharing the time axis) -> figures/current_timeseries/.
Depth range matches the structure: semisub 0-25 m, spar 0-130 m (stored 0_25 and 25_130
combined, weighted by H).

Usage: python scripts/plotting/current_downstream_comparison_timeseries.py [semisub|spar ...]
(default: both)
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

CURRENT_DIR = Path(OUTDIR) / "current"
DOWNSTREAM_MASKS = Path("files/windfarm_downstream_masks.nc")  # VM test copy; Lustre masks/ once finalised
SETS = {"semisub": (["0_25"], "0-25 m"), "spar": (["0_25", "25_130"], "0-130 m")}

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


def means(run, month, ranges, sel):
    """farm -> DataArray of daily mean speed over the mask cells, for the given selection dict."""
    ds = xr.open_dataset(CURRENT_DIR / f"current_{run}_{month}.nc")
    out = {}
    for farm, (es, xs, m) in sel.items():
        sub = ds.isel(eta_rho=es, xi_rho=xs)
        w = xr.DataArray(m[es, xs], dims=("eta_rho", "xi_rho"))
        if len(ranges) == 1:
            speed = sub[f"speed_{ranges[0]}"]
        else:
            H = sum(sub[f"H_{r}"] for r in ranges)
            speed = sum(sub[f"speed_{r}"].fillna(0) * sub[f"H_{r}"] for r in ranges) / H.where(H > 0)
        out[farm] = speed.where(w).mean(("eta_rho", "xi_rho")).load()
    return out


def series(run, ranges, months, sel):
    parts = [means(run, month, ranges, sel) for month in months]
    return {farm: xr.concat([p[farm] for p in parts], "ocean_time") for farm in FARMS}


months = sorted(f.stem.split("_")[-1] for f in CURRENT_DIR.glob("current_wakeref_????-??.nc"))
for run in sys.argv[1:] or list(SETS):
    ranges, label = SETS[run]
    exp_farm, wake_farm = series(run, ranges, months, FARM_SEL), series("wakeref", ranges, months, FARM_SEL)
    exp_ext, wake_ext = series(run, ranges, months, EXT_SEL), series("wakeref", ranges, months, EXT_SEL)
    fig, axes = plt.subplots(len(FARMS), 1, figsize=(12, 2.4 * len(FARMS)), sharex=True, layout="constrained")
    for ax, farm in zip(axes, FARMS):
        ef, wf = xr.align(exp_farm[farm], wake_farm[farm], join="inner")
        ee, we = xr.align(exp_ext[farm], wake_ext[farm], join="inner")
        ax.plot(wf.ocean_time, ef - wf, color="tab:gray", label="farm only")
        ax.plot(we.ocean_time, ee - we, color="tab:red", label="farm + downstream")
        ax.axhline(0, color="black", linewidth=0.5)
        ax.set_ylabel(farm.replace("_", " ") + "\n(m s$^{-1}$)")
        ax.grid(alpha=0.3)
    axes[0].legend(loc="upper right", ncol=2)
    axes[0].set_title(f"Daily mean current speed anomaly ({run} - wakeref, {label}): "
                       f"farm vs. farm+downstream averaging")
    axes[-1].xaxis.set_major_formatter(mdates.ConciseDateFormatter(mdates.AutoDateLocator()))
    save_fig(fig, f"current_{run}_downstream_comparison", "current_timeseries")
    plt.close(fig)
    print(run, "done", flush=True)
