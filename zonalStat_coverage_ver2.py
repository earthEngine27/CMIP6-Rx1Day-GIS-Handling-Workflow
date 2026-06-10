import os
import geopandas as gpd
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from exactextract import exact_extract

# 1. Define your file paths
raster_path = r"D:\Gifford\IOM\00_ClimateData\02_Percent_Change\00_RCMs\Vanuatu_meanDailyRain\NorESM\Vanuatu_Percent_Change_Vanuatu_Mean_Rainfall_SelectedMonths_25km_RCP85_NCC-NorESM1-M_2080-01-01_2099-12-30.tif"
vector_path = r"D:\Gifford\IOM\Vanuatu\Rain\Rainfall_Extreme\Vanuatu_VMGDStations_AdjustedExtremeRain_01Jun2026_StationID_Province_ClimateRescaled.shp"
output_path = r"D:\Gifford\IOM\00_ClimateData\03_Catchment_Change\Vanuatu_RCMs_meanDailyRain\Vanuatu_Average_DailyRain_NCC-NorESM1-M_PercentChange_RCP85_2080_2099.shp"

# Setting up a physical temporary file path for the reprojected raster
temp_raster_path = r"D:\Gifford\IOM\cordex\temp_reprojected.tif"

def calculate_overlap_average_to_shp(raster_p, vector_p, out_p, temp_p):
    print("Loading vector dataset...")
    polygons = gpd.read_file(vector_p)
    target_crs = polygons.crs
    
    reprojected_created = False
    
    print("Opening raster dataset...")
    with rasterio.open(raster_p) as src:
        if src.crs != target_crs:
            print(f"CRS mismatch detected! Raster: {src.crs} | Vector: {target_crs}")
            print(f"Reprojecting raster using Nearest Neighbor to preserve raw values...")
            
            transform, width, height = calculate_default_transform(
                src.crs, target_crs, src.width, src.height, *src.bounds
            )
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': target_crs,
                'transform': transform,
                'width': width,
                'height': height
            })
            
            with rasterio.open(temp_p, 'w', **kwargs) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=target_crs,
                        # CHANGED: Preserves exact original pixel values during grid shift
                        resampling=Resampling.nearest 
                    )
            reprojected_created = True
            
            print("Calculating exact pixel overlap statistics...")
            stats_df = exact_extract(temp_p, polygons, ['mean'], output="pandas")
        else:
            print("CRS matches perfectly. No projection needed.")
            print("Calculating exact pixel overlap statistics...")
            stats_df = exact_extract(raster_p, polygons, ['mean'], output="pandas")
        
    print("Appending statistics to geometry...")
    mean_col = [col for col in stats_df.columns if 'mean' in col]
    
    if not mean_col:
        raise ValueError("Could not find a 'mean' column in exact_extract output.")
    
    polygons['ovr_avg'] = stats_df[mean_col].iloc[:, 0].values
    
    print("Writing final Shapefile...")
    polygons.to_file(out_p, driver="ESRI Shapefile")
    print(f"Success! Shapefile with overlap statistics saved to: {out_p}")
    
    if reprojected_created and os.path.exists(temp_p):
        try:
            os.remove(temp_p)
            print("Temporary spatial file successfully cleared.")
        except Exception as e:
            print(f"Could not automatically delete temporary file: {e}")

# Run the function
calculate_overlap_average_to_shp(raster_path, vector_path, output_path, temp_raster_path)