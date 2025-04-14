import os
import geopandas as gpd
import xarray as xr
import numpy as np
from shapely.geometry import box
from typing import Union, Sequence

def join_wbgt_to_geography(
    data: Union[xr.DataArray, xr.Dataset],
    geo_type: str = "county",
    var_names: Sequence[str] = None
) -> gpd.GeoDataFrame:
    """
    Spatially join gridded variables (e.g. WBGT, MRT, T2m) to Census regions.

    Parameters:
      data : xr.DataArray or xr.Dataset
        If DataArray, must have dims 'latitude' and 'longitude' and name (will
        default to 'wbgt' if name is None).  If Dataset, must contain one or more
        data_vars with dims ('latitude','longitude') plus optionally extra dims
        like 'valid_time'.
      geo_type : str
        'county' or 'tract'.
      var_names : sequence of str, optional
        Which data_vars in the Dataset to process.  If None and `data` is a
        Dataset, all data_vars will be used.  Ignored if `data` is a DataArray.

    Returns:
      GeoDataFrame with columns:
        region_id, <each var_name>, geometry
    """
    # load the shapefile
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    if geo_type == "county":
        shp = "cb_2023_us_county_5m/cb_2023_us_county_5m.shp"
    elif geo_type == "tract":
        shp = "cb_2023_us_tract_5m/cb_2023_us_tract_5m.shp"
    else:
        raise ValueError("geo_type must be 'county' or 'tract'")
    regions = gpd.read_file(os.path.join(base_dir, shp)).to_crs("EPSG:4326")

    # normalize input into a Dataset + select vars
    if isinstance(data, xr.DataArray):
        name = data.name or "wbgt"
        ds = data.to_dataset(name=name)
        vars_to_do = [name]
    elif isinstance(data, xr.Dataset):
        ds = data
        vars_to_do = list(ds.data_vars) if var_names is None else list(var_names)
        missing = set(vars_to_do) - set(ds.data_vars)
        if missing:
            raise KeyError(f"Dataset does not contain variables: {missing}")
    else:
        raise TypeError("`data` must be an xarray DataArray or Dataset")

    # extract grid cell centers
    lats = ds["latitude"].values
    lons = ds["longitude"].values
    if len(lats) < 2 or len(lons) < 2:
        raise ValueError("Need at least two latitudes and longitudes to infer cell size")
    dlat = abs(lats[1] - lats[0])
    dlon = abs(lons[1] - lons[0])

    # build cell polygons
    polys = [
        box(lon - dlon/2, lat - dlat/2, lon + dlon/2, lat + dlat/2)
        for lat in lats for lon in lons
    ]

    # assemble a GeoDataFrame of the grid, collapsing extra dims by max()
    grid_dict = {"geometry": polys}
    for var in vars_to_do:
        da = ds[var]
        extra = [d for d in da.dims if d not in ("latitude", "longitude")]
        if extra:
            da = da.max(dim=extra)
        grid_dict[var] = da.values.ravel()
    grid = gpd.GeoDataFrame(grid_dict, crs="EPSG:4326")

    # reproject to an equal‐area CRS for accurate area calculations
    ea_crs = "EPSG:2163"  # US National Atlas Equal Area
    regions_ea = regions.to_crs(ea_crs)
    grid_ea    = grid.to_crs(ea_crs)

    # loop over regions, compute weighted averages
    results = []
    for idx, region in regions_ea.iterrows():
        mask  = grid_ea.intersects(region.geometry)
        sub_ea = grid_ea[mask]
        if sub_ea.empty:
            continue

        cell_area  = sub_ea.geometry.area
        inter_area = sub_ea.geometry.intersection(region.geometry).area
        weights    = inter_area / cell_area

        if weights.sum() == 0:
            vals = {var: np.nan for var in vars_to_do}
        else:
            vals = {
                var: (sub_ea[var] * weights).sum() / weights.sum()
                for var in vars_to_do
            }

        # use the original geographic geometry for output
        orig_geom = regions.loc[idx, "geometry"]
        region_id = regions.loc[idx].get("GEOID", None)
        row = {"region_id": region_id, **vals, "geometry": orig_geom}
        results.append(row)

    # build result GeoDataFrame in EPSG:4326
    result_gdf = gpd.GeoDataFrame(results, crs="EPSG:4326")
    return result_gdf
