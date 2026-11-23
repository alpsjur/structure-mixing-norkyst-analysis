"""Build farm + downstream-extension masks. Run from the repo root.

For each wind farm, adds a downstream-extension mask to the farm footprint:
- Directional farms (stable mean current, see docs/notes.md): built per *sector*, since
  sectors can be spread far apart along the flow direction (a single farm-wide corridor then
  leaves gaps between the farm and the corridor for sectors upstream of the farm's downstream
  edge). Each sector gets its own fixed-width corridor, starting at the sector's centroid and
  extending DOWNSTREAM_KM along the sector's own mean current direction (0-25 m, wakeref,
  circular mean over all months weighted by n_days). Width = sector's own cross-stream extent
  + 2 x MARGIN_KM. The farm's extension is the union of its sectors' corridors.
- Weak/directionally-unstable farms (WEAK_FARMS): one isotropic circular buffer of radius
  DOWNSTREAM_KM around the whole farm footprint instead (no per-sector split needed, since an
  isotropic buffer cannot leave the same kind of gap).

Output per farm: `<farm>_extension` (1 = downstream corridor/circle, excludes the farm
itself) and `<farm>_extended` (1 = farm OR extension), both masked to wet (mask_rho) cells.
Attributes record the shape, length/radius, width/margin, and per-sector direction/speed used.

Usage (repo root):
    python scripts/computations/make_windfarm_downstream_masks.py
"""
import os
import sys

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
sys.path.insert(0, ".")

from pathlib import Path

import numpy as np
import xarray as xr

from analysis.downstream import circle_mask, corridor_mask, farm_mean_direction
from analysis.io import BASE, MASKS, OUTDIR

# ---- settings ----------------------------------------------------------------
DOWNSTREAM_KM = 60.0  # corridor length / circle radius; see docs/notes.md for rationale
MARGIN_KM = 5.0  # added on each side of the sector's cross-stream extent for corridor width
DIRECTION_RANGE = "0_25"  # depth range used to estimate the mean current direction
WEAK_FARMS = {"Nordvest_C", "Sorvest_F"}  # isotropic circle instead of a directional corridor
OUT = Path("files/windfarm_downstream_masks.nc")
# --------------------------------------------------------------------------------

masks = xr.open_dataset(MASKS)
FARMS = [v for v in masks.data_vars if not v.endswith("_sectors")]
farm_masks = {f: (masks[f].values > 0) for f in FARMS}

with xr.open_dataset(f"{BASE}/wakeref/norkyst_avg_0001.nc") as g:
    angle = g.angle.load()
    wet = g.mask_rho.values > 0

current_dir = Path(OUTDIR) / "current"
lon, lat = masks.lon_rho.values, masks.lat_rho.values

# sector masks for the directional farms (dict key: "<farm>_sector<i>")
sector_masks = {}
sector_of = {}  # "<farm>_sector<i>" -> (farm, i)
for farm in FARMS:
    if farm in WEAK_FARMS:
        continue
    labels = masks[f"{farm}_sectors"].values
    for i in range(1, int(labels.max()) + 1):
        key = f"{farm}_sector{i}"
        sector_masks[key] = labels == i
        sector_of[key] = (farm, i)

farm_directions = farm_mean_direction(current_dir, {f: farm_masks[f] for f in WEAK_FARMS}, angle,
                                       range_name=DIRECTION_RANGE)
sector_directions = farm_mean_direction(current_dir, sector_masks, angle, range_name=DIRECTION_RANGE)

out = {}
for farm in FARMS:
    fmask = farm_masks[farm]
    if farm in WEAK_FARMS:
        direction_deg, speed = farm_directions[farm]
        ext = circle_mask(lon, lat, fmask, DOWNSTREAM_KM) & ~fmask & wet
        attrs = {
            "long_name": f"Downstream extension of {farm} (circle, weak/unstable current)",
            "shape": "circle",
            "radius_km": DOWNSTREAM_KM,
            "mean_current_direction_deg": direction_deg,
            "mean_current_speed_m_s": speed,
            "note": "isotropic buffer used instead of a directional corridor; see docs/notes.md",
        }
        print(f"{farm}: shape=circle, dir={direction_deg:.1f} deg, speed={speed:.3f} m/s, "
              f"farm cells={int(fmask.sum())}, extension cells={int(ext.sum())}")
    else:
        sector_keys = [k for k, (f, _) in sector_of.items() if f == farm]
        ext = np.zeros_like(fmask)
        dirs, speeds = [], []
        for key in sector_keys:
            smask = sector_masks[key]
            direction_deg, speed = sector_directions[key]
            dirs.append(direction_deg)
            speeds.append(speed)
            ext |= corridor_mask(lon, lat, smask, direction_deg, DOWNSTREAM_KM, MARGIN_KM)
        ext = ext & ~fmask & wet
        attrs = {
            "long_name": f"Downstream extension of {farm} (union of per-sector corridors)",
            "shape": "corridor",
            "length_km": DOWNSTREAM_KM,
            "margin_km": MARGIN_KM,
            "n_sectors": len(sector_keys),
            "sector_direction_deg": dirs,
            "sector_speed_m_s": speeds,
            "direction_range": DIRECTION_RANGE,
        }
        print(f"{farm}: shape=corridor, {len(sector_keys)} sectors, dirs="
              f"{[round(d, 1) for d in dirs]} deg, speeds={[round(s, 3) for s in speeds]} m/s, "
              f"farm cells={int(fmask.sum())}, extension cells={int(ext.sum())}")
    out[f"{farm}_extension"] = xr.DataArray(ext.astype("int8"), dims=("eta_rho", "xi_rho"), attrs=attrs)
    out[f"{farm}_extended"] = xr.DataArray(
        (ext | fmask).astype("int8"), dims=("eta_rho", "xi_rho"),
        attrs={"long_name": f"{farm} mask OR its downstream extension"})

ds = xr.Dataset(out, coords={"lon_rho": masks.lon_rho, "lat_rho": masks.lat_rho})
ds.attrs["description"] = (
    "Wind-farm downstream-extension masks on the Norkyst rho grid, for averaging over the "
    "farm plus the water advected downstream (or a buffer, for weak-current farms). "
    "Directional farms: built per sector, each corridor starting at its own sector centroid, "
    "to avoid gaps for sectors spread out along the flow direction. "
    f"See docs/notes.md (2026-11-20 entries). Built from windfarm_masks.nc and "
    f"current_wakeref_*.nc ({DIRECTION_RANGE} m range)."
)
OUT.parent.mkdir(exist_ok=True)
ds.to_netcdf(OUT, encoding={v: {"zlib": True, "complevel": 4} for v in ds.data_vars})
print("wrote", OUT)
