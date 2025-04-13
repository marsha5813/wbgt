import os
import cdsapi
import xarray as xr
import zipfile
import numpy as np
from scipy import ndimage
import tempfile
import shutil
import calendar

def download_era5_data(bbox, year, month=None):
    """
    Download ERA5 reanalysis data for the given bounding box and time period.
    
    Parameters:
      bbox  : tuple (min_lon, min_lat, max_lon, max_lat)
      year  : integer year (e.g., 2023)
      month : optional integer month (1-12); if None, data for the entire year are downloaded
    
    Returns:
      ds : xarray Dataset with:
           - 2m_temperature
           - 2m_dewpoint_temperature
           - 10m_u_component_of_wind
           - 10m_v_component_of_wind
           
    Data is loaded into memory and temporary files are deleted.
    """
    c = cdsapi.Client()
    if month:
        months = [f"{month:02d}"]
    else:
        months = [f"{m:02d}" for m in range(1, 13)]
    
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".nc")
    result_filename = tmp_file.name
    tmp_file.close()
    
    c.retrieve(
        'reanalysis-era5-single-levels',
        {
            'product_type': 'reanalysis',
            'variable': [
                '2m_temperature',
                '2m_dewpoint_temperature',
                '10m_u_component_of_wind',
                '10m_v_component_of_wind'
            ],
            'year': str(year),
            'month': months,
            'day': [f"{d:02d}" for d in range(1, 32)],
            'time': [f"{t:02d}:00" for t in range(24)],
            'area': [bbox[3], bbox[0], bbox[1], bbox[2]],
            'format': 'netcdf'
        },
        result_filename
    )
    
    with open(result_filename, "rb") as f:
        header = f.read(4)
    
    if header.startswith(b"PK"):
        extract_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(result_filename, "r") as z:
            file_list = z.namelist()
            # Prefer a file with "instant" in its name if available.
            chosen_file = next((fname for fname in file_list if "instant" in fname), file_list[0])
            z.extract(chosen_file, extract_dir)
            data_filepath = os.path.join(extract_dir, chosen_file)
    else:
        data_filepath = result_filename
        extract_dir = None

    try:
        with xr.open_dataset(data_filepath, engine="cfgrib", chunks={'time': 24}) as ds_tmp:
            ds = ds_tmp.load()
    except Exception:
        with xr.open_dataset(data_filepath, engine="netcdf4", chunks={'time': 24}) as ds_tmp:
            ds = ds_tmp.load()
    
    if os.path.exists(result_filename):
        os.remove(result_filename)
    if extract_dir:
        shutil.rmtree(extract_dir)
    
    return ds

def download_derived_utci_data(bbox, year, month, day,
                               variable=["mean_radiant_temperature"],
                               product_type="consolidated_dataset",
                               version="1_1"):
    """
    Download derived UTCI historical data (e.g., mean radiant temperature) for the given date and bounding box.
    
    Parameters:
      bbox         : tuple (min_lon, min_lat, max_lon, max_lat)
      year         : integer year (e.g., 2019)
      month        : integer month (1-12)
      day          : integer day (1-31)
      variable     : list of variables (default is ["mean_radiant_temperature"])
      product_type : "consolidated_dataset" or "intermediate_dataset"
      version      : dataset version (default "1_1")
    
    Returns:
      ds : xarray Dataset with the requested variable(s)
      
    Data is loaded into memory and temporary files are deleted.
    """
    client = cdsapi.Client()
    area = [bbox[3], bbox[0], bbox[1], bbox[2]]
    
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".nc")
    result_filename = tmp_file.name
    tmp_file.close()
    
    request = {
        "variable": variable,
        "version": version,
        "product_type": product_type,
        "year": [str(year)],
        "month": [f"{int(month):02d}"],
        "day": [f"{int(day):02d}"],
        "area": area,
        "format": "netcdf"
    }
    client.retrieve("derived-utci-historical", request, result_filename)
    
    # Check if file is a ZIP archive; if so, extract it.
    with open(result_filename, "rb") as f:
        header = f.read(4)
    if header.startswith(b"PK"):
        extract_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(result_filename, "r") as z:
            file_list = z.namelist()
            chosen_file = file_list[0]
            z.extract(chosen_file, extract_dir)
            data_filepath = os.path.join(extract_dir, chosen_file)
    else:
        data_filepath = result_filename
        extract_dir = None

    with xr.open_dataset(data_filepath, engine="netcdf4") as ds_tmp:
        ds = ds_tmp.load()
    if os.path.exists(result_filename):
        os.remove(result_filename)
    if extract_dir:
        shutil.rmtree(extract_dir)
    
    return ds

def fill_nan_with_nearest_2d(arr):
    """
    Given a 2D numpy array with NaNs, returns an array where NaNs are replaced by the nearest non-NaN neighbor.
    """
    mask = np.isnan(arr)
    if not mask.any():
        # No NaNs present
        return arr
    # ndimage.distance_transform_edt returns, among other things, the indices of the nearest non-NaN
    # Here, indices will have shape (2, height, width) for a 2D input array.
    _, indices = ndimage.distance_transform_edt(mask, return_distances=True, return_indices=True)
    filled = arr.copy()
    # Use the indices arrays to fill in the NaNs.
    filled[mask] = arr[tuple(indices[:, mask])]
    return filled

def fill_mrt_data(ds, var_name="mrt"):
    """
    For an xarray Dataset ds with an MRT variable (2D per time slice), fill missing (NaN)
    spatial values with the nearest non-missing neighbor.
    
    Parameters:
      ds: xarray Dataset containing the variable of interest.
      var_name: Name of the variable to fill (default is "mrt")
    
    Returns:
      ds_filled: The same dataset with the specified variable filled.
    """
    da = ds[var_name]
    
    # Check if there's a time dimension to loop over.
    if "valid_time" in da.dims:
        filled_slices = []
        for t in da.valid_time.values:
            # Select the slice for a particular time
            da_slice = da.sel(valid_time=t)
            # Get the 2D array from the slice
            arr = da_slice.values
            # Fill the missing values using our helper function
            filled_arr = fill_nan_with_nearest_2d(arr)
            # Recreate a DataArray for this time slice
            da_filled = xr.DataArray(
                filled_arr,
                coords=da_slice.coords,
                dims=da_slice.dims
            )
            filled_slices.append(da_filled.expand_dims(valid_time=[t]))
        # Concatenate along the time dimension
        da_filled_all = xr.concat(filled_slices, dim="valid_time")
    else:
        # If no time coordinate, apply directly.
        da_filled_all = xr.DataArray(
            fill_nan_with_nearest_2d(da.values),
            coords=da.coords,
            dims=da.dims
        )
    
    # Replace the original variable in the dataset with the filled one.
    ds_filled = ds.copy()
    ds_filled[var_name] = da_filled_all
    return ds_filled

def download_combined_data_month(bbox, year, month):
    """
    Downloads ERA5 reanalysis data for the entire month and loops through each day to
    download the corresponding derived UTCI data (e.g., mean radiant temperature). Then,
    the derived UTCI data are interpolated onto the ERA5 grid (using nearest neighbor),
    filled to remove any edge NaNs, and merged into a single xarray Dataset along the time
    coordinate ('valid_time').

    Parameters:
      bbox  : tuple (min_lon, min_lat, max_lon, max_lat)
      year  : integer (e.g., 2023)
      month : integer month (e.g., 7 for July)

    Returns:
      ds_combined : an xarray Dataset containing:
                    - 2m_temperature, 2m_dewpoint_temperature,
                      10m_u_component_of_wind, 10m_v_component_of_wind
                    - mean radiant temperature (as 'mrt'),
                    with the time coordinate spanning all days in the month.
    """
    # Download ERA5 reanalysis data for the month.
    ds_era5 = download_era5_data(bbox, year, month)
    
    # Download derived UTCI data for each day in the month.
    _, num_days = calendar.monthrange(year, month)
    list_utci = []
    for day in range(1, num_days + 1):
        # Download derived UTCI data for the given day.
        ds_utci_day = download_derived_utci_data(bbox, year, month, day)
        # Rename coordinates for consistency with ERA5.
        ds_utci_day = ds_utci_day.rename({'time': 'valid_time', 'lat': 'latitude', 'lon': 'longitude'})
        # Interpolate the derived UTCI data onto the ERA5 grid using nearest neighbor.
        ds_utci_day = ds_utci_day.interp(
            latitude=ds_era5.latitude,
            longitude=ds_era5.longitude,
            method='nearest'
        )
        list_utci.append(ds_utci_day)
    
    # Concatenate the daily derived data along the valid_time dimension.
    ds_utci_all = xr.concat(list_utci, dim='valid_time')
    
    # Fill the outer missing ring in the 'mrt' variable
    ds_utci_all = fill_mrt_data(ds_utci_all, var_name="mrt")
    
    # Merge ERA5 data with the interpolated (and gap-filled) derived UTCI data.
    ds_combined = xr.merge([ds_era5, ds_utci_all])
    return ds_combined