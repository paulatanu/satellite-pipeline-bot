import streamlit as st
import ee
import geemap.foliumap as geemap
import json
import os
from datetime import datetime

# Set up page config
st.set_page_config(layout="wide", page_title="Satellite Change Detection")
st.title("🛰️ Satellite Change Detection - West Bengal")

# 1. Authenticate GEE
def authenticate_ee():
    try:
        if 'EE_KEY' in os.environ:
            key_dict = json.loads(os.environ['EE_KEY'])
            # Use the project_id from your JSON key
            project_id = key_dict.get('project_id') 
            credentials = ee.ServiceAccountCredentials(key_dict['client_email'], key_string=json.dumps(key_dict))
            ee.Initialize(credentials, project=project_id)
        else:
            st.error("EE_KEY not found in environment variables. Please check your Secrets.")
            st.stop()
    except Exception as e:
        st.error(f"Authentication failed: {e}")
        st.stop()

authenticate_ee()

# 2. Sidebar Controls
with st.sidebar:
    st.header("Custom Settings")
    roi_coords = st.text_input("Coordinates (Lon, Lat)", "87.2697, 21.9507") # Default: Dantan
    
    # We set default dates so the app doesn't start with a 'None' error
    date_before = st.date_input("Select 'Before' Date", value=datetime(2023, 1, 1))
    date_after = st.date_input("Select 'After' Date", value=datetime(2024, 1, 1))
    
    threshold = st.slider("Change Threshold (Sensitivity)", 0.0, 0.5, 0.1, help="Higher = less sensitive to small changes")

# 3. GIS Logic
if date_before and date_after:
    try:
        lon, lat = map(float, roi_coords.split(","))
        roi = ee.Geometry.Point([lon, lat]).buffer(5000)

        def get_ndbi(date_obj):
            # Convert Python date to string for EE
            date_str = date_obj.strftime('%Y-%m-%d')
            ee_date = ee.Date(date_str)
            end_date = ee_date.advance(1, 'month')
            
            img = ee.ImageCollection("COPERNICUS/S2_HARMONIZED")\
                    .filterBounds(roi)\
                    .filterDate(ee_date, end_date)\
                    .sort('CLOUDY_PIXEL_PERCENTAGE')\
                    .first()
            
            # NDBI = (SWIR - NIR) / (SWIR + NIR)
            return img.normalizedDifference(['B11', 'B8'])

        # Calculate Images
        before_img = get_ndbi(date_before)
        after_img = get_ndbi(date_after)
        
        # Calculate Change
        change = after_img.subtract(before_img)
        urban_growth = change.gt(threshold).selfMask()

        # 4. Map Visualization
        st.subheader(f"Analysis: {date_before} vs {date_after}")
        Map = geemap.Map(center=[lat, lon], zoom=13)
        
        # Add layers
        Map.addLayer(before_img, {'min': -0.5, 'max': 0.5, 'palette': ['blue', 'white', 'green']}, 'Before NDBI')
        Map.addLayer(after_img, {'min': -0.5, 'max': 0.5, 'palette': ['blue', 'white', 'red']}, 'After NDBI')
        Map.addLayer(urban_growth, {'palette': 'yellow'}, 'Detected Growth (Yellow)')
        
        # Display Map
        Map.to_streamlit(height=700)
        
    except Exception as e:
        st.warning(f"No clear imagery found for these dates or area. Try adjusting dates. Error: {e}")
