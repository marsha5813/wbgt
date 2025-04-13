# WBGT

WBGT is a Python package to retrieve Wet Bulb Globe Temperatures for the United States: either the entire nation, or a single state, county or Census tract. WBGT will optionally return the data on a ~32km grid or assign values to counties or tracts by proportionally allocating gridded values to the county or tract geometries.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Setting Up Your CDS API Key](#setting-up-your-cds-api-key)
  - [Installing via pip](#installing-via-pip)
- [Usage](#usage)
- [Function Details](#function-details)
- [Contributing](#contributing)
- [License](#license)
- [Roadmap](#roadmap)

## Overview

WBGT simplifies the process for computing WBGT values by retrieving the necessary climate components (air temperature, wind speed, dewpoint temperature and mean radiant temperature) from the relevant API endpoints, calculating the necessary components, and (optionally) spatially joining the results to Census geographies.

WBGT is designed to retrieve one month of data (e.g., July 2023). It will return the daily values for every day in the requested month, or it can optionally return the max WBGT for the month. 

This package is indebted to [thermofeel](https://github.com/ecmwf/thermofeel), a Python library that calculates thermal comfort indices laid out in [this paper](https://www.sciencedirect.com/science/article/pii/S2352711022000176). Thanks to thermofeel, WBGT is able to utilize the [Brimicombe approximation](https://pubmed.ncbi.nlm.nih.gov/36825116/) to Wet Bulb Globe Temperatures, widely regarded as the best approximation that uses metrics available in the [ERA5 Climate reanalysis data](https://www.ecmwf.int/en/forecasts/dataset/ecmwf-reanalysis-v5).

## Installation

### Prerequisites

- Python 3.7 or newer
- A CDS API Key

### Setting Up Your CDS API Key

Before using WBGT, you must set up your CDS API key to download climate reanalysis data. Follow these steps:

1. **Obtain a CDS API Key:**
   - Visit the [Copernicus Climate Data Store](https://cds.climate.copernicus.eu) website.
   - Follow the detailed instructions provided in this [CDS API key setup tutorial](https://ecmwf-projects.github.io/copernicus-training-c3s/cds-tutorial.html#install-the-cds-api-key).
   - Log in to the CDS website via your web browser and accept the necessary licenses.

2. **Configure Your CDS API Key:**
   - Once you have your API key, create a file named `.cdsapirc` in your home directory.
   - Add your API key details in the following format:
     ```yaml
     url: https://cds.climate.copernicus.eu/api/v2
     key: YOUR-UID:YOUR-API-KEY
     ```

### Installing `wbgt` via pip

You can install WBGT directly from GitHub using pip:

```bash
pip install git+https://github.com/marsha5813/wbgt.git
```

### Usage

The package exposes a single primary function, `get_wbgt`, which allows you to retrieve WBGT data based on your geographical and temporal requirements. For example:

```python
import wbgt

# Example 1: Retrieve daily WBGT for the state of Maryland (FIPS "24") for July 2023 with output on the ~32km ERA5 grid
wbgt_data_md_grid = wbgt.get_wbgt(
    geo_limit="state",
    geo_limit_fips = "24",
    output_type="grid",
    month=7,
    year=2023,
    max=False
)

# wbgt_data will be an xarray DataArray if output_type is "grid"
print(wbgt_data_md_grid)

# Example 2: Retrieve maximum WBGT for the state of Maryland (FIPS "24") for July 2023 with WBGT values assigned to counties
wbgt_data_md_counties = wbgt.get_wbgt(
    geo_limit="state",
    geo_limit_fips = "24",
    output_type="counties",
    month=7,
    year=2023,
    max=True
)

# Example 3: Retrieve maximum WBGT for the entire United States for July 2023 with WBGT values assigned to Census tracts
wbgt_data_us_tracts = wbgt.get_wbgt(
    geo_limit="nation",
    geo_limit_fips = None,
    output_type="tracts",
    month=7,
    year=2023,
    max=True
)
````

This function downloads the required ERA5 reanalysis data, computes daily WBGT values and their monthly maximums, and then optionally joins the data to Census geometries (county or tract) based on your specified output format.

### Function details
The `get_wbgt` function signature is:

```python
def get_wbgt(geo_limit: str, geo_limit_fips: str, output_type: str,
             month: int, year: int, max: bool = True):
    """
    Retrieve Wet Bulb Globe Temperature (WBGT) data for a specified geography and time period.

    Parameters:
      geo_limit (str): One of "nation", "state", "county", or "tract". Determines the spatial extent.
                       If "nation", a bounding box covering the entire United States (including Alaska and Hawaii) is used.
      geo_limit_fips (str): The FIPS code for the specified geography (e.g., "24" for Maryland).
                            Set to None if geo_limit is "nation".
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
```

### Contributing
Contributions to WBGT are welcome! If you have any ideas, bug reports, or improvements, please open an issue or submit a pull request.

### License
WBGT is open-source software released under the MIT License.

### Roadmap
- Currently, the Cartographic Boundary Files are included in the repo due to problems with FTP requests from Census. This should eventually be converted into querying the map server.