import pandas as pd
import geopandas as gpd

# ---------- CONFIG ----------
PARCELS_FILE         = "data_local/parcels_citywide.geojson"
PROJECTS_CSV         = "data_local/projects.csv"

PARCEL_KEY_COL       = "PIN"                # unique ID in parcel data
PARCEL_ADDRESS_COL   = "MAILTOADD"          # readable address
PARCEL_SDAT_COL      = "SDATLINK"           # link to SDAT detail page

OUT_PARCELS          = "data/projects_parcels.geojson"
OUT_POINTS           = "data/projects_points.geojson"
SIMPLIFY_TOL         = 0.00005              # tweak if polygons feel heavy
# -----------------------------

def main():
    # 1) Load parcels
    parcels = gpd.read_file(PARCELS_FILE)
    if parcels.crs is None or parcels.crs.to_epsg() != 4326:
        parcels = parcels.to_crs(4326)

    # Normalize parcel key to string
    parcels[PARCEL_KEY_COL] = parcels[PARCEL_KEY_COL].astype(str)

    # 2) Load your custom projects table
    projects = pd.read_csv(PROJECTS_CSV, dtype={"parcel_id": str})

    # Optional sanity check
    print(f"Loaded {len(parcels)} parcels, {len(projects)} projects")

    # 3) Inner join: keep only parcels that have a matching project
    merged = parcels.merge(
        projects,
        left_on=PARCEL_KEY_COL,
        right_on="parcel_id",
        how="inner",
        suffixes=("", "_proj"),
    )

    print(f"Matched {len(merged)} parcels with custom projects")

    # 4) Derive display fields
    merged["display_address"] = merged[PARCEL_ADDRESS_COL]
    merged["sdat_url"] = merged[PARCEL_SDAT_COL]

    # 5) Choose properties to expose on the web
    props = [
        PARCEL_KEY_COL,
        "display_address",
        "sdat_url"
    ]

    # 6) Polygons layer
    gdf_parcels = gpd.GeoDataFrame(
        merged[props + ["geometry"]].copy(),
        crs="EPSG:4326",
    )

    # Simplify geometry for web performance
    gdf_parcels["geometry"] = gdf_parcels.geometry.simplify(
        SIMPLIFY_TOL, preserve_topology=True
    )

    gdf_parcels.to_file(OUT_PARCELS, driver="GeoJSON")
    print(f"✅ Wrote {OUT_PARCELS} with {len(gdf_parcels)} features")

    # 7) Points layer (centroids)
    gdf_points = gdf_parcels.copy()
    gdf_points["geometry"] = gdf_points.geometry.centroid

    gdf_points.to_file(OUT_POINTS, driver="GeoJSON")
    print(f"✅ Wrote {OUT_POINTS} with {len(gdf_points)} features")



if __name__ == "__main__":
    main()