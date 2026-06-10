import os
import glob
import re
import geopandas as gpd
import pandas as pd

# 1. Define your folders
input_folder = r"D:\Gifford\IOM\00_ClimateData\03_Catchment_Change\Vanuatu_RCMs_meanDailyRain\NorESM"
output_folder = r"D:\Gifford\IOM\00_ClimateData\04_Final\Vanuatu_RCMs_MeanDailyRain\NorESM"

os.makedirs(output_folder, exist_ok=True)

def batch_process_every_single_shp(in_dir, out_dir):
    search_path = os.path.join(in_dir, "*.shp")
    shapefiles = glob.glob(search_path)
    
    if not shapefiles:
        print(f"No shapefiles found in {in_dir}")
        return

    base_gdf = None
    wide_data_dict = {}
    cols_to_drop = ["Watershed", "Incharge", "Province"]
    
    print(f"Found {len(shapefiles)} shapefiles in the directory to process.\n" + "-"*50)
    
    for shp_path in shapefiles:
        filename = os.path.basename(shp_path)
        print(f"Processing File: {filename}")
        
        polygons = gpd.read_file(shp_path)
        
        # Verify required math columns exist
        historical_cols = ['Yr005', 'Yr025', 'Yr100', 'ovr_avg']
        missing_cols = [col for col in historical_cols if col not in polygons.columns]
        if missing_cols:
            print(f" -> Skipping {filename}: Missing required columns {missing_cols}")
            print("-" * 30)
            continue
            
        base_name_no_ext = os.path.splitext(filename)[0]
        
        # --- 1. DYNAMIC REGEX DETECTION FOR SCENARIO AND HORIZON ---
        # Find RCPxx or SSPxxx (Case-insensitive)
        scenario_match = re.search(r'(RCP\d{2}|SSP\d{3})', base_name_no_ext, re.IGNORECASE)
        # Find any pair of 4-digit years separated by an underscore (e.g., 2020_2045)
        year_match = re.search(r'(\d{4})_(\d{4})', base_name_no_ext)
        
        # Extract values or fall back to defaults if not found
        if scenario_match:
            full_scenario = scenario_match.group(1).upper()                 # e.g., "RCP26"
            # Strip letters to keep it short for column names (e.g., "RCP26" -> "26")
            ssp_short = re.sub(r'[a-zA-Z]', '', full_scenario) 
        else:
            full_scenario = "UNKNOWN"
            ssp_short = "sc"

        if year_match:
            start_year = year_match.group(1)                                # e.g., "2020"
            end_year_full = year_match.group(2)                             # e.g., "2045"
            end_year = end_year_full[-2:]                                   # e.g., "45"
            horizon_str = f"{start_year}_{end_year_full}"                   # e.g., "2020_2045"
        else:
            horizon_str = "UNKNOWN"
            end_year = "ad"
            
        # Build the 10-char safe column prefix (e.g., "26_45_F005")
        prefix = f"{ssp_short}_{end_year}_"  
        
        # Establish the base spatial blueprint from the first valid file
        if base_gdf is None:
            cols_to_keep = [col for col in polygons.columns if col != 'ovr_avg' and col not in cols_to_drop]
            base_gdf = polygons[cols_to_keep].copy()
            base_gdf.reset_index(drop=True, inplace=True)
        
        # --- Run Future Rainfall Math Calculations ---
        f_yr005 = (polygons['Yr005'] * (1 + polygons['ovr_avg'])).round(2).values
        f_yr025 = (polygons['Yr025'] * (1 + polygons['ovr_avg'])).round(2).values
        f_yr100 = (polygons['Yr100'] * (1 + polygons['ovr_avg'])).round(2).values
        
        # --- Create and Save the Cleaned Individual Shapefile ---
        individual_gdf = polygons.copy()
        individual_gdf[f"{prefix}F005"] = f_yr005
        individual_gdf[f"{prefix}F025"] = f_yr025
        individual_gdf[f"{prefix}F100"] = f_yr100
        
        # Drop unwanted attributes safely
        existing_drop_cols = [col for col in cols_to_drop + ['ovr_avg'] if col in individual_gdf.columns]
        if existing_drop_cols:
            individual_gdf = individual_gdf.drop(columns=existing_drop_cols)
            
        # --- Dynamic Output Naming ---
        # Cleans up naming by pairing the detected scenario and horizon at the end
        if "PercentChange_" in base_name_no_ext:
            prefix_part = base_name_no_ext.split("PercentChange_")[0]
            individual_out_name = f"{prefix_part}PercentChange_{full_scenario}_{horizon_str}.shp"
        else:
            individual_out_name = f"{base_name_no_ext}_{full_scenario}_{horizon_str}.shp"
            
        individual_gdf.to_file(os.path.join(out_dir, individual_out_name), driver="ESRI Shapefile")
        print(f" -> Detected: {full_scenario} | Horizon: {horizon_str}")
        print(f" -> Saved individual file: {individual_out_name}")
        
        # --- Track Columns for the Consolidated Wide Master Shapefile ---
        wide_data_dict[f"{prefix}F005"] = f_yr005
        wide_data_dict[f"{prefix}F025"] = f_yr025
        wide_data_dict[f"{prefix}F100"] = f_yr100
        
        print("-" * 30)

    # --- Horizontal Matrix Combination and Export (Master Summary File) ---
    if base_gdf is not None:
        print("Assembling structured dataframe horizontally into master blueprint...")
        
        calculated_df = pd.DataFrame(wide_data_dict, index=base_gdf.index)
        final_wide_gdf = base_gdf.join(calculated_df)
        
        consolidated_out_path = os.path.join(out_dir, "Vanuatu_Master_Future_Rainfall.shp")
        final_wide_gdf.to_file(consolidated_out_path, driver="ESRI Shapefile")
        
        print("="*50)
        print("SUCCESS! All adaptive files and master layout generated.")
        print(f"Master wide shapefile ready at:\n{consolidated_out_path}")
        print("="*50)
    else:
        print("Error: No valid shapefiles containing required attributes were processed.")

# Run the complete finalized pipeline
batch_process_every_single_shp(input_folder, output_folder)