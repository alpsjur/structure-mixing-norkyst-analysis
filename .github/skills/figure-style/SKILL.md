---
name: figure-style
description: Plotting conventions for the wind-farm mixing analysis.
---

# Figure conventions
## Maps
- A working reference implementation is in [map_example.py](map_example.py). Start from it for any map.
- Use `cartopy` with `ccrs.NorthPolarStereo()` projection and `ccrs.PlateCarree()` data transform.
- Draw land as light gray (`cfeature.LAND`, `facecolor="lightgray"`) on top of the data (higher `zorder` than the field), plus `cfeature.COASTLINE` above that.
- Set the map extent from the projected grid corners (`ax.projection.transform_points` on `lon_rho`/`lat_rho`, then `set_extent(..., crs=ax.projection)`), so the map fits the model domain. For zoomed maps (e.g. around a wind farm) pass an explicit lon/lat box instead.
- Plot gridlines with labels on left/bottom only, dashed, gray, `alpha=0.5`, `linewidth=0.5`, `dms=True`.
- To plot fields, use `pcolormesh` with `cmocean` colormaps and `shading="auto"`.
- When relevant, use vertical colorbar with a label that includes units.
- Always pass `rasterized=True` to `pcolormesh` on the full grid (about 3M cells); otherwise PDFs are ~90 MB. Coastlines and text stay vector.

## Wind farms on maps
- Helpers `add_farm_outlines` and `add_turbines` are in [map_example.py](map_example.py).
- Farm outlines: the exact boundary of the masked rho cells as polygons (`farm_outline` builds a shapely union of the cell quadrilaterals, corners = mean of the four surrounding rho points; `ax.add_geometries(..., crs=ccrs.PlateCarree(), facecolor="none", edgecolor="black", linewidth=0.8, zorder=4)`), above land and coastline. Do not smooth the outline or use `ax.contour`.
- Individual turbines: `ax.scatter` at the actual turbine lon/lat from `~/structure-mixing-grid-utils/turbine_coordinates/*.txt` (not the snapped grid cells), small dots (`marker="."`), `s=2`, black, `zorder=5`. The marker size may need adjusting for strongly zoomed maps.
- Outlines and turbines can be used together or separately.

## Colormaps
- Bathymetry / depth: `cmo.deep`.
- PEA (full fields, not differences): `cmo.matter` on a log scale, `LogNorm(vmin=1, vmax=1000)` (J m-3) with `extend="both"`; PEA is ~0 or slightly negative (numerical noise) in mixed columns, so clip the data first (`da.clip(min=1)`), otherwise values <= 0 are masked and show as white holes. Use the same norm for all runs and months so maps are comparable. Pass `norm=` (not `vmin`/`vmax`) to `plot_map`.
- Other sequential fields (current speed, TKE): `cmocean` sequential, e.g. `cmo.thermal`, `cmo.haline`; not `deep` or `matter`, which are reserved for bathymetry and PEA.
- Anomalies (run minus `wakeref`): diverging map centred on 0 (e.g. `cmo.balance`) with a symmetric range (`vmin=-vmax`). Set `vmax` to the 99th percentile of `|anomaly|` (`np.nanpercentile(np.abs(a), 99)`), not the maximum, so a few extreme cells do not wash out the pattern. Use a separate `vmax` per map (anomaly magnitude grows over time, so a shared scale makes early days look blank); use a shared `vmax` only when maps are meant to be compared in magnitude.

## Output
- Save to `figures/<subfolder>/` as PNG at 300 dpi (`save_fig` in `map_example.py` creates the folder). Only save as PDF if specifically asked to (pass `PDF=True` to `save_fig` in `map_example.py`). 
- Use subfolders by topic: `grid` (bathymetry, wind-farm layout); `<variable>_map` and `<variable>_timeseries` for maps and farm time series, with one folder per PEA range (`pea_map`, `pea50_map`, `pea100_map`, `pea150_map`, `pea_timeseries`, `pea50_timeseries`, ..., `pea_comparison_map`) and `current_map`, `current_timeseries`; `scratch` (quick looks, the `plot_map` default); add new ones per variable/topic (e.g. `tke_map`). No figures directly in `figures/`.
- Multi-panel maps: one `draw_map` per panel on `plt.subplots(..., subplot_kw={"projection": ccrs.NorthPolarStereo()})`; panels that show the same quantity on the same scale share one vertical colorbar (`fig.colorbar(pcm, ax=[ax1, ax2])`), a difference panel gets its own.
- Name: `<variable>_<run>_<period>.png`, e.g. `figures/pea_map/pea_spar_2022-07.png`. Whole-period mean: `<variable>_<run>_whole.png`; first time step: `<variable>_<run>_first.png`. Anomalies: `<variable>_<run>-minus-wakeref_<period>.png`.


## Standard figure sets
- Map figures: 3 panels (run | wakeref | run - wakeref); run and wakeref share the colour scale and colorbar, the difference is taken per day then averaged. Monthly means are eddy-dominated, so also make whole-period means.
- Plot each run only over its own structure depth range for current speed: semisub 0-25 m, spar 0-130 m. 
- Farm time series (`scripts/plotting/*_farm_timeseries.py`): one row per wind farm (mask cells, daily mean), shared time axis; left column run and wakeref overlaid (grey = wakeref, blue = run), right column run - wakeref (red) with a zero line. Folders `<range>_timeseries`, `current_timeseries`.
