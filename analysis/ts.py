"""Farm temperature-salinity profiles on fixed depths from monthly mean + anomaly files."""
import numpy as np
import xarray as xr

from analysis.pea import z_levels


def zgrid(zmax=150.0, dz=5.0):
    """Fixed depths (m, negative down) at layer centres from the surface to zmax."""
    return -(dz / 2 + dz * np.arange(int(round(zmax / dz))))


def farm_bbox(mask):
    eta, xi = np.nonzero(mask)
    return slice(eta.min(), eta.max() + 1), slice(xi.min(), xi.max() + 1)


def to_fixed_z(var, z, zfix):
    """Interpolate (s_rho, ncell) onto zfix (nz,) per column; NaN outside the column. Returns (ncell, nz)."""
    out = np.full((var.shape[1], len(zfix)), np.nan)
    for i in range(var.shape[1]):
        zc, v = z[:, i], var[:, i]
        ok = np.isfinite(v)
        if ok.sum() < 2:
            continue
        out[i] = np.interp(zfix, zc[ok], v[ok], left=np.nan, right=np.nan)
    return out


def farm_cells(ds, name, es, xs, mask):
    """Values of `name` (s_rho, ncell) at the farm cells (mask is the bbox-sliced boolean mask)."""
    return ds[name].isel(ocean_time=0, eta_rho=es, xi_rho=xs).values[:, mask].astype("float64")


def farm_ts(mean_ds, anom_ds, es, xs, mask, zfix):
    """Reference (wakeref mean) and run (mean + anomaly) T, S, plus the anomaly itself, per farm cell.

    Returns a dict of (ncell, nz) arrays: temp_ref, salt_ref, temp_run, salt_run, dtemp, dsalt.
    The depths of the reference and the run come from their own mean sea surface height.
    dtemp/dsalt are the anomaly files on the reference depths (the matched-day difference, unaffected
    by the mean file using all timestamps), run - wakeref.
    """
    h = mean_ds.h.isel(eta_rho=es, xi_rho=xs)
    hc = float(mean_ds.hc)
    zeta_ref = mean_ds.zeta.isel(ocean_time=0, eta_rho=es, xi_rho=xs)
    zeta_run = zeta_ref + anom_ds.zeta.isel(ocean_time=0, eta_rho=es, xi_rho=xs)

    def z_at(zeta):
        z = z_levels(zeta, h, mean_ds.s_rho.values, mean_ds.Cs_r.values, hc)
        return z[:, mask] - zeta.values[mask]  # relative to the surface

    z_ref, z_run = z_at(zeta_ref), z_at(zeta_run)
    t_ref, s_ref = farm_cells(mean_ds, "temp", es, xs, mask), farm_cells(mean_ds, "salt", es, xs, mask)
    dt, ds_ = farm_cells(anom_ds, "temp", es, xs, mask), farm_cells(anom_ds, "salt", es, xs, mask)
    return {
        "temp_ref": to_fixed_z(t_ref, z_ref, zfix),
        "salt_ref": to_fixed_z(s_ref, z_ref, zfix),
        "temp_run": to_fixed_z(t_ref + dt, z_run, zfix),
        "salt_run": to_fixed_z(s_ref + ds_, z_run, zfix),
        "dtemp": to_fixed_z(dt, z_ref, zfix),
        "dsalt": to_fixed_z(ds_, z_ref, zfix),
    }


def to_dataset(fields, zfix, lon, lat, attrs):
    ds = xr.Dataset(
        {k: (("cell", "z"), v.astype("float32")) for k, v in fields.items()},
        coords={"z": ("z", zfix, {"units": "m"}), "lon": ("cell", lon), "lat": ("cell", lat)},
        attrs=attrs,
    )
    return ds
