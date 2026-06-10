import os
import glob
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

# =========================================================================
# 1. EXACT PATH CONFIGURATIONS
# =========================================================================
# Direct path to your baseline rainfall file (mm/day)
baseline_raster_path = r"D:\Gifford\IOM\00_ClimateData\00_Cordex_RCMs\Fiji\Baseline\Fiji_Mean_RX1day_SelectedMonths_25km_Degrees_historical_MOHC-HadGEM2-ES_1971-01-01_2000-12-30.tif"

# Path to the folder containing your absolute future rainfall scenarios (mm/day)
# (The folder containing the files that were giving you values over 100)
future_scenarios_dir = r"D:\Gifford\IOM\00_ClimateData\00_Cordex_RCMs\Fiji\HadGEM"

# Destination folder for your clean, normalized decimal Percent Increase outputs
output_dir           = r"D:\Gifford\IOM\00_ClimateData\02_Percent_Change\00_RCMs\Fiji\HadGEM"

os.makedirs(output_dir, exist_ok=True)


def calculate_percent_increase_layers(baseline_path, future_dir, out_dir):
    # Find all future scenario .tif rasters
    search_path = os.path.join(future_dir, "*.tif")
    future_rasters = glob.glob(search_path)
    
    if not future_rasters:
        print(f"No future rasters found in: {future_dir}")
        return
        
    if not os.path.exists(baseline_path):
        print(f"Baseline master raster not found at: {baseline_path}")
        return

    print(f"Found {len(future_rasters)} future scenarios to compare against baseline.")
    print("MODE: Extraction of Relative Percent Increase (Decimal Scale: e.g., 0.60 = 60%)")
    print("-" * 60)

    for fut_path in future_rasters:
        fut_filename = os.path.basename(fut_path)
        scenario_tag = os.path.splitext(fut_filename)[0]
        
        print(f"Processing Percent Increase for: {scenario_tag}")

        # ---------------------------------------------------------------------
        # STEP 1: Dynamically isolate the finest grid resolution layout
        # ---------------------------------------------------------------------
        with rasterio.open(baseline_path) as base_src:
            base_res = abs(base_src.res[0])
        with rasterio.open(fut_path) as fut_src:
            fut_res = abs(fut_src.res[0])
            
        template_path = baseline_path if base_res < fut_res else fut_path
        
        with rasterio.open(template_path) as template_src:
            meta_blueprint = template_src.meta.copy()
            template_crs = template_src.crs
            template_transform = template_src.transform
            width = template_src.width
            height = template_src.height

        # ---------------------------------------------------------------------
        # STEP 2: Project/Align Baseline data to the fine blueprint
        # ---------------------------------------------------------------------
        baseline_grid = np.empty((height, width), dtype=np.float32)
        with rasterio.open(baseline_path) as base_src:
            reproject(
                source=rasterio.band(base_src, 1),
                destination=baseline_grid,
                src_transform=base_src.transform,
                src_crs=base_src.crs,
                dst_transform=template_transform,
                dst_crs=template_crs,
                resampling=Resampling.nearest,
                src_nodata=base_src.nodata,
                dst_nodata=np.nan
            )

        # ---------------------------------------------------------------------
        # STEP 3: Project/Align Future Scenario data to the fine blueprint
        # ---------------------------------------------------------------------
        future_grid = np.empty((height, width), dtype=np.float32)
        with rasterio.open(fut_path) as fut_src:
            reproject(
                source=rasterio.band(fut_src, 1),
                destination=future_grid,
                src_transform=fut_src.transform,
                src_crs=fut_src.crs,
                dst_transform=template_transform,
                dst_crs=template_crs,
                resampling=Resampling.nearest,
                src_nodata=fut_src.nodata,
                dst_nodata=np.nan
            )

        # ---------------------------------------------------------------------
        # STEP 4: Calculate Percent Increase with Ocean/Zero Protections
        # ---------------------------------------------------------------------
        # Clean out absolute NoData flags (-9999) so they don't break our math
        baseline_grid[baseline_grid == -9999.0] = np.nan
        future_grid[future_grid == -9999.0] = np.nan
        
        # Formula: (Future - Baseline) / Baseline
        # np.errstate prevents python from crashing over ocean dividing by zero
        with np.errstate(divide='ignore', invalid='ignore'):
            percent_increase_grid = (future_grid - baseline_grid) / baseline_grid
            
            # Clip negative shifts to 0 if you ONLY want to map absolute INCREASE.
            # Comment out the line below if you want to allow negative values (decreases)
            percent_increase_grid = np.where(percent_increase_grid < 0, 0, percent_increase_grid)

        # ---------------------------------------------------------------------
        # STEP 5: Re-mask NoData Boundaries and Export
        # ---------------------------------------------------------------------
        meta_blueprint.update({
            "driver": "GTiff",
            "dtype": "float32",
            "count": 1,
            "nodata": -9999.0
        })
        
        # Swap NaNs back to standard GIS NoData values
        percent_increase_grid[np.isnan(percent_increase_grid)] = -9999.0
        percent_increase_grid[np.isinf(percent_increase_grid)] = -9999.0

        # Debug print statement to verify the output scale matches your expectations
        valid_data = percent_increase_grid[percent_increase_grid != -9999.0]
        if len(valid_data) > 0:
            print(f" -> Scale Check: Min Increase = {valid_data.min():.4f} | Max Increase = {valid_data.max():.4f}")
        
        # Save output file
        output_filename = f"Fiji_Percent_Increase_{scenario_tag.replace('Fiji_Future_Daily_Rainfall_', '')}.tif"
        final_output_path = os.path.join(out_dir, output_filename)
        
        with rasterio.open(final_output_path, "w", **meta_blueprint) as dst:
            dst.write(percent_increase_grid.astype(np.float32), 1)
            
        print(f" -> SUCCESS: Exported clean decimal map to {output_filename}")
        print("-" * 50)

    print("=" * 60)
    print("ALL PERCENT INCREASE RASTERS COMPLETED!")
    print(f"Saved outputs available here:\n{out_dir}")
    print("=" * 60)

# Run the calculation script
calculate_percent_increase_layers(baseline_raster_path, future_scenarios_dir, output_dir)