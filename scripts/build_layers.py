import pandas as pd
import geopandas as gpd

# ---------- CONFIG ----------
PARCELS_FILE         = "data_local/parcels_citywide.geojson"
PROJECTS_CSV         = "data_local/project_parcels.csv"
CUSTOM_PARCELS       = "data_local/custom_parcels.geojson"

PARCEL_KEY_COL       = "PIN"                # unique ID in parcel data
PARCEL_ADDRESS_COL   = "MAILTOADD"          # readable address
PARCEL_SDAT_COL      = "SDATLINK"           # link to SDAT detail page

OUT_PARCELS          = "data/projects_parcels.geojson"
OUT_PROJECT_POLYS    = "data/projects_polys.geojson"
SIMPLIFY_TOL         = 0.00005              # tweak if polygons feel heavy
# -----------------------------

def load_parcels():
    parcels = gpd.read_file(PARCELS_FILE)

    if parcels.crs is None or parcels.crs.to_epsg() != 4326:
        parcels = parcels.to_crs(4326)
   
    # Normalize parcel key to string
    parcels[PARCEL_KEY_COL] = parcels[PARCEL_KEY_COL].astype(str).str.strip()

    #Load custom polygons (optional override/supplement)
    try:
        custom = gpd.read_file(CUSTOM_PARCELS)
        if custom.crs is None or custom.crs.to_epsg() != 4326:
            custom = custom.to_crs(4326)
        custom[PARCEL_KEY_COL] = custom[PARCEL_KEY_COL].astype(str).str.strip()

        parcels = pd.concat([parcels, custom], ignore_index=True)
        print(f"Loaded {len(custom)} custom parcel geometries")
    except FileNotFoundError:
        print("No custom_parcels.geojson found; skipping custom geometries.")

    return parcels

def load_projects_table():
    # Expect columns:
    # parcel_id, project_id, project_name
    projects = pd.read_csv(PROJECTS_CSV, dtype={"parcel_id": str, "project_id": str, "project_name": str})

    return projects




def build_parcel_layers(merged: gpd.GeoDataFrame):
    """
    Build:
      - projects_parcels.geojson   (one feature per parcel)
    """
    merged["display_address"] = merged[PARCEL_ADDRESS_COL]
    merged["sdat_url"] = merged[PARCEL_SDAT_COL]

    parcel_props = [
        PARCEL_KEY_COL,
        "display_address",
        "sdat_url"
    ]

    # Polygons layer
    gdf_parcels = gpd.GeoDataFrame(
        merged[parcel_props + ["geometry"]].copy(),
        crs="EPSG:4326",
    )
    #Simplify geometry for web performance (not sure how much of a difference this makes)
    gdf_parcels["geometry"] = gdf_parcels.geometry.simplify(
        SIMPLIFY_TOL, preserve_topology=True
    )

    gdf_parcels.to_file(OUT_PARCELS, driver="GeoJSON")
    print(f"Wrote {OUT_PARCELS} with {len(gdf_parcels)} features")


def build_project_layer(merged: gpd.GeoDataFrame):
    """
    Build:
      - projects_sites.geojson   (one feature per project_id)
    Geometry: convex hull of all parcels in the project.
    """
    # Only keep rows that have a project_id
    proj = merged.copy()
    
    # Dissolve parcels by project_id
    # This gives us one row per project_id, with unioned geometry (might be MultiPolygon)

    #Add  additional fields here.
    agg = {
        "project_id": "first",
        "project_name": "first",
    }

    dissolved = proj.dissolve(by="project_id", aggfunc=agg)
    dissolved = dissolved.reset_index(drop=True)

    # Rename some columns to nicer names
    dissolved = dissolved.rename(
        columns={
            PARCEL_ADDRESS_COL: "display_address",
            PARCEL_SDAT_COL: "sdat_url",
        }
    )

    # Geometry choice:
    # - dissolved.geometry = union of parcels (could be MultiPolygon)
    # - convex hull = clean single polygon around them
    dissolved["geometry"] = dissolved.geometry.convex_hull

    project_props = [
        "project_id",
        "project_name",
    ]

    gdf_projects = gpd.GeoDataFrame(
        dissolved[project_props + ["geometry"]].copy(),
        crs="EPSG:4326",
    )

    gdf_projects["geometry"] = gdf_projects.geometry.simplify(
        SIMPLIFY_TOL, preserve_topology=True
    )

    gdf_projects.to_file(OUT_PROJECT_POLYS, driver="GeoJSON")
    print(f"Wrote {OUT_PROJECT_POLYS} with {len(gdf_projects)} project features")




def main():
    parcels  = load_parcels()
    projects = load_projects_table()

    print(f"Loaded {len(parcels)} city parcels, {len(projects)} project parcel rows")
    
    merged = parcels.merge(
        projects,
        left_on=PARCEL_KEY_COL,
        right_on="parcel_id",
        how="inner",
        suffixes=("", "_proj"),
    )

    print(f"Matched {len(merged)} parcels with custom projects")

    build_parcel_layers(merged)
    
    build_project_layer(merged)
    

if __name__ == "__main__":
    main()