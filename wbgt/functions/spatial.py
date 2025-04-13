import os
import geopandas as gpd
import xarray as xr
import numpy as np
from shapely.geometry import box

def join_wbgt_to_geography(max_wbgt: xr.DataArray, geo_type: str = "county") -> gpd.GeoDataFrame:
    """
    Spatially joins gridded WBGT values (max_wbgt) to local Census regions
    (counties or tracts) that are stored as shapefiles in the /data directory
    one level above the functions directory.
    
    The function converts grid cells to polygons, calculates the fraction of each
    cell that intersects with a Census region, and computes a weighted average
    WBGT for the region.

    Parameters:
      max_wbgt: xarray.DataArray
          A DataArray containing gridded wet bulb globe temperatures.
          It must have 'latitude' and 'longitude' coordinates (cell centers).
      geo_type: str
          Either "county" or "tract". Other options are not supported.

    Returns:
      result_gdf: geopandas.GeoDataFrame
          A GeoDataFrame with one row per region (county or tract), including the
          weighted WBGT value, the region identifier (GEOID if available), and geometry.
    """
    
    # Compute the base directory: go up one level from the current file's directory
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    
    # Determine the shapefile path based on the geography type.
    if geo_type == "county":
        shp_path = os.path.join(base_dir, "cb_2023_us_county_5m", "cb_2023_us_county_5m.shp")
    elif geo_type == "tract":
        shp_path = os.path.join(base_dir, "cb_2023_us_tract_5m", "cb_2023_us_tract_5m.shp")
    else:
        raise ValueError("Invalid geography type. Choose 'tract' or 'county'.")

    # Read the shapefile into a GeoDataFrame.
    regions_gdf = gpd.read_file(shp_path)
    
    # Convert CRS to EPSG:4326 if needed.
    if regions_gdf.crs is None or regions_gdf.crs.to_string() != "EPSG:4326":
        regions_gdf = regions_gdf.to_crs("EPSG:4326")
    
    # --------------------------------------------------------
    # Convert grid cells from max_wbgt to polygons.
    # Assumes the xarray DataArray has 1D 'lat' and 'lon' coordinates representing cell centers.
    # --------------------------------------------------------
    lats = max_wbgt['latitude'].values
    lons = max_wbgt['longitude'].values

    # Estimate grid resolution (assuming uniform spacing).
    if len(lats) > 1:
        dlat = np.abs(lats[1] - lats[0])
    else:
        raise ValueError("Latitude coordinate must have more than one value to determine cell size.")
    
    if len(lons) > 1:
        dlon = np.abs(lons[1] - lons[0])
    else:
        raise ValueError("Longitude coordinate must have more than one value to determine cell size.")

    grid_polys = []
    wbgt_values = []
    # Create a polygon for each grid cell.
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            cell_poly = box(lon - dlon/2, lat - dlat/2, lon + dlon/2, lat + dlat/2)
            grid_polys.append(cell_poly)
            wbgt_values.append(max_wbgt.values[i, j])
    
    grid_gdf = gpd.GeoDataFrame({"wbgt": wbgt_values, "geometry": grid_polys}, crs="EPSG:4326")
    
    # --------------------------------------------------------
    # Proportional allocation: For each region, compute a weighted average WBGT.
    # For each grid cell overlapping a region, use the fraction of its area inside the region as a weight.
    # --------------------------------------------------------
    results = []
    for idx, region in regions_gdf.iterrows():
        region_geom = region.geometry
        # Identify grid cells that intersect the region.
        intersects_mask = grid_gdf.intersects(region_geom)
        intersecting_cells = grid_gdf[intersects_mask].copy()
        if intersecting_cells.empty:
            continue

        total_weight = 0.0
        weighted_sum = 0.0
        for cell_idx, cell in intersecting_cells.iterrows():
            intersection = cell.geometry.intersection(region_geom)
            if not intersection.is_empty:
                weight = intersection.area / cell.geometry.area
                weighted_sum += cell.wbgt * weight
                total_weight += weight

        region_wbgt = weighted_sum / total_weight if total_weight > 0 else np.nan
        
        region_id = region.get("GEOID", idx)
        results.append({
            "region_id": region_id,
            "wbgt": region_wbgt,
            "geometry": region_geom
        })
    
    result_gdf = gpd.GeoDataFrame(results, crs="EPSG:4326")
    return result_gdf
