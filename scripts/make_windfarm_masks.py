"""Build rho-point wind farm masks split into sectors. Run from the repo root.

Turbines are matched to the nearest wet rho cell (as in structure-mixing-grid-utils).
Turbine cells are grouped into sectors by single-linkage clustering (cells closer than
LINK_CELLS are linked). Within each sector, binary closing (smallest size giving one
connected region) and hole filling make the sector cohesive. Stray turbine cells that closing
cannot join to a sector are dropped from the mask.
Output per farm: `<farm>` (0/1 union of sectors) and `<farm>_sectors` (labels 1..n, 0 outside).
"""
from pathlib import Path

import numpy as np
import xarray as xr
from scipy import ndimage
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.sparse.csgraph import minimum_spanning_tree
from scipy.spatial import cKDTree
from scipy.spatial.distance import cdist

UTILS = Path.home() / "structure-mixing-grid-utils"
GRID = UTILS / "grid_files" / "norkyst_grd_v31.nc"
TURBINES = UTILS / "turbine_coordinates"
OUT = Path("files/windfarm_masks.nc")
MAX_DIST_DEG = 0.1
LINK_CELLS = 5
MAX_CLOSING = 20
MAX_DROP = 2  # turbine cells per sector that may be dropped as strays
# The Nordavind file holds two sub-areas separated by a latitude gap (71.416-71.478).
SPLITS = {"Nordavind_CD": {"Nordavind_D": lambda xy: xy[:, 1] < 71.45,
                           "Nordavind_C": lambda xy: xy[:, 1] >= 71.45}}


def read_turbines(path):
    rows = [ln.split() for ln in path.read_text().splitlines()
            if ln.strip() and not ln.startswith("[")]
    return np.array([[float(a), float(b)] for a, b in rows])


def cohesive(cells):
    """Smallest closing (in cells) leaving one region, then fill holes.

    If closing cannot join a stray turbine cell, the stray is dropped: the largest region is kept
    once at most MAX_DROP turbine cells lie outside it. If that never happens (size -1 is
    returned), turbine cells are joined along a minimum spanning tree instead.
    """
    st = np.ones((3, 3))
    for size in range(MAX_CLOSING + 1):
        pad = size + 1
        padded = np.pad(cells, pad)
        closed = ndimage.binary_closing(padded, st, iterations=size) if size else padded
        filled = ndimage.binary_fill_holes(closed)[pad:-pad, pad:-pad]
        lab, n = ndimage.label(filled, st)
        sizes = ndimage.sum(cells, lab, range(1, n + 1))
        if cells.sum() - sizes.max() <= MAX_DROP:
            return lab == sizes.argmax() + 1, size, int(cells.sum() - sizes.max())
    return connect_mst(cells), -1, 0


def connect_mst(cells):
    """Join turbine cells with straight lines of cells along their minimum spanning tree,
    widened by 1 cell.

    Used for sectors where closing fails, e.g. a line of turbines.
    """
    ij = np.argwhere(cells)
    mst = minimum_spanning_tree(cdist(ij, ij)).tocoo()
    out = cells.copy()
    for a, b in zip(mst.row, mst.col):
        n = int(np.abs(ij[a] - ij[b]).max()) + 1
        line = np.rint(np.linspace(ij[a], ij[b], n)).astype(int)
        out[line[:, 0], line[:, 1]] = True
    return ndimage.binary_fill_holes(ndimage.binary_dilation(out, np.ones((3, 3))))


grid = xr.open_dataset(GRID)
lon, lat, wet = grid.lon_rho.values, grid.lat_rho.values, grid.mask_rho.values > 0
eta_w, xi_w = np.nonzero(wet)
tree = cKDTree(np.column_stack([lon[eta_w, xi_w], lat[eta_w, xi_w]]))

masks = {}
for path in sorted(TURBINES.glob("*.txt")):
    file_name = path.stem.removeprefix("windfarms_")
    all_xy = read_turbines(path)
    if file_name in SPLITS:
        groups = {n: all_xy[sel(all_xy)] for n, sel in SPLITS[file_name].items()}
    else:
        groups = {file_name: all_xy}
    for name, xy in groups.items():
        dist, idx = tree.query(xy)
        if (dist > MAX_DIST_DEG).any():
            raise RuntimeError(f"{name}: turbine farther than {MAX_DIST_DEG} deg from a wet cell")
        cells = np.zeros(wet.shape, bool)
        cells[eta_w[idx], xi_w[idx]] = True
        ij = np.argwhere(cells)
        cluster = fcluster(linkage(ij, "single"), LINK_CELLS, "distance")
        order = np.argsort([ij[cluster == c].mean(axis=0) @ [1e4, 1] for c in np.unique(cluster)])
        sectors = np.zeros(wet.shape, "int8")
        sizes = []
        n_dropped = 0
        for label, c in enumerate(np.unique(cluster)[order], start=1):
            sector = np.zeros(wet.shape, bool)
            sector[tuple(ij[cluster == c].T)] = True
            sector, size, dropped = cohesive(sector)
            n_dropped += dropped
            if (sectors[sector] > 0).any():
                raise RuntimeError(f"{name}: sector {label} overlaps another sector")
            sectors[sector] = label
            sizes.append(size)
        masks[name] = xr.DataArray(
            (sectors > 0).astype("int8"), dims=("eta_rho", "xi_rho"),
            attrs={"long_name": f"Wind farm {name} mask (1 = inside any sector)",
                   "n_turbines": len(xy), "n_sectors": len(sizes),
                   "n_turbines_dropped": n_dropped})
        masks[f"{name}_sectors"] = xr.DataArray(
            sectors, dims=("eta_rho", "xi_rho"),
            attrs={"long_name": f"Wind farm {name} sector labels (0 outside)",
                   "closing_cells": sizes,
                   "closing_note": "-1 = no closing, cells joined by minimum spanning tree lines", "link_cells": LINK_CELLS,
                   "sector_order": "south to north (mean eta), then by xi"})
        print(f"{name}: {len(xy)} turbines, {len(sizes)} sectors, "
              f"cells per sector {[int((sectors == i).sum()) for i in range(1, len(sizes) + 1)]}, "
              f"closing {sizes}, dropped {n_dropped}, on land: {int(((sectors > 0) & ~wet).sum())}")

ds = xr.Dataset(masks, coords={"lon_rho": grid.lon_rho, "lat_rho": grid.lat_rho})
ds.attrs["description"] = "Wind farm masks (sectors, closed and hole-filled) on the Norkyst rho grid (norkyst_grd_v31.nc)"
OUT.parent.mkdir(exist_ok=True)
ds.to_netcdf(OUT, encoding={v: {"zlib": True, "complevel": 4} for v in ds.data_vars})
print("wrote", OUT)
