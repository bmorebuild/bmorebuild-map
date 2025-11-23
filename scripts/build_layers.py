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

OUT_UNDER_CONSTRUCTION          = "data/UNDER_CONSTRUCTION.geojson"
OUT_COMPLETED_2025    = "data/COMPLETED_2025.geojson"
SIMPLIFY_TOL         = 0.00005              # tweak if polygons feel heavy
# -----------------------------


def load_parcels():
    
    print("Load geometries")
    parcels = gpd.read_file(PARCELS_FILE)

    if parcels.crs is None or parcels.crs.to_epsg() != 4326:
        parcels = parcels.to_crs(4326)
   
    # Normalize parcel key to string
    parcels[PARCEL_KEY_COL] = parcels[PARCEL_KEY_COL].astype(str).str.strip()
    print(f"    Loaded {len(parcels)} city parcels")


    #Load custom polygons (optional override/supplement)
    try:
        custom = gpd.read_file(CUSTOM_PARCELS)
        if custom.crs is None or custom.crs.to_epsg() != 4326:
            custom = custom.to_crs(4326)
        custom[PARCEL_KEY_COL] = custom[PARCEL_KEY_COL].astype(str).str.strip()
        print(f"    Loaded {len(custom)} custom parcels")
        
        parcels = pd.concat([parcels, custom], ignore_index=True)
        print(f"    Combined into {len(parcels)} total shapes")
       


    except FileNotFoundError:
        print("No custom_parcels.geojson found; skipping custom geometries.")

    return parcels



def load_projects_table():
    

    print("Load CSVs")
    #load parcel csv file and retain all columns except project_name
    parcels_tbl = pd.read_csv(PROJECTS_PARCELS_CSV, dtype={"parcel_id": str, "project_id": str, "project_status": str, "completed_year":str})
    
    #load project list csv file and retain all columns
    proj_list = pd.read_csv(PROJECT_LIST_CSV,dtype={"project_id": str, "project_name": str, "project_link": str},
    )

    print(f"    project_parcels.csv: {len(parcels_tbl)} parcels")
    print(f"    project_list.csv: {len(proj_list)} projects")

    #join parcel csv and projects csv with project_id
    project_data = parcels_tbl.merge(
        proj_list,
        on="project_id",
        how="left",     # parcels can exist even if project_list row missing
        validate="m:1", # many parcels -> 1 project
    )
    print(f"    Total {len(project_data)} parcels with matching project")
    return project_data



def build_project_layer(merged: gpd.GeoDataFrame):
    
    """
    Builds:
      - UNDER_CONSTRUCTION.geojson   (one feature per project_id)
      - COMPLETED_2025.geojson (one feature per project_id)
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
        "project_name": "first",
        "project_link": "first",
        "project_status": "first",
        "completed_year": "first"
    }

    dissolved = non_custom.dissolve(by="project_id", aggfunc=agg)
    dissolved = dissolved.reset_index(drop=True)

    #Convex hull = clean single polygon around them
    dissolved["geometry"] = dissolved.geometry.convex_hull

    keep = [
        "project_id",
        "project_name",
        "project_link",
        "project_status",
        "completed_year"
    ]

    #Create non-custom geodataframe
    gdf_non_custom = gpd.GeoDataFrame(
        dissolved[keep + ["geometry"]].copy(),
        crs="EPSG:4326",
    )

    gdf_non_custom["geometry"] = gdf_non_custom.geometry.simplify(
        SIMPLIFY_TOL, preserve_topology=True
    )

    # filter custom parcels to project_props and geometry
    gdf_custom = gpd.GeoDataFrame(
        custom[keep + ["geometry"]].copy(),
        crs="EPSG:4326",
    )

    #append gdf_non_custom and gdf_custom
    gdf_combined = pd.concat([gdf_non_custom, gdf_custom], ignore_index=True)


    #split into two publishable layers
    under_construction = gdf_combined[gdf_combined["project_status"] == "Under Construction"].copy()
    completed_2025 = gdf_combined[(gdf_combined["project_status"] == "Completed") & (gdf_combined["completed_year"].astype(str) == "2025")].copy()


    print("Creating project geometry")
    print(f"    Under Construction:     {len(under_construction)} projects")
    print(f"    Completed 2025:         {len(completed_2025)} projects")


    under_construction.to_file(OUT_UNDER_CONSTRUCTION, driver="GeoJSON")
    completed_2025.to_file(OUT_COMPLETED_2025, driver="GeoJSON")

    print(f"Wrote {OUT_UNDER_CONSTRUCTION}")
    print(f"Wrote {OUT_COMPLETED_2025}")




def main():

    parcels  = load_parcels()

    project_data = load_projects_table()

      
    merged = parcels.merge(
        project_data,
        left_on=PARCEL_KEY_COL,
        right_on="parcel_id",
        how="inner",
        suffixes=("", "_proj"),
    )

    merged = merged.rename(columns={"project_name_y": "project_name"})
    
    build_project_layer(merged)
    print("Complete")

if __name__ == "__main__":
    main()