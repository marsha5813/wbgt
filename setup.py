# setup.py
from setuptools import setup, find_packages

setup(
    name="wbgt",
    version="0.1.0",
    description="Calculate WBGT estimates from ERA5 reanalysis data for US geographies.",
    author="Joey Marshall",
    author_email="joeymarshall@live.com",
    packages=find_packages(), 
    install_requires=[
        "cdsapi",
        "xarray",
        "numpy",
        "geopandas",
        "requests",
        "io",
        "os",
        "zipfile",
        "typing",
        "tempfile",
        "shutil",
        "shapely",
        "pandas",
        "dask",
        "netCDF4",
        "matplotlib",
        "base64",
        "contextily",
        "folium",
        "scipy"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)
