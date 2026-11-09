---
name: metrics
description: Definitions and conventions for metrics in the wind-farm mixing analysis - potential energy anomaly (PEA), current speed, surface TKE, anomalies relative to wakeref, and response vs distance. Use when computing or plotting these quantities from Norkyst output.
---

# Metrics and methodological choices

Open data with the `norkyst-data` skill; precomputed files are in `processed-data`. These are the decisions for *how* to compute things.

## Potential energy anomaly (PEA)
- Definition: `PEA = (1/H) * integral_{-H}^{0} (rho_mean - rho) * g * z dz`, `rho_mean = (1/H) * integral rho dz`. Units J m-3. Higher = more stratified.
- Density from `temp` (potential temperature) and `salt` (practical salinity). ROMS runs with `NONLIN_EOS` (Jackett & McDougall 1995, `rho0 = 1025`). Using TEOS-10 (`gsw`) is accepted: small differences are OK for PEA. If using `gsw`, convert first (`SA = gsw.SA_from_SP`, `CT = gsw.CT_from_pt`) and use pressure from rho-level depth (`gsw.p_from_z`) only for the `SA` conversion. Evaluate density at the surface pressure (`gsw.rho(SA, CT, 0)`, potential density), otherwise compressibility gives a mixed column a nonzero PEA that grows with depth. Do not pass raw `temp`/`salt` to `gsw.rho`.
- Default integration range: the whole water column (bottom to `zeta`). Make the range a function argument (`zmin`, `zmax`) because this choice may change after seeing results.
- Layer thicknesses `dz` come from differences of `z_w` (computed from the ROMS vertical grid variables); do not weight levels equally.
- Mask land with `mask_rho`.
- Implementation: `analysis/pea.py` (`pea(ds, tidx, zmin, zmax)`), processed in eta-slabs only because the machine Copilot works on has ~15 GB RAM. The full analysis will run on HPC, where larger chunks (or dask) are fine. Reuse the function, do not rewrite it.
- Precomputed files: see `processed-data`.

## Current speed
- Interpolate `u` and `v` to rho points, then `speed = sqrt(u**2 + v**2)`.

## Surface TKE
- `tke` is on `s_w` in `his` files only. Surface = top interface (last `s_w` index).

## Anomalies
- Response = run minus `wakeref`: `spar - wakeref`, `semisub - wakeref`, on identical timestamps.
- **Linear vs nonlinear:**
  - Linear quantities (`temp, salt, u, v, w, zeta`): mean of daily anomalies = anomaly of means, so the precomputed monthly anomalies are exact. Fixed `s` levels sit at slightly different depths in the two runs where `zeta` differs: interpolate to fixed z if depth-sensitive.
  - Nonlinear quantities (speed, PEA, density, kinetic energy, TKE magnitude): compute per timestamp, difference, then average. 

