"""Build farm + downstream-extension masks. See the metrics skill (downstream mask notes)
and docs/notes.md (2026-11-20 entries) for the rationale and design decisions.

Two shapes, depending on how stable the farm's mean current direction is:
- "corridor": fixed-width strip extending DOWNSTREAM_KM downstream, starting at the centroid
  of each wind-farm *sector* (not the whole multi-sector farm: sectors can be spread far
  apart along the flow direction, so a single farm-wide corridor leaves gaps for sectors
  upstream of the farm's downstream edge). Width = the sector's own cross-stream extent plus
  a margin on each side. The farm's extension mask is the union of its sectors' corridors.
- "circle": isotropic buffer of radius DOWNSTREAM_KM around the whole farm footprint, for
  farms where the current direction is weak/unstable (no persistent downstream direction).
  Built from the whole farm, not per sector, since there is no direction to cause the gap
  problem above.

Direction is estimated from the farm- or sector-mean 0-25 m wakeref current (depth-independent
enough that the structure's depth range does not matter, see docs/notes.md): a vector mean
(mean of u, v directly, weighted by each month's `n_days`) over all available months, the same
averaging used for the whole-period mean current shown in windfarm_downstream_map.py, so the
corridor direction always matches the plotted background current.
"""
import numpy as np
import xarray as xr
from scipy.spatial import cKDTree

R_EARTH = 6_371_000.0  # m


def local_xy(lon, lat, lon0, lat0):
    """Equirectangular local tangent-plane (x=east, y=north, metres) around (lon0, lat0).

    Good enough for distances of a few tens of km; not for the whole domain.
    """
    deg2rad = np.pi / 180.0
    x = R_EARTH * np.cos(lat0 * deg2rad) * (lon - lon0) * deg2rad
    y = R_EARTH * (lat - lat0) * deg2rad
    return x, y


def farm_mean_direction(current_dir, farms, angle, range_name="0_25"):
    """Vector-mean current direction per mask, weighted by each month's `n_days`.

    current_dir: Path to the directory holding current_wakeref_<YYYY-MM>.nc files.
    farms: {name: boolean mask array (eta_rho, xi_rho)}; works for whole farms or for
        individual sectors (any named set of masks).
    angle: grid rotation angle (eta_rho, xi_rho), from an avg/grid file.
    Returns {name: (direction_deg, speed_m_s)}; direction is "towards", degrees from north,
    clockwise (oceanographic convention), from the vector mean of the monthly (u, v) (i.e. the
    mean current vector, not a direction-only circular mean), matching the whole-period mean
    current used in windfarm_downstream_map.py.
    """
    months = sorted(f.stem.split("_")[-1] for f in current_dir.glob("current_wakeref_????-??.nc"))
    sums = {name: np.zeros(2) for name in farms}  # weighted sum of (east, north), metres/s x days
    weight_total = {name: 0.0 for name in farms}
    for month in months:
        ds = xr.open_dataset(current_dir / f"current_wakeref_{month}.nc")
        n_days = float(ds.attrs["n_days"])
        for name, mask in farms.items():
            w = xr.DataArray(mask, dims=("eta_rho", "xi_rho"))
            u = ds[f"ubar_{range_name}"].where(w).mean().item()
            v = ds[f"vbar_{range_name}"].where(w).mean().item()
            a = angle.where(w).mean().item()
            east = u * np.cos(a) - v * np.sin(a)
            north = u * np.sin(a) + v * np.cos(a)
            sums[name] += n_days * np.array([east, north])
            weight_total[name] += n_days
        ds.close()
    out = {}
    for name in farms:
        east, north = sums[name] / weight_total[name]
        direction = np.degrees(np.arctan2(east, north)) % 360
        mean_speed = np.hypot(east, north)
        out[name] = (direction, mean_speed)
    return out


def corridor_mask(lon, lat, mask, direction_deg, length_km, margin_km):
    """Boolean mask (same shape as lon/lat) of the corridor downstream of `mask`.

    The corridor starts at the centroid of `mask` (not its downstream edge), so it always
    touches/overlaps the mask regardless of the mask's own extent along the flow direction.
    Meant to be called per sector (not per whole multi-sector farm), since sectors can be far
    apart along the flow direction; a single farm-wide corridor would then leave gaps between
    the farm and the corridor for the sectors upstream of the farm's downstream edge.

    direction_deg: "towards" direction (deg from north, clockwise) the corridor extends in.
    length_km: corridor length beyond the mask's centroid.
    margin_km: added on each side of the mask's own cross-stream extent for the width.
    """
    eta, xi = np.nonzero(mask)
    lon0, lat0 = lon[eta, xi].mean(), lat[eta, xi].mean()
    x, y = local_xy(lon, lat, lon0, lat0)

    theta = np.radians(direction_deg)
    u_hat = np.array([np.sin(theta), np.cos(theta)])  # downstream unit vector (east, north)
    v_hat = np.array([np.cos(theta), -np.sin(theta)])  # cross-stream unit vector

    s = x * u_hat[0] + y * u_hat[1]
    c = x * v_hat[0] + y * v_hat[1]

    c_mask = c[eta, xi]
    c_lo, c_hi = c_mask.min(), c_mask.max()
    margin = margin_km * 1000.0
    length = length_km * 1000.0

    # s=0 is the mask centroid by construction (x, y are relative to lon0, lat0)
    return (s >= 0) & (s <= length) & (c >= c_lo - margin) & (c <= c_hi + margin)


def circle_mask(lon, lat, farm_mask, radius_km):
    """Boolean mask (same shape as lon/lat): cells within radius_km of the nearest farm cell."""
    eta, xi = np.nonzero(farm_mask)
    lon0, lat0 = lon[eta, xi].mean(), lat[eta, xi].mean()
    x, y = local_xy(lon, lat, lon0, lat0)

    tree = cKDTree(np.column_stack([x[eta, xi], y[eta, xi]]))
    dist, _ = tree.query(np.column_stack([x.ravel(), y.ravel()]), workers=-1)
    dist = dist.reshape(x.shape)
    return dist <= radius_km * 1000.0
