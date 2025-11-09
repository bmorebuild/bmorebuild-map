import geopandas as gpd

PARCELS_FILE = "data_local/parcels_citywide.geojson"

gdf = gpd.read_file(PARCELS_FILE)

print("CRS:", gdf.crs)
print("\nColumns:")
#print(list(gdf.columns))
print(gdf.columns)


print("\nExample row:")
print(gdf.head(1).T)