"""Animate daily PEA: experiment | wakeref (log, shared colorbar) | experiment - wakeref -> MP4.

Run from the repo root, e.g.
    python scripts/plotting/pea_daily_animation.py --runs spar semisub
On the VM use --max-days and --pea-dir to a small test set; full runs belong on the HPC.
All months where the run and wakeref PEA files both exist are used.
"""
import argparse
import os
import sys

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
sys.path.insert(0, ".github/skills/figure-style")
sys.path.insert(0, ".")

from pathlib import Path

import cartopy.crs as ccrs
import cmocean.cm as cmo
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.animation import FFMpegWriter
from matplotlib.colors import LogNorm

import map_example
from analysis.io import MASKS, OUTDIR
from map_example import add_farm_outlines, draw_map

map_example.MASKS = MASKS

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--runs", nargs="+", default=["spar", "semisub"])
parser.add_argument("--pea-dir", default=str(Path(OUTDIR) / "pea"))
parser.add_argument("--outdir", default="figures/pea")
parser.add_argument("--max-days", type=int, default=None, help="Limit number of frames (for testing)")
parser.add_argument("--fps", type=int, default=6)
parser.add_argument("--dpi", type=int, default=100)
parser.add_argument("--sample-stride", type=int, default=10,
                    help="Use every n-th cell in both directions for the difference colour range")
args = parser.parse_args()

PEA_DIR = Path(args.pea_dir)
LOG_NORM = LogNorm(vmin=1, vmax=1000)  # J m-3; same for all runs and days


def month_files(run):
    """Return [(month, run_file, wakeref_file)] for months where both exist."""
    out = []
    for f in sorted(PEA_DIR.glob(f"pea_{run}_*.nc")):
        month = f.stem.split("_")[-1]
        wake = PEA_DIR / f"pea_wakeref_{month}.nc"
        if wake.exists():
            out.append((month, f, wake))
    return out


def daily_pairs(files, max_days):
    """Yield (day, pea_run, pea_wake) 2D arrays, one day at a time (lazy, low memory)."""
    n = 0
    for month, frun, fwake in files:
        with xr.open_dataset(frun) as exp, xr.open_dataset(fwake) as wake:
            pe, pw = xr.align(exp.pea, wake.pea, join="inner")
            for i in range(pe.sizes["ocean_time"]):
                if max_days is not None and n >= max_days:
                    return
                yield pe.ocean_time.values[i], pe.isel(ocean_time=i).values, pw.isel(ocean_time=i).values
                n += 1


for run in args.runs:
    files = month_files(run)
    if not files:
        print(f"No PEA files with matching wakeref for {run} in {PEA_DIR}")
        continue

    with xr.open_dataset(files[0][2]) as w:
        lon, lat = w.lon_rho.load(), w.lat_rho.load()
    template = xr.DataArray(np.zeros(lon.shape), dims=lon.dims, coords={"lon_rho": lon, "lat_rho": lat})

    # Pass 1: fixed symmetric difference range (99th percentile of |diff| over all days)
    s = args.sample_stride
    samples = [np.abs((pe - pw)[::s, ::s]).ravel() for _, pe, pw in daily_pairs(files, args.max_days)]
    samples = np.concatenate(samples)
    vmax = float(np.nanpercentile(samples, 99))
    print(run, "diff vmax", round(vmax, 2), "J m-3")

    fig, axes = plt.subplots(1, 3, figsize=(24, 10), subplot_kw={"projection": ccrs.NorthPolarStereo()},
                             layout="constrained")
    pcm_exp = draw_map(axes[0], template, cmap=cmo.matter, norm=LOG_NORM)
    pcm_wake = draw_map(axes[1], template, cmap=cmo.matter, norm=LOG_NORM)
    pcm_diff = draw_map(axes[2], template, cmap=cmo.balance, vmin=-vmax, vmax=vmax)
    for ax in axes:
        add_farm_outlines(ax)
    axes[0].set_title(run)
    axes[1].set_title("wakeref")
    axes[2].set_title(f"{run} - wakeref")
    fig.colorbar(pcm_exp, ax=axes[:2], orientation="vertical", label="PEA (J m$^{-3}$)",
                 extend="both", shrink=0.8)
    fig.colorbar(pcm_diff, ax=axes[2], orientation="vertical", label="PEA difference (J m$^{-3}$)",
                 extend="both", shrink=0.8)
    title = fig.suptitle("")

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    fname = out / f"pea_{run}_daily.mp4"
    writer = FFMpegWriter(fps=args.fps, codec="libx264", extra_args=["-pix_fmt", "yuv420p"])
    n = 0
    with writer.saving(fig, str(fname), dpi=args.dpi):
        # Pass 2: one frame per day; clip noise (PEA < 1) so log scale shows no holes
        for t, pe, pw in daily_pairs(files, args.max_days):
            pcm_exp.set_array(np.clip(pe, 1, None))
            pcm_wake.set_array(np.clip(pw, 1, None))
            pcm_diff.set_array(pe - pw)
            title.set_text(f"Daily PEA, {str(t)[:10]}")
            writer.grab_frame()
            n += 1
    plt.close(fig)
    print(run, n, "frames ->", fname)
