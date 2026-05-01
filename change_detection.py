import ee
import json
import os
import gspread # For Google Sheets
from datetime import datetime

# 1. Authenticate using the Secret Key from GitHub
key_dict = json.loads(os.environ['EE_KEY'])
credentials = ee.ServiceAccountCredentials(key_dict['client_email'], key_string=json.dumps(key_dict))
ee.Initialize(credentials)

# 2. Define ROI (e.g., a coordinate in West Bengal)
roi = ee.Geometry.Point([88.3639, 22.5726]).buffer(5000) # Example: 5km around Kolkata

def get_built_up(start_date, end_date):
    # Fetch Sentinel-2, filter clouds, and calculate NDBI
    img = ee.ImageCollection("COPERNICUS/S2_HARMONIZED")\
            .filterBounds(roi)\
            .filterDate(start_date, end_date)\
            .sort('CLOUDY_PIXEL_PERCENTAGE')\
            .first()
    
    # NDBI = (SWIR - NIR) / (SWIR + NIR)
    ndbi = img.normalizedDifference(['B11', 'B8']).rename('NDBI')
    return ndbi

# 3. Compare Two Timeframes
before = get_built_up('2025-01-01', '2025-02-01')
after = get_built_up('2026-04-01', '2026-05-01')

# 4. Calculate Change
change = after.subtract(before)
# Flag areas where built-up index increased significantly (> 0.1)
urban_growth = change.gt(0.1).selfMask()

# 5. Export result (for now, we print the area of change)
stats = urban_growth.reduceRegion(reducer=ee.Reducer.sum(), geometry=roi, scale=10)
print(f"Detected Urban Growth Area: {stats.getInfo()}")

# 2. Add Google Sheets Logging
def log_to_sheets(pixels, area):
    # Authenticate with the same Service Account key used for EE
    gc = gspread.service_account_from_dict(key_dict)
    sh = gc.open_by_key('YOUR_SHEET_ID_HERE')
    worksheet = sh.get_worksheet(0)
    
    row = [datetime.now().strftime("%Y-%m-%d"), "Dantan", pixels, area]
    worksheet.append_row(row)

# 3. Execution
stats = urban_growth.reduceRegion(reducer=ee.Reducer.sum(), geometry=dantan_roi, scale=10).getInfo()
pixel_count = stats.get('NDBI', 0)
area_sqm = pixel_count * 100 # Sentinel-2 is 10m resolution

log_to_sheets(pixel_count, area_sqm)
