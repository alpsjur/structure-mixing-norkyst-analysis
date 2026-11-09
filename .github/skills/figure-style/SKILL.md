---
name: figure-style
description: Plotting conventions for the wind-farm mixing analysis - map figures (cartopy, cmocean, light gray land), anomaly colour scales, figure size, and output naming/format. Use when making or editing any figure of Norkyst output.
---

# Figure conventions

A working reference implementation is in [map_example.py](map_example.py). Start from it for any map.

## Maps
- `cartopy` with `cmocean` colormaps. Projection: `ccrs.NorthPolarStereo()` (data transform `ccrs.PlateCarree()`); use `pcolormesh` with `shading="auto"`.
- Always draw land as light gray (`cfeature.LAND`, `facecolor="lightgray"`) on top of the data (higher `zorder` than the field), plus `cfeature.COASTLINE` above that.
- Set the map extent from the projected grid corners (`ax.projection.transform_points` on `lon_rho`/`lat_rho`, then `set_extent(..., crs=ax.projection)`), so the map fits the model domain. For zoomed maps (e.g. around a wind farm) pass an explicit lon/lat box instead.
- Gridlines with labels on left/bottom only, dashed, gray, `alpha=0.5`, `linewidth=0.5`, `dms=True`.
- Vertical colorbar with a label that includes units.
- Always pass `rasterized=True` to `pcolormesh` on the full grid (about 3M cells); otherwise PDFs are ~90 MB. Coastlines and text stay vector.
- Cartopy downloads Natural Earth coastlines on first use, which needs internet. On HPC without internet, pre-download them or point `cartopy.config["data_dir"]` to a local copy.

## Wind farms on maps
Helpers `add_farm_outlines` and `add_turbines` are in [map_example.py](map_example.py).
- Farm outlines: the exact boundary of the masked rho cells as polygons (`farm_outline` builds a shapely union of the cell quadrilaterals, corners = mean of the four surrounding rho points; `ax.add_geometries(..., crs=ccrs.PlateCarree(), facecolor="none", edgecolor="black", linewidth=0.8, zorder=4)`), above land and coastline. Do not smooth the outline or use `ax.contour`.
- Individual turbines: `ax.scatter` at the actual turbine lon/lat from `~/structure-mixing-grid-utils/turbine_coordinates/*.txt` (not the snapped grid cells), small dots (`marker="."`), `s=2`, black, `zorder=5`. The marker size may need adjusting for strongly zoomed maps.
- Outlines and turbines can be used together or separately.

## Colormaps
- Bathymetry / depth: `cmo.deep`.
- PEA (full fields, not differences): `cmo.matter` on a log scale, `LogNorm(vmin=1, vmax=1000)` (J m-3) with `extend="both"`; PEA is ~0 or slightly negative (numerical noise) in mixed columns, so clip the data first (`da.clip(min=1)`), otherwise values <= 0 are masked and show as white holes. Use the same norm for all runs and months so maps are comparable. Pass `norm=` (not `vmin`/`vmax`) to `plot_map`.
- Other sequential fields (current speed, TKE): `cmocean` sequential, e.g. `cmo.thermal`, `cmo.haline`; not `deep` or `matter`, which are reserved for bathymetry and PEA.
- Anomalies (run minus `wakeref`): diverging map centred on 0 (`cmo.balance`) with a symmetric range (`vmin=-vmax`). Set `vmax` to the 99th percentile of `|anomaly|` (`np.nanpercentile(np.abs(a), 99)`), not the maximum, so a few extreme cells (eddies) do not wash out the pattern. Use a separate `vmax` per map (anomaly magnitude grows over time, so a shared scale makes early days look blank); use a shared `vmax` only when maps are meant to be compared in magnitude.

## Output
- Save to `figures/<subfolder>/` as PNG at 300 dpi and PDF (`save_fig` in `map_example.py` creates the folder). Subfolders by topic: `grid` (bathymetry, wind-farm layout), `pea` (potential energy anomaly); add new ones per variable/topic (e.g. `currents`, `tke`). No figures directly in `figures/`.
- Multi-panel maps: one `draw_map` per panel on `plt.subplots(..., subplot_kw={"projection": ccrs.NorthPolarStereo()})`; panels that show the same quantity on the same scale share one vertical colorbar (`fig.colorbar(pcm, ax=[ax1, ax2])`), a difference panel gets its own.
- Width 8 cm (single column) or 17 cm (double column) when the figure is for the paper; quick-look figures may be larger.
- Name: `<variable>_<run>_<period>.png`, e.g. `figures/pea/pea_spar_2022-07.png` (for 3-panel experiment / wakeref / difference figures); single-field maps as `<variable>_<run>_<period>`.

## Not yet decided
Fonts, wind-farm name labels on maps, panel labelling, and journal style. Ask the user rather than inventing.
