# wbgt/core.py

from wbgt.functions import census, api, compute, spatial, viz

def get_wbgt(geo_limit: str, geo_limit_fips: str, output_type: str,
             month: int, year: int, max: bool = True):
    """
    Retrieve Wet Bulb Globe Temperature (WBGT) data for a specified geography and time period.

    Parameters:
      geo_limit (str): One of "nation", "state", "county", or "tract". Determines the spatial extent.
                       If "nation", a bounding box covering the entire United States (including Alaska and Hawaii) is used.
      geo_limit_fips (str): The FIPS code for the specified geography (e.g., "24" for Maryland).
                            Set to None geo_limit is "nation".
      output_type (str): One of "grid", "counties", or "tracts".
                         "grid" returns raw gridded WBGT data,
                         "counties" and "tracts" spatially join the WBGT data to the respective Census geometries.
      month (int): The month (1-12) of climate reanalysis data to download.
      year (int): The year of the climate reanalysis data.
      max (bool): If True (default), returns the maximum WBGT for each grid cell over the month.
                  If False, returns the daily WBGT values.

    Returns:
      Depending on the output_type:
         - For "grid": an xarray DataArray containing the maximum (or daily) WBGT values.
         - For "counties" or "tracts": a geopandas GeoDataFrame with WBGT values joined to the respective geometry.

    Raises:
      ValueError: If an invalid geo_limit or output_type is provided.
    """
    # Determine the bounding box for data download.
    if geo_limit.lower() == "nation":
        # Hardcoded bounding box covering the entire United States (including Alaska and Hawaii)
        bbox = (-179, 18, -65, 72)
    elif geo_limit.lower() in ["state", "county", "tract"]:
        bbox, geo, bbox_gdf = census.get_geography_bbox(geo_limit.lower(), geo_limit_fips)
    else:
        raise ValueError("Invalid geo_limit. Must be one of 'nation', 'state', 'county', or 'tract'.")

    # Download the ERA5 reanalysis and derived UTCI data for the specified month.
    ds_combined = api.download_combined_data_month(bbox, year, month)

    # Compute the daily WBGT and the maximum WBGT from the combined dataset.
    daily_wbgt, max_wbgt = compute.compute_daily_and_max_wbgt(ds_combined)

    # Depending on the output type, either return raw grid data or spatially joined WBGT.
    output_type = output_type.lower()
    if output_type == "grid":
        return max_wbgt if max else daily_wbgt
    elif output_type == "counties":
        wbgt_counties = spatial.join_wbgt_to_geography(max_wbgt, "county")
        return wbgt_counties
    elif output_type == "tracts":
        wbgt_tracts = spatial.join_wbgt_to_geography(max_wbgt, "tract")
        return wbgt_tracts
    else:
        raise ValueError("Invalid output_type. Must be one of 'grid', 'counties', or 'tracts'.")