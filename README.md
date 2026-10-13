# Staten Island Tax Lot & Building Footprint Analysis

A geospatial audit and analysis pipeline cross-referencing New York City's **MapPLUTO (26v2)** tax lot records with official **Building Footprints (5zhs-2jue)** from NYC Open Data / OTI for Staten Island (Richmond County).

---

## Overview

Tax lot assessment data in MapPLUTO provides recorded gross building floor area (`BldgArea`) and the number of stories (`NumFloors`). Photogrammetric building footprints provide actual, measured building footprints on the ground.

This project calculates the volumetric floor-area-to-footprint ratio:
$$\text{Ratio} = \frac{\text{Footprint Area} \times \text{NumFloors}}{\text{BldgArea}}$$

And its logarithmic transformation $\ln(\text{Ratio})$ to detect:
* **Extreme Under-ratios ($\ll 1.0$)**: Subterranean/mezzanine spaces or severely over-reported gross building area in tax records.
* **Extreme Over-ratios ($\gg 1.0$)**: Unrecorded additions, large structures assessed at nominal square footage, or mismatching lot identifiers.

---

## Methodology & Filter Criteria

To eliminate false discrepancy flags from multi-structure properties (e.g. lots containing both a primary residence and detached garages/sheds, where `NumFloors` only counts the tallest building), the analysis filters strictly to **clean 1:1 single-building lots**:
1. `NumBldgs == 1`
2. `NumFloors > 0`
3. `BldgArea > 0`
4. Exactly one building footprint polygon matching the lot's 10-digit BBL.

On Staten Island, this yields an analytical cohort of **96,565 single-building tax lots** (76.8% of all lots).

---

## Key Results & Distribution

* **1st Percentile**: `0.6115`
* **5th Percentile**: `0.7526`
* **25th Percentile**: `1.0549`
* **50th Percentile (Median)**: **`1.1947`**
* **75th Percentile**: `1.3884`
* **95th Percentile**: `1.8714`
* **99th Percentile**: `2.3887`

The median ratio sits at **~1.19** because photogrammetric footprints capture exterior rooflines, overhangs, and unenclosed porches that are excluded from interior taxable gross floor area (`BldgArea`), and upper floors frequently feature setbacks smaller than the ground footprint.

---

## Deliverables

* [`DATA_SOURCES.md`](DATA_SOURCES.md): Full provenance, download URLs, versions (`26v2`), and SODA API queries.
* `data/ratio_results.csv`: Complete calculated dataset across all 96,565 matched lots.
* `data/review_sheet.csv`: 30-lot review sheet isolating the 15 lowest and 15 highest ratio extremes.
* `data/flagged_lots.gpkg`: Multi-layer GeoPackage containing both tax lot and footprint geometries for the 30 flagged parcels.

---

## Setup & Execution

### 1. Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Run Pipeline
```powershell
python pipeline.py
```