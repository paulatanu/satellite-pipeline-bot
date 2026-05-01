import streamlit as st
import ee
import geemap
import json
import os
from datetime import datetime

# Set up page config
st.set_page_config(layout="wide", page_title="Satellite Change Detection")
st.title("🛰️ Satellite Change Detection - West Bengal")

# 1. Authenticate GEE with specific secret matching check
def authenticate_ee():
    try:
        # Check if the secret exists in Streamlit/GitHub environment
        if 'EARTH_ENGINE_KEY' in os.environ:
            secret_content = os.environ['EARTH_ENGINE_KEY']
            
            try:
                key_dict = json.loads(secret_content)
            except json.JSONDecodeError:
                st.error("❌ The secret 'EARTH_ENGINE_KEY' is not a valid JSON. Check for missing braces { }.")
                st.stop()
                
            project_id = key_dict.get('project_id') # Will fetch 'ee-atanupaul'
            credentials = ee.ServiceAccountCredentials(key_dict['client_email'], key_string=json.dumps(key_dict))
            ee.Initialize(credentials, project=project_id)
        else:
            st.warning("⚠️ Secret Mismatch: Could not find 'EARTH_ENGINE_KEY'. Ensure your Streamlit Secret is named exactly this.")
            st.stop()
    except Exception as e:
        st.error(f"❌ Authentication failed: {e}")
        st.stop()

# Run authentication immediately
authenticate_ee()

# 2. Sidebar Controls
with st.sidebar:
    st.header("Custom Settings")
    roi_coords = st.text_input("Coordinates (Lon, Lat)", "87.2697, 21.9507") # Default: Dantan
    date_before = st.date_input("Select 'Before' Date", value=datetime(2023, 1, 1))
    date_after = st.date_input("Select 'After' Date", value=datetime(2024, 1, 1))
    threshold = st.slider("Change Threshold (Sensitivity)", 0.0, 0.5, 0.1)

# 3. GIS Logic
if date_before and date_after:
    with st.spinner('Processing Satellite Data...'):
        try:
            lon, lat = map(float, roi_coords.split(","))
            roi = ee.Geometry.Point([lon, lat]).buffer(5000)

            def get_ndbi(date_obj):
                date_str = date_obj.strftime('%Y-%m-%d')
                ee_date = ee.Date(date_str)
                # Fetch Sentinel-2, filter clouds, and calculate NDBI
                img = ee.ImageCollection("COPERNICUS/S2_HARMONIZED")\
                        .filterBounds(roi)\
                        .filterDate(ee_date, ee_date.advance(1, 'month'))\
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
            st.subheader(f"Urban Growth Detection: {date_before} vs {date_after}")
            Map = geemap.Map(center=[lat, lon], zoom=13)
            
            # Add Layers
            Map.addLayer(before_img, {'min': -0.5, 'max': 0.5, 'palette': ['blue', 'white', 'green']}, 'Before NDBI')
            Map.addLayer(after_img, {'min': -0.5, 'max': 0.5, 'palette': ['blue', 'white', 'red']}, 'After NDBI')
            Map.addLayer(urban_growth, {'palette': 'yellow'}, 'Detected Growth (Yellow)')
            
            # Render to Streamlit
            Map.to_streamlit(height=700)
            
        except Exception as e:
            st.warning(f"Analysis failed. Ensure cloud-free images exist for these dates. Error: {e}")
