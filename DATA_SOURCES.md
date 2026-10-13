# Data Sources

This document records the provenance, download dates, versions, and metadata for datasets used in this project.

---

## 1. MapPLUTO (Tax Lots & Attributes)

* **Source Agency**: New York City Department of City Planning (DCP) — *BYTES of the BIG APPLE*
* **Dataset Name**: MapPLUTO (Shoreline Clipped)
* **Dataset Version**: `26v2` (August 2026 release)
* **Download Date**: October 13, 2026
* **Download URLs**:
  * Shapefile Package: `https://s-media.nyc.gov/agencies/dcp/assets/files/zip/data-tools/bytes/mappluto/nyc_mappluto_26v2_shp.zip`
  * Data Dictionary PDF: `https://s-media.nyc.gov/agencies/dcp/assets/files/pdf/data-tools/bytes/pluto_datadictionary.pdf`
  * Readme PDF: `https://s-media.nyc.gov/agencies/dcp/assets/files/pdf/data-tools/bytes/pluto_readme.pdf`
* **Local Storage**:
  * **Raw Archive (untouched)**: `data/raw/nyc_mappluto_26v2_shp.zip` (145.53 MB / 152.6 MB uncompressed)
  * **Data Dictionary**: `data/pluto_datadictionary.pdf` (580 KB)
  * **Processed Staten Island Layer**: `data/staten_island_mappluto.gpkg` (Layer: `staten_island_mappluto`)
* **Staten Island Dataset Specifications**:
  * **Filter Applied**: `Borough == 'SI'`
  * **Row Count**: 125,709 tax lots
  * **CRS**: `EPSG:2263` (NAD83 / New York Long Island ftUS)
  * **File Size**: 75.63 MB (79,306,752 bytes)
  * **Total Columns**: 102 fields

---

## 2. NYC Building Footprints

* **Source Agency**: NYC Office of Technology and Innovation (OTI) via NYC Open Data
* **Dataset Name**: Building Footprints
* **Dataset Identifier**: `5zhs-2jue`
* **Download Date**: October 13, 2026
* **Primary Export Attempt**:
  * Export URL: `https://data.cityofnewyork.us/api/geospatial/5zhs-2jue?method=export&format=Shapefile`
  * Status: Timed out after 180 seconds due to server-side generation of >1.08 million citywide polygons.
* **Direct SODA API Query**:
  * Endpoint: `https://data.cityofnewyork.us/resource/5zhs-2jue.geojson`
  * Filter Query: `$where=bin >= 5000000 AND bin < 6000000&$order=bin ASC`
  * Method: Paginated SODA API streaming (10,000 features per batch)
  * Staten Island Buildings Count: 142,499
* **Local Storage**:
  * **Raw GeoJSON (WGS84)**: `data/staten_island_building_footprints.geojson`
  * **Projected GeoPackage**: `data/staten_island_building_footprints.gpkg` (Layer: `staten_island_building_footprints`)
* **Staten Island Dataset Specifications**:
  * **Row Count**: 142,499 buildings
  * **CRS**: `EPSG:2263` (NAD83 / New York Long Island ftUS, reprojected from WGS84 `EPSG:4326`)
