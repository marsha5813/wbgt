# Environment
import wbgt.functions.census as census
import wbgt.functions.api as api
import wbgt.functions.compute as compute
import wbgt.functions.viz as viz
import wbgt.functions.spatial as spatial
import geopandas as gpd
import numpy as np
import xarray as xr

# Download data for July 22, 2024, 
# currently the hottest day on record

# Bounding box for whole United States
bbox = (-179.148909, 18.7763, -64.4623, 49.384358)  # (min_lon, min_lat, max_lon, max_lat)

# Download ERA5 data for this bounding box
ds_era5 = api.download_era5_data(bbox = bbox, year = 2024, month = 7)

# Keep only the time slice representing July 22, 2024
ds_era5_day = ds_era5.sel(valid_time=ds_era5.valid_time.dt.floor("D") == np.datetime64("2024-07-22"))

# Download derived UTCI data for the same bounding box
ds_utci = api.download_derived_utci_data(bbox, year=2024, month=7, day=22)

# Align UTCI grid with ERA5
ds_utci_aligned = ds_utci.rename({'lat': 'latitude', 'lon': 'longitude', 'time': 'valid_time'})
mrt_interp = ds_utci_aligned.interp(latitude=ds_era5.latitude, longitude=ds_era5.longitude, method='nearest')

# Fill in outer ring of missings
mrt_interp = api.fill_mrt_data(mrt_interp)

# Now join the two datasets on the time dimension.
ds_combined = xr.merge([ds_era5_day, mrt_interp])

# Compute WBGT parameters
daily_wbgt, max_wbgt = compute.compute_daily_and_max_wbgt(ds_combined)


# Join the max_wbgt data to ds_combined
final_grid = ds_combined.assign(wbgt=max_wbgt)

# collapse your final_grid to only 2D arrays:
final_grid = xr.Dataset({
    "wbgt": final_grid["wbgt"],  # already 2D
    "mrt":  final_grid["mrt"].max(dim="valid_time"),
    "t2m":  final_grid["t2m"].max(dim="valid_time"),
})

# Join the combined data to counties
counties_gdf = spatial.join_wbgt_to_geography(
    final_grid,
    geo_type="county",
    var_names=["wbgt", "mrt", "t2m"]
)

# Join the combined data to tracts
tracts_gdf = spatial.join_wbgt_to_geography(
    final_grid,
    geo_type="tract",
    var_names=["wbgt", "mrt", "t2m"]
)

# Export
import geopandas as gpd
counties_gdf.to_file("geoms.gpkg", layer="counties", driver="GPKG")
tracts_gdf.to_file("geoms.gpkg", layer="tracts",   driver="GPKG")
final_grid.to_zarr("final_grid.zarr", consolidated=True)
