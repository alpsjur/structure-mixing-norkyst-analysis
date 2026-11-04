---
name: metrics
description: Definitions and conventions for metrics in the wind-farm mixing analysis - potential energy anomaly (PEA), current speed, surface TKE, anomalies relative to wakeref, and response vs distance. Use when computing or plotting these quantities from Norkyst output.
---

# Metrics and methodological choices

Open data with the `norkyst-data` skill. These are the decisions for *how* to compute things.

## Potential energy anomaly (PEA)
- Definition: `PEA = (1/H) * integral_{-H}^{0} (rho_mean - rho) * g * z dz`, `rho_mean = (1/H) * integral rho dz`. Units J m-3. Higher = more stratified.
- Density from `temp` (potential temperature) and `salt` (practical salinity). ROMS runs with `NONLIN_EOS` (Jackett & McDougall 1995, `rho0 = 1025`). Using TEOS-10 (`gsw`) is accepted: small differences are OK for PEA. If using `gsw`, convert first (`SA = gsw.SA_from_SP`, `CT = gsw.CT_from_pt`) and use pressure from depth (`gsw.p_from_z`). Do not pass raw `temp`/`salt` to `gsw.rho`.
- **Default integration range: the whole water column** (bottom to `zeta`). Make the range a function argument (`zmin`, `zmax`) because this choice may change after seeing results.
- Layer thicknesses `dz` come from differences of `z_w` (computed from the ROMS vertical grid variables); do not weight levels equally.
- Mask land with `mask_rho`.
- Implementation: `analysis/pea.py` (`pea(ds, tidx, zmin, zmax)`), processed in eta-slabs only because the machine Copilot works on has ~15 GB RAM. The full analysis will run on HPC, where larger chunks (or dask) are fine. Reuse the function, do not rewrite it.
- Whole-column PEA is dominated by the deep ocean (up to ~4e4 J m-3 in the Norwegian Sea, but ~0 on the shelf where the wind farms are). Use a capped colour range (e.g. 99.5th percentile) for maps, or consider a depth-limited range. Open choice, see below.

## Current speed
- Interpolate `u` and `v` to rho points, then `speed = sqrt(u**2 + v**2)`.

## Structure parameters (per turbine)
| | Cylinders | Depth extent | Cylinder diameter |
|---|---|---|---|
| `semisub` | 4 | 25 m | 12.375 m |
| `spar` | 1 | 130 m | 20 m |

## Surface TKE
- `tke` is on `s_w` in `his` files only. Surface = top interface (last `s_w` index).

## Anomalies
- Response = run minus `wakeref`: `spar - wakeref`, `semisub - wakeref`, on identical timestamps.
- Plot anomalies with a diverging colormap centred on 0 and a symmetric colour range.
- Choose the range from a high percentile of `abs(anomaly)` (e.g. 99.9), not min/max: anomalies are localised around the wind farms, and a few extreme cells would otherwise hide everything else.

## Open questions (do not assume; ask the user)
- Response vs distance: how to define distance, and whether to use only downstream distance. "Downstream" definition is undecided (candidates: mean current direction).

