import pandas as pd
import geopandas as gpd


# ---------- CONFIG ----------
PARCELS_FILE         = "data_local/parcels_citywide.geojson"
PROJECTS_PARCELS_CSV = "data_local/project_parcels.csv"
PROJECT_LIST_CSV     = "data_local/project_list.csv"
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
    parcels_tbl = pd.read_csv(PROJECTS_PARCELS_CSV, dtype={"parcel_id": str, "project_id": str, "project_name": str})
    
    
    #Under construction: combine the two so that more project data can be displayed
    proj_list = pd.read_csv(PROJECT_LIST_CSV,dtype={"project_id": str, "project_name": str, "project_link": str},
    )

    projects = parcels_tbl.merge(
        proj_list,
        on="project_id",
        how="left",     # parcels can exist even if project_list row missing
        validate="m:1", # many parcels -> 1 project
    )

    return projects



def build_project_layer(merged: gpd.GeoDataFrame):
    
    """
    Builds:
      - projects_sites.geojson   (one feature per project_id)
    """
       
    # Split into non-custom vs custom based on PIN suffix
    pin_str = merged[PARCEL_KEY_COL].astype(str)
    mask_custom = pin_str.str.endswith("CUST")

    non_custom = merged[~mask_custom].copy()
    custom     = merged[mask_custom].copy()


    # Dissolve non-custom parcels by project_id
    # This gives us one row per project_id

    #Add  additional fields here.
    agg = {
        "project_id": "first",
        "project_name_y": "first",
        "project_link": "first",
    }

    dissolved = non_custom.dissolve(by="project_id", aggfunc=agg)
    dissolved = dissolved.reset_index(drop=True)

    #Convex hull = clean single polygon around them
    dissolved["geometry"] = dissolved.geometry.convex_hull

    project_props = [
        "project_name_y",
        "project_link"
    ]

    #Create non-customer geodataframe
    gdf_non_custom = gpd.GeoDataFrame(
        dissolved[project_props + ["geometry"]].copy(),
        crs="EPSG:4326",
    )

    gdf_non_custom["geometry"] = gdf_non_custom.geometry.simplify(
        SIMPLIFY_TOL, preserve_topology=True
    )

    # filter custom parcels to project_props and geometry
    gdf_custom = gpd.GeoDataFrame(
        custom[project_props + ["geometry"]].copy(),
        crs="EPSG:4326",
    )

    #append gdf_non_custom and gdf_custom
    gdf_combined = pd.concat([gdf_non_custom, gdf_custom], ignore_index=True)

    gdf_combined.to_file(OUT_PROJECT_POLYS, driver="GeoJSON")
    print(f"Wrote {OUT_PROJECT_POLYS} with {len(gdf_combined)} project features")




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
    build_project_layer(merged)
    print("Complete")

if __name__ == "__main__":
    main()