# Documentation of structure-mixing experiments with Norkyst
**Contact**: Anna Lina Sjur, anna.l.sjur@met.no

## 1. Overview

This document describe output from three Norkyst ROMS simulations designed to quantify how the foundations of floating offshore wind turbines mix the ocean.  

The simulated period is **2 February – 31 August 2022 (211 days)**. Six planned wind farms are included (Figure 1).

<img src="../figures/grid/domain_windfarms.png" alt="Model domain" width="82%">

*Figure 1: Model domain, bathymetry and the six wind farms included in the experiments.*

## 2. Experiments
Experiemnts for two types of floating foundations are included:
- **Spar**: a single cylinder with a deep draft (130 m). 
- **Semisubmersible (semisub)**: a platform with several shorter columns with a shallower draft (25 m).

In addition to the two runs with turbine foundations, a reference run without ocean mixing from foundations is included. All runs include the atmospheric wake of the wind farms in the surface forcing. 


This gives the following set of experiments:
| Run | Atmospheric wake | Ocean mixing parametrization | Turbine foundation |
|---|---|---|---|
| `wakeref` | yes | no | – |
| `spar` | yes | yes | 1 cylinder, 20 m diameter, 130 m deep |
| `semisub` | yes | yes | 4 cylinders, 12.375 m diameter each, 25 m deep |

Note that Sørvest F is shallower than the spar depth. In the `spar` experiment, foundations in Sørvest F are thus modeled as extending all the way to the seafloor, efficiently representing monopile foundations. 

### Ocean mixing parametrization
The ocean mixing parametrization is based on Rennau et al. (2012), extended to the GLS closure.
Foundations are modeled as vertical cylinders. In grid cells where foundations are present they (1) exert a drag on the flow, and (2) the kinetic energy removed from the mean flow is added to the GLS turbulence closure as extra turbulent kinetic energy and mixing. The drag coefficient is `STR_CD = 0.63` (as in Rennau et al., 2012) and the GLS closure coefficient is `GLS_C4 = 0.45` (moderate mixing). The full description of the parametrization can be found in
[README_STRUCTURE_MIXING.md](https://github.com/alpsjur/roms/blob/structure-mixing/README_STRUCTURE_MIXING.md).

The main difference between the two types of foundations, as represented in the parametrization, is their horizontal and vertical extent. The semisubmerible has a larger frontal width per turbine, so it adds stronger drag and mixing, but only in the upper 25 m. The spar has a smaller frontal width but reaches much deeper, affecting a larger part of the water column. 

*Rennau, H., Schimmels, S. & Burchard, H. (2012). On the effect of structure-induced turbulence and mixing on the stratification in the vicinity of offshore wind farm foundations. Coastal Engineering, 60, 53–68.*

## 3. Data access and files

Catalog: <https://thredds.met.no/thredds/catalog/havvind/structure_mixing/catalog.html>

Each run has its own folder (`wakeref`, `spar`, `semisub`). In each folder, you can find the following files:

| File | Content | Time resolution | 
|---|---|---|
| `norkyst_avg_NNNN.nc` | one daily mean per file, time-stamped 12:00 | daily mean | 
| `norkyst_his_NNNN.nc` | 3-hourly snapshots; file 0001 has 9 records (00:00 on 2 Feb to 00:00 on 3 Feb), later files have 8 (03:00 to 24:00) | 3-hourly | 
| `norkyst_rst.nc` | model restart file | 4 days | 

`NNNN` is the day number (0001 = 2 February 2022, 0211 = 31 August 2022).

The files contain the following variables:

| Variable | Description | Unit | In `avg` | In `his` |
|---|---|---|:-:|:-:|
| `u`, `v` | horizontal velocity components (grid-aligned) | m s⁻¹ | ✓ | ✓ |
| `ubar`, `vbar` | depth-averaged velocity | m s⁻¹ | ✓ | ✓ |
| `w` | vertical velocity | m s⁻¹ | ✓ | ✓ |
| `omega` | S-coordinate vertical velocity | m³ s⁻¹ | ✓ | |
| `temp` | potential temperature | °C | ✓ | ✓ |
| `salt` | salinity | – | ✓ | ✓ |
| `zeta` | sea surface height | m | ✓ | ✓ |
| `AKs` | vertical diffusion coefficient for salinity | m² s⁻¹ | | ✓ |
| `tke` | turbulent kinetic energy | m² s⁻² | | ✓ |
| `gls` | turbulent generic length scale | m³ s⁻² | | ✓ |
| `Uwind`, `Vwind` | surface wind components | m s⁻¹ | | ✓ |


---


