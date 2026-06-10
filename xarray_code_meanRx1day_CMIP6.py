import xarray as xr
import rioxarray
import geopandas as gpd
import time
from rasterio.enums import Resampling
import warnings

# Silence the multiple fill values serialization warning from NetCDF
warnings.filterwarnings("ignore", category=UserWarning, module="xarray.conventions")

# --- Settings ---
file_path = r"D:\Gifford\IOM\00_ClimateData\00 Historical GCM\Raw_Historical\EC-Earth3-CC\*.nc" 
shapefile_path = r"D:\Gifford\IOM\Fiji\Administrative Boundary\UN OCHA\Projected\fji_polbnda_adm3_tikina_Projected.shp"
start_year = "1970"
end_year = "2000"

def get_time():
    return time.strftime("%H:%M:%S")

print(f"[{get_time()}] --- Starting CMIP6 Mean RX1day Processing ---")

# 1. Load the Shapefile Geometry and Projection
print(f"[{get_time()}] Step 1: Loading shapefile and extracting target CRS...")
gdf = gpd.read_file(shapefile_path)
target_crs = gdf.crs  
print(f"[{get_time()}] Target CRS detected: {target_crs.to_string()}")

# 2. Open CMIP6 Dataset 
print(f"[{get_time()}] Step 2: Opening CMIP6 dataset...")
ds = xr.open_mfdataset(
    file_path, 
    chunks={"time": -1}, 
    parallel=True, 
    data_vars="minimal"
)

# Print native resolution info
native_lat_res = abs(ds.lat.diff("lat").values[0])
native_lon_res = abs(ds.lon.diff("lon").values[0])
print(f"[{get_time()}] Detected Native GCM Resolution: {native_lat_res:.4f}° x {native_lon_res:.4f}°")

# 3. Slice Years AND Filter for Wet Season (November to April)
print(f"[{get_time()}] Step 3: Slicing years {start_year}-{end_year} and filtering for wet season...")
years_subset = ds.sel(time=slice(start_year, end_year))

wet_season_months = [11, 12, 1, 2, 3, 4]
wet_season_ds = years_subset.sel(time=years_subset.time.dt.month.isin(wet_season_months))

# 4. Unit Conversion to mm/day
print(f"[{get_time()}] Step 4: Converting precipitation units to mm/day...")
wet_season_mm = wet_season_ds["pr"] * 86400

# 5. Calculate Annual RX1day and then find the 30-Year Mean
print(f"[{get_time()}] Step 5: Calculating annual RX1day, then averaging over 1970-2000...")
# Group by year and pull the maximum value for each year block
annual_rx1day = wet_season_mm.groupby("time.year").max(dim="time")

# Take the average of those annual maximums across the 'year' dimension
mean_rx1day = annual_rx1day.mean(dim="year")

# 6. Handle Initial NetCDF Spatial Dimensions
print(f"[{get_time()}] Step 6: Setting up initial native CRS...")
mean_rx1day = mean_rx1day.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=True)
mean_rx1day.rio.write_crs("EPSG:4326", inplace=True)

# 7. Reproject to Shapefile CRS (Native Resolution Preserved)
print(f"[{get_time()}] Step 7: Reprojecting raster to match shapefile CRS...")
reprojected_grid = mean_rx1day.rio.reproject(
    target_crs,
    resampling=Resampling.bilinear
)

# 8. Clip to the Shapefile's TOTAL BOUNDING BOX Window
print(f"[{get_time()}] Step 8: Slicing to the shapefile's rectangular bounding box...")
minx, miny, maxx, maxy = gdf.total_bounds

final_bounded = reprojected_grid.rio.clip_box(
    minx=minx, 
    miny=miny, 
    maxx=maxx, 
    maxy=maxy
)

# 9. Save
output_filename = f"Fiji_Mean_RX1day_{start_year}_{end_year}_ECEarth3CC.tif"
print(f"[{get_time()}] Step 9: Saving final GeoTIFF to {output_filename}...")
final_bounded.rio.to_raster(
    output_filename,
    compress="lzw",
    tiled=True,
    windowed=True
)

print(f"[{get_time()}] --- Done! Average RX1day raster saved successfully ---")