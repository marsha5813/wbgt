import numpy as np
import xarray as xr
import thermofeel  # make sure thermofeel is installed

def compute_daily_and_max_wbgt(ds):
    """
    Compute the wet bulb globe temperature (WBGT) for each day in an xarray object,
    and then find the maximum WBGT for each grid cell.

    Parameters:
        ds (xarray.Dataset): Dataset with variables:
            - 't2m': 2m air temperature in Kelvin
            - 'mrt': mean radiant temperature in Kelvin
            - 'u10': u component of wind at 10m in m/s
            - 'v10': v component of wind at 10m in m/s
            - 'd2m': dew point temperature in Kelvin

    Returns:
        wbgt (xarray.DataArray): Daily WBGT values, with the same dimensions as ds (including time).
        wbgt_max (xarray.DataArray): Maximum WBGT per grid cell (maximized over the time dimension).
    """
    # Calculate 10-m wind speed from the u10 and v10 components
    wind_speed_10m = np.sqrt(ds['u10']**2 + ds['v10']**2)
    
    # Compute WBGT for each time slice using thermofeel.calculate_wbgt.
    # Here, apply_ufunc is used to vectorize the function application across the dataset.
    wbgt = xr.apply_ufunc(
        thermofeel.calculate_wbgt,  # function to compute wbgt
        ds['t2m'],                  # 2m air temperature
        ds['mrt'],                  # mean radiant temperature
        wind_speed_10m,             # computed 10m wind speed
        ds['d2m'],                  # dew point temperature
        vectorize=True,             # ensure the function is applied elementwise
        dask="parallelized",        # optional: enables parallelism if using Dask arrays
        input_core_dims=[[], [], [], []],   # no core dimensions (each function call works on a single element per array)
        output_core_dims=[[]]            # output is a scalar for each point
    )
    
    # Convert WBGT from Kelvin to Celsius.
    wbgt_c = wbgt - 273.15

    # Compute the maximum WBGT for each grid cell (assuming the time dimension is called 'time')
    wbgt_max = wbgt_c.max(dim='valid_time')
    
    return wbgt, wbgt_max

# Example usage:
# Assuming you have an xarray.Dataset `ds` with valid_time, latitude, and longitude dimensions:
# wbgt_daily, wbgt_grid_max = compute_daily_and_max_wbgt(ds)
