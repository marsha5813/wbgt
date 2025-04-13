import geopandas as gpd
import requests
from io import BytesIO
from shapely.geometry import box

def get_geography_bbox(geo_type, fips_code):
    """
    Retrieve the bounding box and geometry for a given Census geography
    using TIGERweb GeoServer endpoints (no local shapefiles required).
    
    Parameters:
      geo_type : one of "tract", "county", or "state"
      fips_code: FIPS code string corresponding to the desired geography
      
    Returns:
      bbox : tuple (min_lon, min_lat, max_lon, max_lat)
      geo  : GeoDataFrame row(s) for the requested geography 
      bbox_gdf : GeoDataFrame containing the bounding box geometry in EPSG:4326
    """
    # Define base URL and layer depending on geo_type
    if geo_type == "state":
        url = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/0/query"
    elif geo_type == "county":
        url = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1/query"
    elif geo_type == "tract":
        url = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks/MapServer/0/query"
    else:
        raise ValueError("Invalid geography type. Choose 'tract', 'county', or 'state'.")

    # Query parameters
    params = {
        'where': f"GEOID='{fips_code}'",
        'outFields': '*',
        'f': 'geojson',
        'outSR': '4326'
    }

    # Make the request
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise ValueError(f"Request failed with status {response.status_code}: {response.text}")

    # Read the GeoJSON into a GeoDataFrame
    try:
        geo = gpd.read_file(BytesIO(response.content))
    except Exception as e:
        raise RuntimeError(f"Could not parse GeoJSON: {e}")

    if geo.empty:
        raise ValueError("No geography found with the provided FIPS code.")

    minx, miny, maxx, maxy = geo.total_bounds
    bbox = (minx, miny, maxx, maxy)

    # Create a GeoDataFrame for the bounding box
    bbox_geom = box(minx, miny, maxx, maxy)
    bbox_gdf = gpd.GeoDataFrame(geometry=[bbox_geom], crs="EPSG:4326")

    return bbox, geo, bbox_gdf
