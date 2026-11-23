---
name: metrics
description: Definitions and conventions for metrics and calculations in the wind-farm mixing analysis.
---

# Metrics and methodological choices
Open data with the `norkyst-data` skill; precomputed files are in `processed-data`. 
This file contains decisions for *how* to compute things.

## Methodological choices

### Depth-integrals and depth-averages
- Raw output is on terrain-following coordinates. See `norkyst-data`.
- Layer thicknesses `dz` come from differences of `z_w` (computed from the ROMS vertical grid variables); do not weight levels equally.
- For sums over a depth range:  layer thickness from `z_w` clipped to the range.

### Depth ranges
- Typical depth ranges are: 
  - surface to the semisubmersible depth (0-25 m)
  - semisubmersible depth to spar depth (25-130 m)
- For areas that are shallower than the depth range: use the part of the depth range that has data. 
- Averages/sums over the full spar depth range (0 - 130 m) can be calculated by combining the (0-25 m) and (25-130 m) averages/sums. Caveat: for areas that are shallower than the full depth range, the weights must be adjusted accordingly. 

## Metrics

### Potential energy anomaly (PEA)
- Definition: `PEA = (1/H) * integral_{-H}^{0} (rho_mix - rho) * g * z dz`. Units J m-3. Higher = more stratified.
- Reference (mixed) state: default `ref="ts"`, `rho_mix = rho(mean SA, mean CT)` (depth-weighted means of the conserved quantities, evaluated at p=0), which includes cabbeling. The classical `ref="rho"` (`rho_mix = (1/H) * integral rho dz`) is available as a variant. Difference (wakeref, whole column): ~1-2 % on the shelf and for h < 1000 m, but ~-45 % for h > 1000 m (PEA_ts lower), since it scales with column depth.
- Use density calculated from `temp` (potential temperature) and `salt` (practical salinity). ROMS runs with `NONLIN_EOS` (Jackett & McDougall 1995, `rho0 = 1025`). Using TEOS-10 (`gsw`) is accepted: small differences are OK for PEA. If using `gsw`, convert first (`SA = gsw.SA_from_SP`, `CT = gsw.CT_from_pt`) and use pressure from rho-level depth (`gsw.p_from_z`) only for the `SA` conversion. Evaluate density at the surface pressure (`gsw.rho(SA, CT, 0)`, potential density), otherwise compressibility gives a mixed column a nonzero PEA that grows with depth. Do not pass raw `temp`/`salt` to `gsw.rho`.
- Default integration range: the whole water column (bottom to `zeta`). Make the range a function argument (`zmin`, `zmax`) because this choice may change after seeing results.
- Mask land with `mask_rho`.
- Implementation: `analysis/pea.py` (`pea(ds, tidx, zmin, zmax)`), processed in eta-slabs (slab size is a parameter). Reuse the function, do not rewrite it.
- For precomputed files: see `processed-data`.

### Speed
- Interpolate `u` and `v` to rho points, then `speed = sqrt(u**2 + v**2)`.
- Speed is saved as the mean over a depth range; calculate the speed for each layer, then calculate the mean over the depth range. Thickness `H` stored so ranges can be combined.
- Matching range per run: semisub uses `0_25`; spar uses 0-130 m, i.e. `0_25` and `25_130` combined as `sum(speed_r * H_r) / sum(H_r)` (NaN where `H = 0` counts as zero weight; NaN if total `H` is 0). Combine per day, then average.

### Velocity
- Velocity refers to the vector (u, v).
- Velocity is saved as the mean over a depth range; calculate the mean of `u` and `v` individually over the depth range, then store as `ubar` and `vbar`. Do not rotate the vector when storing. Thickness `H` stored so ranges can be combined. To show east/north, rotate afterwards with `angle` (in the avg files, not the processed ones): `east = u cos(angle) - v sin(angle)`, `north = u sin(angle) + v cos(angle)`; the grid is rotated, so grid u/v are not east/north.

### Current 
- Refers to the combination of speed and velocity.
- Implementation: `analysis/current.py`. Land/missing `u`, `v` count as zero when interpolating to rho points; results are masked with `mask_rho`.

### Turbulence: TKE, GLS, dissipation
- `tke` and `gls` are on `s_w` in the raw `his` files (3-hourly snapshots; not in `avg` files or processed files). Precomputed daily depth-range means (`tke`, `gls`, `eps`, `H`): see `processed-data` (`analysis/turbulence.py`, `scripts/computations/make_turbulence.py`). `eps` there is the mean of `gls**1.5` per record. Check on the files: `gls_p=2, gls_m=1, gls_n=-0.67, gls_cmu0=0.527`, so `eps = c0^(3+p/n) psi^1.5 ≈ 0.99 psi^1.5`.
- Layer values: average the two bounding `s_w` interfaces to get a layer value, then depth-mean over the range weighted by `dz` (from `z_w`). Same depth ranges as other metrics; store `H` so ranges can be combined.
- **TKE**: `tke` in m2 s-2, saved as the depth-mean over a depth range (not the depth-integral).
- **GLS**: `gls` is the generic length-scale variable psi of the GEN closure. It is used as a turbulence metric directly.
- **Dissipation**: `epsilon = gls^(3/2)` for the GEN closure (m2 s-3). Note it is nonlinear: epsilon from the mean `gls` is not the mean of epsilon. Say which one is used when reporting.
- `tke` and `gls` are model scalars, so means are linear (see Anomalies); no per-timestamp computation is needed for them.

### Richardson number
Two definitions are used. Compute both from the 3-hourly `his` fields (`temp, salt, u, v`), not from daily `avg` means, which smooth out the shear and bias Ri high.
- **Gradient Ri**: `Ri = N2 / S2` on `s_w` interfaces, with `N2 = -(g/rho0) * d(rho)/dz` (density from `temp`, `salt`, see PEA) and `S2 = (du/dz)^2 + (dv/dz)^2` (`u`, `v` interpolated to rho points). Local; Ri < 0.25 is the instability criterion. Heavy-tailed and undefined where `S2 = 0`.
- **Bulk Ri**: `Ri_b = g * drho/rho0 * dz / (du^2 + dv^2)` with differences across a depth range (default 0-25 m and 25-130 m, top minus bottom of the range). One value per column; robust, good for maps, but depends on the range.
- Never average Ri arithmetically. Summarise as the mean of `log10(Ri)` and/or the fraction of time with Ri < 0.25. For anomalies, compare `N2` and `S2` (or the log/fraction summaries) rather than differencing Ri.

### Wind-farm means
- Farm masks: `<farm>` in `windfarm_masks.nc` (six farms: Nordavind_D, Nordavind_C, Nordvest_C, Sorvest_F, Vestavind_B, Vestavind_F; `<farm>_sectors` are for sector analysis). Daily farm mean = NaN-aware mean over mask cells (all cells weighted equally) of the daily field; slice to the mask bounding box before loading.

## Anomalies
- Response = run minus `wakeref`: `spar - wakeref`, `semisub - wakeref`, on identical timestamps.
- Fixed `s` levels sit at slightly different depths in the two runs where `zeta` differs: interpolate to fixed z if depth-sensitive.
- **Linear vs nonlinear:**
  - Linear quantities (e.g. `temp, salt, u, v, w, zeta, tke, gls`): mean of anomalies = anomaly of means, so the precomputed monthly mean files can be used: see `processed-data`.
  - Nonlinear quantities (speed, PEA, density, kinetic energy, dissipation from `gls`, Richardson number): compute per timestamp, difference, then average (if relevant). 


### TS diagrams (farm, monthly)
- `analysis/ts.py`, `scripts/computations/make_ts_farm.py` -> `ts_<farm>_<run>_<YYYY-MM>.nc` (default `<processed>/ts/`; `files/ts/` on the VM). Per farm cell on fixed depths (0-150 m, 5 m, layer centres; NaN below the seabed): potential temperature and practical salinity for wakeref (`*_ref` = `mean_wakeref`) and run (`*_run` = `mean_wakeref + anom_<run>`), and the anomaly `dtemp`, `dsalt` on wakeref depths (use these for differences; the mean file uses all timestamps, the anomaly matched days).
- Plot with `gsw` (SA, CT, sigma0). Plotting: `scripts/plotting/ts_farm_monthly.py` -> `figures/ts_farm/<farm>/ts_<run>_<YYYY-MM>.png` (one month per figure; TS overlay wakeref grey vs run coloured by depth with farm-mean profiles, and dT, dS, dsigma0 profiles with 10-90 % shading).
