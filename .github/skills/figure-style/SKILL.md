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
- Sequential fields (PEA, current speed, TKE): `cmocean` sequential, e.g. `cmo.deep`, `cmo.thermal`, `cmo.haline`. Default `cmo.deep`.
- Anomalies (run minus `wakeref`): diverging map centred on 0 (`RdBu_r` or `cmo.balance`) with a symmetric range (`vmin=-vmax`).

## Output
- Save to `figures/` (create if missing) as PNG at 300 dpi and PDF.
- Width 8 cm (single column) or 17 cm (double column) when the figure is for the paper; quick-look figures may be larger.
- Name: `<variable>_<run>_<period>.png`, e.g. `pea_spar-minus-wakeref_2022-07.png`.

## Not yet decided
Fonts, wind-farm name labels on maps, panel labelling, and journal style. Ask the user rather than inventing.
