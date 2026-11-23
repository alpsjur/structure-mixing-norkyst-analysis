"""Depth-range mean TKE, GLS and dissipation from ROMS his output. See the metrics skill."""
import numpy as np
import xarray as xr

from analysis.current import layer_thickness, range_mean
from analysis.pea import z_levels


def turbulence(ds, ranges, tidxs=None, slab=100):
    """Mean tke, gls and dissipation over depth ranges, averaged over time records of a his dataset.

    ranges: dict name -> (zmin, zmax), depths in m, negative down, relative to the surface.
    tke, gls are on s_w; layer values are the mean of the two bounding interfaces, weighted by
    layer thickness. Each record is depth-averaged first, then records are averaged
    (tidxs: record indices, default all).
    Returns a Dataset on the rho grid with, per range name, tke_<name> (m2 s-2),
    gls_<name> (mean gls), eps_<name> (mean of gls**1.5 per record, GEN closure) and H_<name> (m).
    """
    if int(ds.Vtransform) != 2:
        raise ValueError(f"Only Vtransform=2 is supported, got {int(ds.Vtransform)}")
    if tidxs is None:
        tidxs = range(ds.sizes["ocean_time"])
    tidxs = list(tidxs)
    shape = ds.lon_rho.shape
    neta = shape[0]
    hc = float(ds.hc)
    out = {f"{v}_{n}": np.zeros(shape) for n in ranges for v in ("tke", "gls", "eps", "H")}
    for j in range(0, neta, slab):
        sl = slice(j, min(j + slab, neta))
        h = ds.h.isel(eta_rho=sl)
        for t in tidxs:
            zeta = ds.zeta.isel(ocean_time=t, eta_rho=sl)
            zw = z_levels(zeta, h, ds.s_w.values, ds.Cs_w.values, hc)
            q = {}
            for v in ("tke", "gls"):
                w = ds[v].isel(ocean_time=t, eta_rho=sl).values.astype("float64")
                q[v] = 0.5 * (w[:-1] + w[1:])
            q["eps"] = q["gls"] ** 1.5
            for name, (zmin, zmax) in ranges.items():
                dz = layer_thickness(zw, zmin, zmax)
                for v in ("tke", "gls", "eps"):
                    m, H = range_mean(q[v], dz)
                    out[f"{v}_{name}"][sl] += m / len(tidxs)  # NaN where H = 0
                out[f"H_{name}"][sl] += H / len(tidxs)
    wet = ds.mask_rho.values == 1
    long = {"tke": "mean turbulent kinetic energy", "gls": "mean generic length scale (psi)",
            "eps": "mean dissipation, gls**1.5 per record", "H": "water thickness inside the depth range"}
    units = {"tke": "m2 s-2", "gls": ds.gls.attrs.get("units", ""), "eps": "m2 s-3", "H": "m"}
    data = {}
    for k, val in out.items():
        base = k.split("_")[0]
        data[k] = (("eta_rho", "xi_rho"), np.where(wet, val, np.nan),
                   {"long_name": long[base], "units": units[base]})
    return xr.Dataset(data, coords={"lon_rho": ds.lon_rho, "lat_rho": ds.lat_rho})
