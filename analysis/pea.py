"""Potential energy anomaly (PEA) from ROMS output. See the stratification-metrics skill."""
import gsw
import numpy as np
import xarray as xr

G = 9.81


def z_levels(zeta, h, s, Cs, hc):
    """Depth (Vtransform=2) at levels s/Cs (s_rho/Cs_r or s_w/Cs_w), shape (len(s), eta, xi).

    Negative downward from z=0.
    """
    s = np.asarray(s)[:, None, None]
    C = np.asarray(Cs)[:, None, None]
    z0 = (hc * s + h.values * C) / (hc + h.values)
    return zeta.values + (zeta.values + h.values) * z0


def pea_slab(temp, salt, zw, zr, lon, lat, zmin=None, zmax=None):
    """PEA (J m-3) for one slab.

    temp, salt: (s_rho, eta, xi); zw: (s_w, eta, xi); zr: (s_rho, eta, xi).

    The integration is over the part of the water column between zmin and zmax
    (depths in m, negative down, relative to the surface). Default: whole column.
    """
    zr = zr - zw[-1]  # depth relative to the surface (removes zeta)
    zw = zw - zw[-1]
    lo = zw[:-1]
    hi = zw[1:]
    if zmin is not None:
        lo = np.maximum(lo, zmin)
    if zmax is not None:
        hi = np.minimum(hi, zmax)
    dz = np.clip(hi - lo, 0, None)  # thickness of each layer inside the range
    zc = 0.5 * (np.maximum(zw[:-1], lo) + np.minimum(zw[1:], hi))

    p = gsw.p_from_z(zr, lat)
    SA = gsw.SA_from_SP(salt, p, lon, lat)
    CT = gsw.CT_from_pt(SA, temp)
    rho = gsw.rho(SA, CT, 0.0)  # potential density: a mixed column has PEA=0 (no compressibility)

    H = dz.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        rho_mean = (rho * dz).sum(axis=0) / H
        pea = (G * (rho_mean - rho) * zc * dz).sum(axis=0) / H
    pea[H <= 0] = np.nan
    return pea


def pea(ds, tidx=0, zmin=None, zmax=None, slab=100):
    """PEA for one time record of an avg/his dataset. Returns a 2D DataArray on the rho grid."""
    if int(ds.Vtransform) != 2:
        raise ValueError(f"Only Vtransform=2 is supported, got {int(ds.Vtransform)}")
    out = np.full(ds.lon_rho.shape, np.nan)
    hc = float(ds.hc)
    for j in range(0, out.shape[0], slab):
        sl = slice(j, min(j + slab, out.shape[0]))
        zeta = ds.zeta.isel(ocean_time=tidx, eta_rho=sl)
        h = ds.h.isel(eta_rho=sl)
        zw = z_levels(zeta, h, ds.s_w.values, ds.Cs_w.values, hc)
        zr = z_levels(zeta, h, ds.s_rho.values, ds.Cs_r.values, hc)
        temp = ds.temp.isel(ocean_time=tidx, eta_rho=sl).values.astype("float64")
        salt = ds.salt.isel(ocean_time=tidx, eta_rho=sl).values.astype("float64")
        lon = ds.lon_rho.isel(eta_rho=sl).values
        lat = ds.lat_rho.isel(eta_rho=sl).values
        out[sl] = pea_slab(temp, salt, zw, zr, lon, lat, zmin, zmax)
    out = np.where(ds.mask_rho.values == 1, out, np.nan)
    return xr.DataArray(
        out, dims=("eta_rho", "xi_rho"),
        coords={"lon_rho": ds.lon_rho, "lat_rho": ds.lat_rho},
        name="pea", attrs={"long_name": "potential energy anomaly", "units": "J m-3"},
    )
