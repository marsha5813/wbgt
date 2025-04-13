# Environment
import wbgt.functions.census as census
import wbgt.functions.api as api
import wbgt.functions.compute as compute
import wbgt.functions.viz as viz
import wbgt.functions.spatial as spatial
import numpy as np
import xarray as xr

# Test function to get a bounding box for a Census geography
bbox, geo, bbox_gdf = census.get_geography_bbox("state", "24")  # Maryland
print(bbox)
#geo.plot() # Visualize bounding box

# Download ERA5 data for this bounding box
ds_era5 = api.download_era5_data(bbox = bbox, year = 2023, month = 6)

# Preview data variables in ds_era5
print(ds_era5)
print(ds_era5.variables)
print(ds_era5['t2m'])  # 2m temperature variable

# Check the dimensions and coordinates of the dataset
print("ERA5 dimensions:", ds_era5.dims)
print("ERA5 coordinates:")
print("Latitude:", ds_era5.latitude.values)
print("Longitude:", ds_era5.longitude.values)
print("Time dimension (valid_time):", ds_era5.valid_time.values)

# Plot the first time slice of 2m temperature
m = viz.makemap(bbox, ds_era5, "t2m")
m # Display the map if using Jupyter Notebook or similar environment
# Save the map to an HTML file for viewing in a web browser
#m.save("interactive_map.html")

# Download derived UTCI data for the same bounding box
ds_utci = api.download_derived_utci_data(bbox, year=2023, month=6, day=15)
print(ds_utci)  # Check the downloaded data
print(ds_utci.variables)  # Check the variables in the dataset
viz.makemap(bbox, ds_utci, "mrt")

# Check the dimensions and coordinates of the dataset
print("UTCI dimensions:", ds_utci.dims)
print("UTCI coordinates:")
print("Latitude:", ds_utci.lat.values)
print("Longitude:", ds_utci.lon.values)
print("Time dimension (valid_time):", ds_utci.time.values)

# Now we need to join the two datasets (ERA5 and UTCI) on the time dimension.
# Note that the ERA5 data have higher spatial resolution than the UTCI data
# (which is derived from the ERA5 data). Let's keep the smaller, high-resolution
# grid from the ERA5 data and interpolate the UTCI data to match the ERA5 grid using nearest neighbor.
ds_utci_aligned = ds_utci.rename({'lat': 'latitude', 'lon': 'longitude', 'time': 'valid_time'})
mrt_interp = ds_utci_aligned.interp(latitude=ds_era5.latitude, longitude=ds_era5.longitude, method='nearest')
print(mrt_interp)  # Check the aligned UTCI data
mrt_interp['mrt']
viz.makemap(bbox, mrt_interp, "mrt")

# Note the ring of missing data around the edges of the interpolated data. This is due to the
# interpolation method and the fact that the original data may not cover the entire bounding box.
# The following helper functions can be used to fill in these missing values.
mrt_interp = api.fill_mrt_data(mrt_interp)
viz.makemap(bbox, mrt_interp, "mrt")

# Now join the two datasets on the time dimension.
# Need to limit the ERA5 data to just one day
ds_era5_day = ds_era5.sel(valid_time=ds_era5.valid_time.dt.floor("D") == np.datetime64("2023-06-15"))
ds_combined = xr.merge([ds_era5_day, mrt_interp])
print(ds_combined)
viz.makemap(bbox, ds_combined, "mrt")
viz.makemap(bbox, ds_combined, "d2m")

# Now let's download combined dataset for the month of July 2023
ds_combined = api.download_combined_data_month(bbox = bbox, 
                                               year = 2023, 
                                               month = 7)
print(ds_combined)  # Check the combined dataset
print(ds_combined.variables)  # Check the variables in the dataset
print(ds_combined['mrt'])  
viz.makemap(bbox, ds_combined, "mrt")
viz.makemap(bbox, ds_combined, "t2m")

# Compute WBGT parameters
daily_wbgt, max_wbgt = compute.compute_daily_and_max_wbgt(ds_combined)
print(daily_wbgt)  # Daily WBGT values
print(max_wbgt)  # Maximum WBGT values
print(max_wbgt.values)  # Print the maximum WBGT values

# Convert the DataArrays into Datasets with a variable name.
daily_wbgt_ds = daily_wbgt.to_dataset(name='daily_wbgt')
max_wbgt_ds = max_wbgt.to_dataset(name='max_wbgt')
viz.makemap(bbox, max_wbgt_ds, 'max_wbgt')

# Flatten the DataArray to a 1D array for descriptive statistics
da_series = max_wbgt_ds['max_wbgt'].to_series()
da_series.describe()

# Join the WBGT data to counties
wbgt_counties = spatial.join_wbgt_to_geography(max_wbgt, "county")
viz.make_county_choropleth(wbgt_counties)

