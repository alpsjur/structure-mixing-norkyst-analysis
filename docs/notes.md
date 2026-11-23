# Research notes: isolating the wind-farm mixing signal from chaotic variability

Working notes on methodology for detecting a robust `run - wakeref` response, as distinct
from chaotic (unforced) variability between the runs. Dated entries, most recent last.

## 2026-11-20: farm-only averaging is noise dominated; considering farm + downstream averaging

**Problem**: Daily `run - wakeref` differences (PEA, speed, ...) averaged over the wind-farm
mask alone are dominated by chaotic variability, not a clear wind-farm-mixing signature.
Likely cause: the mixing signal is advected away from the farm by the mean current, so
farm-only averaging (a) misses signal that has already left the footprint and (b) includes
upstream farm cells that see no signal yet.

**Proposed approach**: average over an area combining the farm footprint and the water mass
advected downstream, based on the mean current, for a few more days. Keep some time
resolution (not a single full-period average) to track how the response develops as
stratification builds up over the season.

**First step**: before building the downstream mask, checked how stable the farm-mean
current direction is across the simulated period, since a fixed downstream shape depends on
this being roughly consistent in time.

### Check: monthly-mean current direction per farm (0-25 m, wakeref, Feb-Aug 2022)

Computed from `processed/current/current_wakeref_<YYYY-MM>.nc`, `ubar_0_25`/`vbar_0_25`
averaged over each farm mask, rotated to east/north with the grid `angle`. Circular mean and
circular standard deviation of the resulting monthly direction ("towards", degrees from
north, clockwise) across the 7 months:

| Farm | Mean direction | Circular std | Mean speed range (m/s) |
|---|---|---|---|
| Nordavind_C | 129 deg | 3 deg | 0.04-0.13 |
| Vestavind_B | 352 deg | 10 deg | 0.05-0.10 |
| Vestavind_F | 14 deg | 11 deg | 0.06-0.22 |
| Nordavind_D | 104 deg | 15 deg | 0.02-0.08 |
| Nordvest_C | 48 deg | 21 deg | 0.01-0.12 |
| Sorvest_F | 44 deg | 27 deg | 0.004-0.06 |

(Script: `/tmp/opencode/check_current_direction.py`, not committed; rerun from
`processed/current/` if needed.)

**Interpretation**:
- 4 of 6 farms (Nordavind_C, Vestavind_B, Vestavind_F, Nordavind_D) have a fairly stable
  monthly-mean current direction (circular std <= 15 deg) despite the large seasonal range in
  speed. A single fixed downstream direction per farm looks reasonable for these.
- Nordvest_C and Sorvest_F have the weakest currents (down to 0.004-0.06 m/s) and the most
  directional spread (20-27 deg; Sorvest_F direction even wraps through 0/360 deg in July).
  This looks like a weakly-advective regime (tidal/wind-residual dominated) without a
  persistent "downstream". A fixed downstream corridor is riskier here; may need a wider
  cone, a per-month direction, or to fall back to farm-only averaging for these two farms.
- Speed varies a lot seasonally (up to 10-20x between the weakest and strongest months for
  some farms), which matters for sizing the corridor *length*: a fixed physical distance
  won't correspond to a fixed advection/residence time across the season. Consider sizing
  length from speed x a chosen number of days rather than a fixed km value, varying it
  through the season if time resolution allows.
- Caveat: this is monthly-mean current, so daily/synoptic variability is already smoothed
  out; the true instantaneous directional spread (relevant for how much a single downstream
  shape can capture on any given day) is larger than these numbers suggest.

**Next step**: decide on the shape (corridor vs. cone), width, and length of the downstream
extension, and whether/how to treat Nordvest_C and Sorvest_F differently.

## 2026-11-20: downstream mask design decisions

Decided on the following design for the farm + downstream averaging region, to be
implemented as a new mask (parallel to `windfarm_masks.nc`):

- **Shape**: fixed-width corridor (parallel-sided strip), not a widening cone or soft
  Gaussian weighting. Simpler, reproducible, easy to explain; roughly constant cell count
  along its length.
- **Origin**: one corridor per farm, projected from the farm's bounding box/footprint as a
  whole (not per sector), oriented along the farm's annual-mean current direction (0-25 m,
  wakeref; see circular means above). Multi-sector farms (e.g. Vestavind_F) are treated as
  one shape.
- **Length**: fixed physical distance for all farms, default **15 km**, to be refined later
  if needed. Tried to calibrate this empirically from the `run - wakeref` anomaly fields
  (PEA/speed), but these are too noisy on their own to pick out a clear decorrelation
  distance; a round-number default is used instead for now.
- **Width**: farm's own cross-stream extent (bounding-box dimension perpendicular to the
  corridor direction) plus a fixed margin, so wider farms get a wider corridor rather than
  one fixed width for all.
- **Weak/directionally-unstable farms (Nordvest_C, Sorvest_F)**: no directional corridor,
  since the monthly-mean current direction is not stable enough (circular std 20-27 deg,
  Sorvest_F direction even wraps through 0/360 deg) to justify one fixed direction. Instead,
  use an isotropic circular buffer around the farm footprint, with radius equal to the same
  15 km default used for the other farms' corridor length, so the "extra distance sampled
  beyond the farm edge" is comparable across all six farms.
- The original farm mask is always included; the corridor/circle is a downstream/surrounding
  *extension*, unioned with the farm mask, not a replacement for it.

**Next step**: implement `make_windfarm_downstream_masks.py` (parallel to
`make_windfarm_masks.py`) using these parameters, writing a new mask file (or new variables
in a copy of `windfarm_masks.nc`) with the corridor direction, length, and width (or circle
radius) recorded as attributes per farm.

## 2026-11-20: checked whether current direction changes with depth (0-25 m vs 25-130 m)

Spar foundations affect the water column down to 130 m, so checked whether the corridor
direction chosen from the 0-25 m current (relevant for semisub) still holds for the deeper
25-130 m range (relevant for spar), using the same monthly wakeref current files.

| Farm | 0-25 m dir (std) | 25-130 m dir (std) | difference |
|---|---|---|---|
| Nordavind_C | 129 deg (3 deg) | 129 deg (5 deg) | -0.5 deg |
| Vestavind_F | 14 deg (11 deg) | 12 deg (7 deg) | 2 deg |
| Vestavind_B | 352 deg (10 deg) | 349 deg (9 deg) | 3 deg |
| Nordavind_D | 104 deg (15 deg) | 98 deg (7 deg) | 6 deg |
| Sorvest_F | 44 deg (27 deg) | 29 deg (30 deg) | 15 deg |
| Nordvest_C | 48 deg (21 deg) | 33 deg (10 deg) | 15 deg |

(Script: `/tmp/opencode/check_current_direction_deep.py`, not committed.)

**Conclusion**: for the 4 directional farms, direction is essentially depth-independent
(<= 6 deg difference, 25-130 m often *more* stable than 0-25 m) -> a single corridor
direction per farm is fine, no need for separate semisub/spar corridors. Nordvest_C and
Sorvest_F shift direction by ~15 deg with depth, on top of already being the most
directionally unstable farms at any single depth -> reinforces (does not change) the
decision to use an isotropic circular buffer for these two regardless of structure type.
No change to the design from the previous entry.

## 2026-11-20: implemented the downstream masks

Implemented the design above:
- `analysis/downstream.py`: `farm_mean_direction` (circular-mean current direction per farm
  from `current_wakeref_<YYYY-MM>.nc`, weighted by each month's `n_days`), `corridor_mask`
  and `circle_mask` (both via a local equirectangular tangent-plane projection around the
  farm centroid, accurate to a few tens of km, which is enough for a 15 km extension).
- `scripts/computations/make_windfarm_downstream_masks.py`: builds `<farm>_extension`
  (corridor/circle only) and `<farm>_extended` (farm union extension) for all six farms, with
  direction/shape/length/width recorded as attributes. Writes
  `files/windfarm_downstream_masks.nc` (`OUT` can be changed for the Lustre `masks/` folder
  on the HPC once finalised). Parameters: `DOWNSTREAM_KM=15`, `MARGIN_KM=5`,
  `DIRECTION_RANGE="0_25"`, `WEAK_FARMS={"Nordvest_C", "Sorvest_F"}`.

Resulting cell counts (farm cells / extension cells): Nordavind_D 851/1332, Nordavind_C
950/752, Nordvest_C 2102/6831 (circle), Sorvest_F 2236/7488 (circle), Vestavind_B 1904/1338,
Vestavind_F 1213/1272.

Visually checked (zoomed maps, not saved under version control): Vestavind_F's corridor
correctly extends north-northeast from the farm's downstream edge, with width spanning the
full farm (all 5 sectors); Nordvest_C's circle gives the expected rounded-square buffer
around its blocky 4-sector footprint.

**Next step**: use `<farm>_extended` masks in the farm-mean time series scripts (alongside
the existing `<farm>` masks) to see whether `run - wakeref` anomalies are less
noise-dominated when averaged over farm + downstream vs. farm alone.

## 2026-11-20: comparison scripts and a sanity-check map

Added `scripts/plotting/pea_downstream_comparison_timeseries.py` and
`scripts/plotting/current_downstream_comparison_timeseries.py`: same farm-mean daily
anomaly (`run - wakeref`) as the existing farm time series scripts, but overlaying
farm-only (gray) vs. farm+downstream-extension (red) averaging in one panel per farm, to
compare noise levels directly. Output alongside the existing farm time series
(`figures/<range>_timeseries/pea_<run>_downstream_comparison.png`,
`figures/current_timeseries/current_<run>_downstream_comparison.png`).

Also added `scripts/plotting/windfarm_downstream_map.py`: 6-panel map (one per farm, zoomed
to the farm+extension bounding box) of the whole-period mean current (0-25 m, wakeref,
background + quiver) with the farm mask (black outline) and farm+extension (red outline)
overlaid -> `figures/grid/windfarm_downstream_masks.png`. Visually confirms the corridors
point the right way (arrows align with the red corridor's long axis for the 4 directional
farms) and that Nordvest_C/Sorvest_F have visibly more rotational/incoherent flow (e.g. an
eddy-like turning pattern over Sorvest_F), supporting the isotropic-buffer choice for those
two.

**Next step**: look at the comparison time series across more farms/ranges/runs to judge
whether farm+downstream averaging meaningfully reduces chaotic noise relative to the
wind-farm-mixing signal, and whether DOWNSTREAM_KM/MARGIN_KM need adjusting.

## 2026-11-20: bug found and fixed - corridor must be built per sector, not per whole farm

Visual inspection of `windfarm_downstream_masks.png` (with the big current-direction arrows
added for diagnosis) showed the red corridor often did not even touch the black farm mask for
the 4 directional farms (e.g. Nordavind_D, Vestavind_B). Cause: the corridor was built once
per *whole farm* (union of all its sectors), starting at the farm-wide downstream edge
(`s_farm.max()`). Multi-sector farms (Nordavind_D: 2 sectors, Nordavind_C: 2, Vestavind_B: 4,
Vestavind_F: 5) have sectors spread out along the flow direction, so a corridor starting
beyond the single farthest-downstream sector left a gap for every other sector. Nordvest_C
and Sorvest_F (circle shape) were unaffected, since an isotropic buffer around the whole farm
footprint cannot produce this kind of gap.

**Fix**: `analysis/downstream.py` `corridor_mask` now starts at the centroid of whatever mask
it is given (so `s=0` is the centroid, corridor spans `s in [0, length_km]`), and
`scripts/computations/make_windfarm_downstream_masks.py` calls it once per *sector*
(`<farm>_sectors` labels from `windfarm_masks.nc`), each with its own current direction
(same circular-mean-over-months method, now computed per sector) and its own cross-stream
width. The farm's `<farm>_extension` is the union of its sectors' corridors (circle farms
unchanged: one circle for the whole farm). Re-ran and re-plotted
(`windfarm_downstream_map.py`, now with one big diagnostic arrow per sector, read back from
the `sector_direction_deg` attribute) - every sector's corridor now visibly starts at and
touches its own sector, aligned with the local current arrow.

One new observation: individual sector directions can differ substantially from each other
within the same farm, e.g. Vestavind_B's 4 sectors are 18, 345, 84, 337 deg (the 84 deg
sector has the lowest speed of the four, 0.033 m/s) - worth keeping in mind if a single
farm-level corridor direction is ever needed instead of per-sector.

**Next step**: re-run `pea_downstream_comparison_timeseries.py` and
`current_downstream_comparison_timeseries.py` with the corrected masks and re-assess the
farm-only vs. farm+downstream noise comparison.

## 2026-11-20: unified direction-averaging method; length increased to 60 km

Two follow-up changes:
- The big diagnostic arrows (direction used to build each corridor/circle) looked slightly
  rotated relative to the background quiver for some sectors (e.g. Nordavind_C). Cause: the
  arrows used a circular mean of unit vectors (direction only, ignoring speed), while the
  background quiver/speed map used a direct vector mean of (u, v) (speed-weighted). These are
  different statistics and can disagree when speed varies a lot across months. Changed
  `farm_mean_direction` in `analysis/downstream.py` to use the same vector-mean method as the
  background map (mean of u, v directly, weighted by `n_days`, then direction/speed from that
  mean vector), so the corridor direction always matches the plotted mean current by
  construction. Re-running showed the directions barely changed (e.g. Nordavind_C: 142.7 ->
  142.1 deg, 117.4 -> 117.2 deg) - the remaining small visual "rotation" is real small-scale
  spatial variability in the current field (quiver arrows a few cells away from the farm can
  reasonably point slightly differently than the farm-cell average), not a method artifact.
- `DOWNSTREAM_KM` increased from 15 to 60 km on request, corridors/circles are now
  correspondingly much larger (e.g. Nordavind_D extension 1197 -> 5041 cells, Nordvest_C
  circle 6831 -> 34634 cells).

**New issue noticed**: at 60 km, Nordvest_C's circular buffer now reaches the coastline/fjords
near 63-64 N (masked out by the wet-cell filter, so not wrong, but the usable ocean area
within the circle becomes asymmetric - less area available toward the coast than offshore).
Worth keeping in mind if Nordvest_C's averaging looks odd later.

**Next step**: re-run the farm-only vs. farm+downstream comparison time series with the
corrected, longer masks.

## 2026-11-20: re-ran the comparison time series with the corrected, 60 km masks

Re-ran `pea_downstream_comparison_timeseries.py` (pea, pea50, pea100, pea150) and
`current_downstream_comparison_timeseries.py` (semisub, spar) with the fixed per-sector,
60 km masks.

Result is much clearer than the first (buggy-mask) attempt: in nearly every farm/range/run
panel, the farm+downstream series (red) is visibly smoother than the farm-only series (gray)
- the sharp day-to-day spikes present in farm-only averaging are mostly suppressed. Most
notable:
- Nordvest_C PEA (pea150): farm-only swings roughly -100 to +30 J/m3 around Jul-Aug; farm+
  downstream stays within about +-20 J/m3.
- Sorvest_F (current and PEA): farm-only is unstructured scatter around zero; farm+downstream
  shows some sustained features (e.g. a dip in April, a rise after July) that look more like a
  real slowly-varying signal than noise - though this needs checking against the actual
  mixing-parametrization signal before reading too much into it (circular-buffer averaging
  over a much larger/less current-coherent area could also just be smoothing by brute averaging
  over more cells, independent of whether the extra cells are dynamically "downstream").
- Nordavind_D/C: farm+downstream clearly damps the sharpest spikes (e.g. Nordavind_C's
  ~-0.11 m/s early-March current-speed spike is reduced to about -0.05 m/s).

This supports the core hypothesis that farm+downstream averaging reduces chaotic noise
relative to farm-only averaging. Not yet checked: whether the *signal* (the part attributable
to the mixing parametrization, as opposed to just reduced sampling variance from averaging
over more cells) is preserved or diluted by the larger area - that requires a proper
signal-to-noise analysis, not just a visual noise-level comparison.

**Next step**: quantify signal-to-noise (e.g. mean anomaly over some reference period vs. its
own day-to-day scatter) for farm-only vs. farm+downstream, rather than relying on visual
smoothness alone, to confirm the extra averaging is not simply diluting a real signal that
happens to be concentrated near the farm.
