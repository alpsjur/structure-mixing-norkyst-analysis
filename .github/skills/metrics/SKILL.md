---
name: metrics
description: Definitions and conventions for metrics and calculaitons in the wind-farm mixing analysis.
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
- Standard definition: `PEA = (1/H) * integral_{-H}^{0} (rho_mean - rho) * g * z dz`, `rho_mean = (1/H) * integral rho dz`. Units J m-3. Higher = more stratified.
- Use density calculated from `temp` (potential temperature) and `salt` (practical salinity). ROMS runs with `NONLIN_EOS` (Jackett & McDougall 1995, `rho0 = 1025`). Using TEOS-10 (`gsw`) is accepted: small differences are OK for PEA. If using `gsw`, convert first (`SA = gsw.SA_from_SP`, `CT = gsw.CT_from_pt`) and use pressure from rho-level depth (`gsw.p_from_z`) only for the `SA` conversion. Evaluate density at the surface pressure (`gsw.rho(SA, CT, 0)`, potential density), otherwise compressibility gives a mixed column a nonzero PEA that grows with depth. Do not pass raw `temp`/`salt` to `gsw.rho`.
- Default integration range: the whole water column (bottom to `zeta`). Make the range a function argument (`zmin`, `zmax`) because this choice may change after seeing results.
- Mask land with `mask_rho`.
- Implementation: `analysis/pea.py` (`pea(ds, tidx, zmin, zmax)`), processed in eta-slabs only because the machine Copilot works on has ~15 GB RAM. The full analysis will run on HPC, where larger chunks (or dask) are fine. Reuse the function, do not rewrite it.
- For precomputed files: see `processed-data`.

### Speed
- Interpolate `u` and `v` to rho points, then `speed = sqrt(u**2 + v**2)`.
- Speed is normaly saved as the mean over a depth range; calculate the speed for each layer, then calculate the mean over the depth range. Thickness `H` stored so ranges can be combined. 

### Velocity
- Velocity refers to the vector (u, v).
- Velocity is normaly saved as the mean over a depth range; calculate the mean of `u` and `v` individually over the depth range, then store as `ubar` and `vbar`. Do not rotate the vector. Thickness `H` stored so ranges can be combined. 

### TKE
- `tke` is on `s_w` in the raw `his` files.

## Anomalies
- Response = run minus `wakeref`: `spar - wakeref`, `semisub - wakeref`, on identical timestamps.
- Fixed `s` levels sit at slightly different depths in the two runs where `zeta` differs: interpolate to fixed z if depth-sensitive.
- **Linear vs nonlinear:**
  - Linear quantities (`temp, salt, u, v, w, zeta`): mean of anomalies = anomaly of means, so the precomputed monthly mean files can be used: see `processed-data`.
  - Nonlinear quantities (speed, PEA, density, kinetic energy, TKE magnitude): compute per timestamp, difference, then average (if relevant). 

