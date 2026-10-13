"""
Staten Island Tax Lot & Building Footprint Analysis Pipeline
=============================================================
This script executes the complete data pipeline:
1. Downloads and extracts MapPLUTO 26v2 (filtered to Staten Island).
2. Downloads official Building Footprints (5zhs-2jue) for Staten Island via SODA API.
3. Cleans and standardizes BBL identifiers to 10-digit format.
4. Filters to 1:1 lots (NumBldgs == 1, NumFloors > 0, BldgArea > 0, exactly 1 footprint).
5. Calculates the ratio: (footprint_area * NumFloors) / BldgArea and log_ratio.
6. Exports full results (data/ratio_results.csv), 30-lot review sheet (data/review_sheet.csv),
   and spatial layers for flagged lots (data/flagged_lots.gpkg).
"""

import os
import json
import time
import urllib.request
import urllib.parse
import numpy as np
import pandas as pd
import geopandas as gpd

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")

MAPPLUTO_ZIP_URL = "https://s-media.nyc.gov/agencies/dcp/assets/files/zip/data-tools/bytes/mappluto/nyc_mappluto_26v2_shp.zip"
MAPPLUTO_ZIP_PATH = os.path.join(RAW_DIR, "nyc_mappluto_26v2_shp.zip")
MAPPLUTO_GPKG_PATH = os.path.join(DATA_DIR, "staten_island_mappluto.gpkg")

FOOTPRINTS_GEOJSON_PATH = os.path.join(DATA_DIR, "staten_island_building_footprints.geojson")
FOOTPRINTS_GPKG_PATH = os.path.join(DATA_DIR, "staten_island_building_footprints.gpkg")

RATIO_RESULTS_CSV = os.path.join(DATA_DIR, "ratio_results.csv")
REVIEW_SHEET_CSV = os.path.join(DATA_DIR, "review_sheet.csv")
FLAGGED_LOTS_GPKG = os.path.join(DATA_DIR, "flagged_lots.gpkg")


def clean_bbl(val):
    """Standardizes BBL into a clean 10-digit zero-padded string."""
    if pd.isna(val):
        return None
    try:
        val_str = str(val).strip()
        if val_str.endswith(".0"):
            val_str = val_str[:-2]
        val_int = int(float(val_str))
        if val_int <= 0:
            return None
        return f"{val_int:010d}"
    except (ValueError, TypeError):
        return None


def download_file(url, target_path):
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    if os.path.exists(target_path):
        print(f"[MapPLUTO] Archive already exists: {target_path}")
        return
    print(f"[Download] Fetching {url} -> {target_path}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(target_path, "wb") as f:
        while True:
            chunk = resp.read(1024 * 512)
            if not chunk:
                break
            f.write(chunk)
    print(f"[Download] Complete ({os.path.getsize(target_path)/(1024*1024):.2f} MB)")


def prepare_mappluto():
    download_file(MAPPLUTO_ZIP_URL, MAPPLUTO_ZIP_PATH)
    if os.path.exists(MAPPLUTO_GPKG_PATH):
        print(f"[MapPLUTO] GeoPackage already exists: {MAPPLUTO_GPKG_PATH}")
        return gpd.read_file(MAPPLUTO_GPKG_PATH)

    print("[MapPLUTO] Reading citywide shapefile and filtering to Staten Island (Borough == 'SI')...")
    gdf = gpd.read_file(f"zip://{MAPPLUTO_ZIP_PATH}!MapPLUTO.shp", engine="pyogrio")
    si_gdf = gdf[gdf["Borough"] == "SI"].copy()
    si_gdf.to_file(MAPPLUTO_GPKG_PATH, layer="staten_island_mappluto", driver="GPKG", engine="pyogrio")
    print(f"[MapPLUTO] Saved Staten Island layer ({len(si_gdf)} tax lots) to {MAPPLUTO_GPKG_PATH}")
    return si_gdf


def prepare_footprints():
    if os.path.exists(FOOTPRINTS_GPKG_PATH):
        print(f"[Footprints] GeoPackage already exists: {FOOTPRINTS_GPKG_PATH}")
        return gpd.read_file(FOOTPRINTS_GPKG_PATH)

    if not os.path.exists(FOOTPRINTS_GEOJSON_PATH):
        print("[Footprints] Streaming Staten Island footprints via SODA API (bin >= 5000000 AND bin < 6000000)...")
        base_url = "https://data.cityofnewyork.us/resource/5zhs-2jue.geojson"
        where_clause = "bin >= 5000000 AND bin < 6000000"
        limit = 10000
        offset = 0
        all_features = []

        while True:
            params = {
                "$where": where_clause,
                "$limit": str(limit),
                "$offset": str(offset),
                "$order": "bin ASC",
            }
            url = f"{base_url}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                features = data.get("features", [])
                all_features.extend(features)
                print(f"  Fetched {len(all_features)} features...", end="\r")
                if len(features) < limit:
                    break
                offset += limit

        print(f"\n[Footprints] Downloaded {len(all_features)} features.")
        full_geojson = {"type": "FeatureCollection", "features": all_features}
        with open(FOOTPRINTS_GEOJSON_PATH, "w", encoding="utf-8") as f:
            json.dump(full_geojson, f)

    print("[Footprints] Reprojecting footprints to EPSG:2263...")
    fp_gdf = gpd.read_file(FOOTPRINTS_GEOJSON_PATH)
    fp_2263 = fp_gdf.to_crs(epsg=2263)
    fp_2263.to_file(FOOTPRINTS_GPKG_PATH, layer="staten_island_building_footprints", driver="GPKG")
    print(f"[Footprints] Saved projected footprints ({len(fp_2263)}) to {FOOTPRINTS_GPKG_PATH}")
    return fp_2263


def run_pipeline():
    os.makedirs(RAW_DIR, exist_ok=True)
    pluto_gdf = prepare_mappluto()
    fp_gdf = prepare_footprints()

    print("\n[Pipeline] Standardizing BBL identifiers...")
    pluto_gdf["bbl_clean"] = pluto_gdf["BBL"].apply(clean_bbl)
    fp_gdf["bbl_clean"] = fp_gdf["base_bbl"].apply(clean_bbl)

    # Compute area directly in EPSG:2263 (square feet)
    fp_gdf["footprint_area"] = fp_gdf.geometry.area

    print("[Pipeline] Filtering to 1:1 single-building lots...")
    fp_counts = fp_gdf["bbl_clean"].value_counts()
    lots_with_1_fp = set(fp_counts[fp_counts == 1].index)

    filtered_lots = pluto_gdf[
        (pluto_gdf["NumBldgs"] == 1)
        & (pluto_gdf["NumFloors"] > 0)
        & (pluto_gdf["BldgArea"] > 0)
        & (pluto_gdf["bbl_clean"].isin(lots_with_1_fp))
    ].copy()

    fp_1to1 = fp_gdf[fp_gdf["bbl_clean"].isin(set(filtered_lots["bbl_clean"]))].drop_duplicates("bbl_clean")

    merged = filtered_lots.merge(
        fp_1to1[["bbl_clean", "bin", "footprint_area", "geometry"]].rename(columns={"geometry": "fp_geometry"}),
        on="bbl_clean",
        how="inner",
    )

    merged["ratio"] = (merged["footprint_area"] * merged["NumFloors"]) / merged["BldgArea"]
    merged["log_ratio"] = np.log(merged["ratio"])

    print(f"[Pipeline] Matched {len(merged)} lots meeting all criteria.")

    # 1. Export full results
    csv_cols = ["bbl_clean", "Address", "BldgArea", "NumFloors", "footprint_area", "ratio", "log_ratio"]
    ratio_df = merged[csv_cols].rename(columns={"bbl_clean": "BBL", "Address": "address"})
    ratio_df.to_csv(RATIO_RESULTS_CSV, index=False)
    print(f"[Export] Full results saved: {RATIO_RESULTS_CSV}")

    # 2. Export 30-lot review sheet (15 bottom + 15 top)
    bottom15 = merged.sort_values(by="ratio", ascending=True).head(15).copy()
    bottom15["flag_type"] = "Extreme Under-Ratio (footprint*floors << BldgArea)"
    bottom15["rank"] = range(1, 16)

    top15 = merged.sort_values(by="ratio", ascending=False).head(15).copy()
    top15["flag_type"] = "Extreme Over-Ratio (footprint*floors >> BldgArea)"
    top15["rank"] = range(1, 16)

    review30 = pd.concat([bottom15, top15], ignore_index=True)
    review_cols = ["flag_type", "rank", "bbl_clean", "Address", "BldgArea", "NumFloors", "footprint_area", "ratio", "log_ratio"]
    review_df = review30[review_cols].rename(columns={"bbl_clean": "BBL", "Address": "address"})
    review_df.to_csv(REVIEW_SHEET_CSV, index=False)
    print(f"[Export] 30-lot review sheet saved: {REVIEW_SHEET_CSV}")

    # 3. Export flagged lots with geometry
    flagged_lots_gdf = gpd.GeoDataFrame(review_df, geometry=review30["geometry"].values, crs=filtered_lots.crs)
    flagged_lots_gdf.to_file(FLAGGED_LOTS_GPKG, layer="flagged_tax_lots", driver="GPKG")

    flagged_fp_gdf = gpd.GeoDataFrame(review_df, geometry=review30["fp_geometry"].values, crs=fp_gdf.crs)
    flagged_fp_gdf.to_file(FLAGGED_LOTS_GPKG, layer="flagged_building_footprints", driver="GPKG")
    print(f"[Export] Flagged lots spatial layer saved: {FLAGGED_LOTS_GPKG}")

    # Summary Stats
    p = np.percentile(merged["ratio"], [1, 5, 25, 50, 75, 95, 99])
    print("\n--- Summary Percentiles ---")
    print(f" 1st: {p[0]:.4f} |  5th: {p[1]:.4f} | 25th: {p[2]:.4f} | 50th: {p[3]:.4f}")
    print(f"75th: {p[4]:.4f} | 95th: {p[5]:.4f} | 99th: {p[6]:.4f}")


if __name__ == "__main__":
    run_pipeline()
