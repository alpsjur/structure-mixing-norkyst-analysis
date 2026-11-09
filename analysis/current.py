"""Depth-range mean current from ROMS output. See the metrics skill."""
import numpy as np
import xarray as xr

from analysis.pea import z_levels


def u_to_rho(u):
    """(..., eta, xi_u) -> (..., eta, xi_rho); edge points copy the nearest u point."""
    u = np.pad(u, [(0, 0)] * (u.ndim - 1) + [(1, 1)], mode="edge")
    return 0.5 * (u[..., :-1] + u[..., 1:])


def v_to_rho(v, first, last):
    """(..., eta_v rows, xi) -> (..., eta rho rows, xi).

    v holds rows [a-1, b) of the eta_v axis clipped to its range; `first`/`last` say whether
    the slab touches the south/north edge, where the missing row is replaced by the edge row.
    """
    pad = [(0, 0)] * (v.ndim - 2) + [(1 if first else 0, 1 if last else 0), (0, 0)]
    v = np.pad(v, pad, mode="edge")
    return 0.5 * (v[..., :-1, :] + v[..., 1:, :])


def range_mean(q, dz):
    """Thickness-weighted mean over the first axis. q, dz: (s_rho, eta, xi)."""
    H = dz.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        m = (q * dz).sum(axis=0) / H
    m[H <= 0] = np.nan
    return m, H


def layer_thickness(zw, zmin, zmax):
    """Thickness of each layer inside [zmin, zmax] (depths relative to the surface, negative down)."""
    zw = zw - zw[-1]
    lo = np.maximum(zw[:-1], zmin)
    hi = np.minimum(zw[1:], zmax)
    return np.clip(hi - lo, 0, None)


def current(ds, ranges, tidx=0, slab=100):
    """Mean current over depth ranges for one time record of an avg/his dataset.

    ranges: dict name -> (zmin, zmax), depths in m, negative down, relative to the surface.
    u, v are interpolated to rho points (not rotated) and weighted by layer thickness.
    Returns a Dataset on the rho grid with, for each range name, ubar_<name>, vbar_<name>
    (mean components), speed_<name> (mean of sqrt(u2+v2)) and H_<name> (thickness covered, m).
    Combine ranges with (m1*H1 + m2*H2) / (H1 + H2).
    """
    if int(ds.Vtransform) != 2:
        raise ValueError(f"Only Vtransform=2 is supported, got {int(ds.Vtransform)}")
    shape = ds.lon_rho.shape
    neta = shape[0]
    hc = float(ds.hc)
    out = {f"{v}_{n}": np.full(shape, np.nan) for n in ranges for v in ("ubar", "vbar", "speed", "H")}
    for j in range(0, neta, slab):
        a, b = j, min(j + slab, neta)
        sl = slice(a, b)
        zeta = ds.zeta.isel(ocean_time=tidx, eta_rho=sl)
        h = ds.h.isel(eta_rho=sl)
        zw = z_levels(zeta, h, ds.s_w.values, ds.Cs_w.values, hc)
        u = ds.u.isel(ocean_time=tidx, eta_u=sl).values.astype("float64")
        v = ds.v.isel(ocean_time=tidx, eta_v=slice(max(a - 1, 0), min(b, neta - 1))).values.astype("float64")
        u = u_to_rho(np.nan_to_num(u))  # land faces count as zero velocity
        v = v_to_rho(np.nan_to_num(v), a == 0, b == neta)
        speed = np.hypot(u, v)
        for name, (zmin, zmax) in ranges.items():
            dz = layer_thickness(zw, zmin, zmax)
            out[f"ubar_{name}"][sl], out[f"H_{name}"][sl] = range_mean(u, dz)
            out[f"vbar_{name}"][sl], _ = range_mean(v, dz)
            out[f"speed_{name}"][sl], _ = range_mean(speed, dz)
    wet = ds.mask_rho.values == 1
    attrs = {"ubar": "mean eastward-grid u (not rotated)", "vbar": "mean northward-grid v (not rotated)",
             "speed": "mean current speed", "H": "water thickness inside the depth range"}
    data = {}
    for k, val in out.items():
        base = k.split("_")[0]
        data[k] = (("eta_rho", "xi_rho"), np.where(wet, val, np.nan),
                   {"long_name": attrs[base], "units": "m" if base == "H" else "m s-1"})
    return xr.Dataset(data, coords={"lon_rho": ds.lon_rho, "lat_rho": ds.lat_rho})
