**General Description:**

This code is designed to handle CMIP6 General Circulation Models (GCMs) stored as netCDF files, then apply a nested workflow to filter out wet-season months, extract RX1Day, and quantify the mean RX1Day over a specified time frame. Rioxarray and Rasterio are further incorporated as code dependencies to facilitate data conversion and corresponding spatial projection. 

A dedicated wall-to-wall GeoTIFF data comparison workflow is developed to automate the percent increase in rainfall calculation at the native resolution of GCMs. Such a coding approach directly generates per-pixel rainfall increase that can be further incorporated in calculating future rainfall increase through the delta change method.

Percent increase GeoTIFF file outputs are then distributed into a geospatially-discrete watershed scale using the "exactExtract" tool, overcoming data extraction protocols of conventional zonal statistics found on offline GIS software packages that heavily rely on pixel centroid for calculation execution. This tool enables future-climate-informed rainfall information relevant for high-resolution, watershed-scale two-dimensional numerical simulation of floods.

Finally, this includes a Python-based workflow setup that applies the delta change calculation results to the existing baseline rainfall data, produces individual SHP data for every scenario, and collectively compiles future rainfall events into a single, standalone masterfile SHP.

Development of these coding workflows is supported by the University of the Philippines Resilience Institute through the generous funding support of the International Organization for Migration (IOM). This is part of the larger initiative of producing future climate-informed flood hazard maps to address future climate displacement in the Pacific island countries of Fiji and Vanuatu.
