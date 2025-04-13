import folium
from folium.features import GeoJsonTooltip
import matplotlib.pyplot as plt
from io import BytesIO
import base64

def makemap(bbox, ds, variable):
    """
    Display a variable from an xarray Dataset on an interactive folium base map.
    
    Parameters:
      bbox     : tuple (min_lon, min_lat, max_lon, max_lat)
      ds       : xarray Dataset containing the variable data
      variable : string, the name of the variable to display
      
    Returns:
      m : folium.Map object with the data overlaid.
    """
    # Extract the data array; if there is a time dimension, take the first slice.
    da = ds[variable]
    if 'time' in da.dims:
        da = da.isel(time=0)
    elif 'valid_time' in da.dims:
        da = da.isel(valid_time=0)
    
    # Convert the DataArray to a numpy array.
    data = da.values

    # Unpack the bounding box.
    min_lon, min_lat, max_lon, max_lat = bbox

    # Create a matplotlib figure (without axes) to plot the data.
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    ax.axis('off')
    
    # Plot the data with a colormap; specify extent so the image matches the bbox.
    # The extent for imshow is [min_lon, max_lon, min_lat, max_lat].
    ax.imshow(data, cmap='viridis', origin='upper', extent=[min_lon, max_lon, min_lat, max_lat])
    plt.tight_layout(pad=0)

    # Save the figure to a BytesIO object.
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
    buf.seek(0)
    plt.close(fig)

    # Encode the image to base64.
    img_data = base64.b64encode(buf.read()).decode('utf-8')
    data_url = f"data:image/png;base64,{img_data}"

    # Determine the map center.
    center_lat = (min_lat + max_lat) / 2.0
    center_lon = (min_lon + max_lon) / 2.0

    # Create a folium Map centered on the bounding box.
    m = folium.Map(location=[center_lat, center_lon], zoom_start=8)

    # Define the overlay bounds as [[south, west], [north, east]].
    bounds = [[min_lat, min_lon], [max_lat, max_lon]]
    
    # Add the image overlay to the map.
    folium.raster_layers.ImageOverlay(image=data_url, bounds=bounds, opacity=0.6).add_to(m)
    folium.LayerControl().add_to(m)
    
    return m

def make_county_choropleth(wbgt_counties, value_field="wbgt", geojson_field="region_id", zoom_start=5):
    """
    Create an interactive folium choropleth map of counties.

    Parameters:
      wbgt_counties: geopandas.GeoDataFrame
          Output from spatial.join_wbgt_to_geography containing county geometries,
          a unique identifier (default in field 'region_id'), and a weighted WBGT value.
      value_field: str
          Name of the field in wbgt_counties to use for the choropleth (default "wbgt").
      geojson_field: str
          The field name for the region identifier to join on (default "region_id").
      zoom_start: int
          Initial zoom level for the folium map.

    Returns:
      folium.Map: An interactive folium map with a choropleth overlay.
    """
    # Calculate the center of the map from total bounds.
    # total_bounds returns: [minx, miny, maxx, maxy]
    bounds = wbgt_counties.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2.0
    center_lon = (bounds[0] + bounds[2]) / 2.0
    map_center = [center_lat, center_lon]
    
    # Create a base folium map.
    m = folium.Map(location=map_center, zoom_start=zoom_start)
    
    # Convert the counties GeoDataFrame to a GeoJSON string.
    counties_geojson = wbgt_counties.to_json()
    
    # Add a choropleth layer.
    folium.Choropleth(
        geo_data=counties_geojson,
        data=wbgt_counties,
        columns=[geojson_field, value_field],
        key_on=f'feature.properties.{geojson_field}',
        fill_color='YlOrRd',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='Weighted WBGT'
    ).add_to(m)
    
    # Optionally add a GeoJson layer with a tooltip for more interactivity.
    tooltip = GeoJsonTooltip(
        fields=[geojson_field, value_field],
        aliases=[f"{geojson_field.upper()}", "WBGT"],
        localize=True
    )
    
    folium.GeoJson(
        counties_geojson,
        name="County Boundaries",
        tooltip=tooltip,
        style_function=lambda feature: {
            "color": "black",
            "weight": 1,
            "fillOpacity": 0
        }
    ).add_to(m)
    
    folium.LayerControl().add_to(m)
    
    return m