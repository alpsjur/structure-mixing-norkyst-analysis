"""Monthly farm TS diagrams (0-150 m): wakeref vs run, plus run - wakeref profiles of T, S and sigma0.

Run from the repo root after scripts/computations/make_ts_farm.py (default input files/ts).
One figure per farm, run and month; columns: TS diagram | dT | dS | dsigma0.
TS diagram: all farm cells x depth levels (wakeref grey, run coloured by depth), farm-mean profiles
(wakeref black dashed, run solid), sigma0 isolines. Difference columns: farm-mean run - wakeref vs depth,
shaded 10-90 % range over the farm cells.
-> figures/ts_farm/<farm>/ts_<run>_<YYYY-MM>.png
Usage: python scripts/plotting/ts_farm_monthly.py [--indir files/ts] [--runs spar semisub] [--farms ...]
"""
import argparse
import os
import sys
import warnings

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
sys.path.insert(0, ".github/skills/figure-style")
sys.path.insert(0, ".")

from pathlib import Path

import cmocean.cm as cmo
import gsw
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from map_example import save_fig

MONTHS = [f"2022-{m:02d}" for m in range(2, 9)]
FARMS = ["Nordavind_D", "Nordavind_C", "Nordvest_C", "Sorvest_F", "Vestavind_B", "Vestavind_F"]


def sigma0(temp, salt, lon, lat, z):
    """Potential density anomaly (kg m-3) from potential temperature and practical salinity."""
    p = gsw.p_from_z(z[None, :], lat[:, None])
    SA = gsw.SA_from_SP(salt, p, lon[:, None], lat[:, None])
    CT = gsw.CT_from_pt(SA, temp)
    return gsw.sigma0(SA, CT), SA, CT


def load(indir, farm, run, month):
    ds = xr.open_dataset(Path(indir) / f"ts_{farm}_{run}_{month}.nc").load()
    z, lon, lat = ds.z.values, ds.lon.values, ds.lat.values
    out = {"z": z}
    for tag in ("ref", "run"):
        sig, SA, CT = sigma0(ds[f"temp_{tag}"].values.astype(float), ds[f"salt_{tag}"].values.astype(float), lon, lat, z)
        out[tag] = {"CT": CT, "SA": SA, "sig": sig}
    out["dT"], out["dS"] = ds.dtemp.values, ds.dsalt.values
    out["dsig"] = out["run"]["sig"] - out["ref"]["sig"]
    return out


def diff_panel(ax, z, d, color):
    mean = np.nanmean(d, axis=0)
    lo, hi = np.nanpercentile(d, [10, 90], axis=0)
    ax.fill_betweenx(z, lo, hi, color=color, alpha=0.25, linewidth=0)
    ax.plot(mean, z, color=color)
    ax.axvline(0, color="black", linewidth=0.5)
    ax.grid(alpha=0.3)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--indir", default="files/ts")
    p.add_argument("--runs", nargs="+", default=["spar", "semisub"])
    p.add_argument("--farms", nargs="+", default=FARMS)
    p.add_argument("--months", nargs="+", default=MONTHS)
    a = p.parse_args()

    for farm in a.farms:
        for run in a.runs:
            data = {m: load(a.indir, farm, run, m) for m in a.months}
            # axis limits shared over the months so the panels are comparable
            allref = [d["ref"] for d in data.values()] + [d["run"] for d in data.values()]
            SA_all = np.concatenate([r["SA"].ravel() for r in allref])
            CT_all = np.concatenate([r["CT"].ravel() for r in allref])
            slim = np.nanpercentile(SA_all, [0.1, 99.9]) + np.array([-0.05, 0.05])
            tlim = np.nanpercentile(CT_all, [0.1, 99.9]) + np.array([-0.3, 0.3])
            ss, tt = np.meshgrid(np.linspace(*slim, 80), np.linspace(*tlim, 80))
            sig_bg = gsw.sigma0(ss, tt)

            for month in a.months:
                d = data[month]
                z = d["z"]
                zz = np.broadcast_to(z, d["ref"]["SA"].shape)
                fig, axes = plt.subplots(1, 4, figsize=(16, 5), gridspec_kw={"width_ratios": [2.2, 1, 1, 1]},
                                         layout="constrained")
                ax = axes[0]
                cs = ax.contour(ss, tt, sig_bg, levels=np.arange(20, 30, 0.5), colors="gray", linewidths=0.4)
                ax.clabel(cs, fmt="%.1f", fontsize=6)
                ax.scatter(d["ref"]["SA"], d["ref"]["CT"], s=3, color="tab:gray", alpha=0.4, linewidths=0,
                           label="wakeref", rasterized=True)
                sc = ax.scatter(d["run"]["SA"], d["run"]["CT"], s=3, c=-zz, cmap=cmo.deep, vmin=0, vmax=150,
                                alpha=0.5, linewidths=0, label=run, rasterized=True)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    ax.plot(np.nanmean(d["ref"]["SA"], 0), np.nanmean(d["ref"]["CT"], 0), "k--", linewidth=1,
                            label="wakeref mean")
                    ax.plot(np.nanmean(d["run"]["SA"], 0), np.nanmean(d["run"]["CT"], 0), "k-", linewidth=1,
                            label=f"{run} mean")
                    diff_panel(axes[1], z, d["dT"], "tab:red")
                    diff_panel(axes[2], z, d["dS"], "tab:blue")
                    diff_panel(axes[3], z, d["dsig"], "tab:green")
                ax.set_xlim(slim)
                ax.set_ylim(tlim)
                ax.set_xlabel("SA (g kg$^{-1}$)")
                ax.set_ylabel("CT (°C)")
                ax.legend(loc="upper left", fontsize=7, markerscale=3)
                fig.colorbar(sc, ax=ax, label="depth (m)", pad=0.01)
                for x in axes[1:]:
                    x.set_ylim(-150, 0)
                    x.set_xlabel("farm mean (line), 10-90 % (shading)", fontsize=7)
                axes[1].set_ylabel("depth (m)")
                axes[0].set_title(f"{farm.replace('_', ' ')}, {month}: {run} vs wakeref")
                axes[1].set_title(f"$\\Delta$T (°C), {run} - wakeref")
                axes[2].set_title("$\\Delta$S")
                axes[3].set_title("$\\Delta\\sigma_0$ (kg m$^{-3}$)")
                save_fig(fig, f"ts_{run}_{month}", f"ts_farm/{farm}")
                plt.close(fig)
            print(farm, run, "done", flush=True)


if __name__ == "__main__":
    main()
