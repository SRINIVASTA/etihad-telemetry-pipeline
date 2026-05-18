import streamlit as st
import time
import random
import pandas as pd
import logging
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError

# 1. ENTERPRISE OBSERVABILITY & LOGGING CONFIGURATION
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s]: %(message)s')
logger = logging.getLogger("EtihadDataPlatform")

# 2. DATA QUALITY CONTRACT LAYER (Pydantic Schema Gate)
class TelemetryRecord(BaseModel):
    flight_callsign: str = Field(..., min_length=3)
    origin_country: str
    latitude: float = Field(..., ge=15.0, le=35.0)  # Bounded within real aviation tracking vectors
    longitude: float = Field(..., ge=45.0, le=65.0)
    altitude_meters: int = Field(..., ge=0)

# 3. CONFIGURE INTERFACE SYSTEM LAYOUT
st.set_page_config(
    page_title="Etihad Infrastructure Command Center",
    page_icon="✈️",
    layout="wide"
)

# Custom Style sheets to match an airport radar operations screen
st.markdown("""
    <style>
    .main { background-color: #0b0f19; color: #f3f4f6; }
    div[data-testid="stMetricValue"] { color: #38bdf8 !important; font-family: monospace; }
    div[data-testid="stMetricLabel"] { color: #9ca3af !important; text-transform: uppercase; font-size: 11px !important; }
    .dataframe { font-family: monospace !important; background-color: #0f172a !important; }
    </style>
""", unsafe_allow_html=True)

# 4. STATEFUL DATA LAYER MANAGEMENT
if "fleet_state" not in st.session_state:
    st.session_state.fleet_state = [
        {"flight_callsign": "EY/ETD151", "origin_country": "United Arab Emirates", "latitude": 24.4539, "longitude": 54.3773, "speed_lat": 0.04, "speed_lon": 0.03, "altitude_meters": 8500},
        {"flight_callsign": "EY/ETD101", "origin_country": "United Arab Emirates", "latitude": 24.1200, "longitude": 53.9500, "speed_lat": -0.03, "speed_lon": 0.05, "altitude_meters": 9200},
        {"flight_callsign": "EK/UAE72",  "origin_country": "United Arab Emirates", "latitude": 25.2048, "longitude": 55.2708, "speed_lat": -0.05, "speed_lon": -0.04, "altitude_meters": 10500},
        {"flight_callsign": "QR/QTR319", "origin_country": "Qatar", "latitude": 24.8900, "longitude": 54.1200, "speed_lat": 0.02, "speed_lon": -0.06, "altitude_meters": 7400},
        {"flight_callsign": "AI/AIC465", "origin_country": "India", "latitude": 23.5000, "longitude": 53.2000, "speed_lat": 0.06, "speed_lon": 0.02, "altitude_meters": 11200},
        {"flight_callsign": "MALFORMED_X", "origin_country": "Unknown", "latitude": 5.0, "longitude": 12.0, "speed_lat": 0.0, "speed_lon": 0.0, "altitude_meters": -500} # ❌ Intentionally bad entry to test our guard
    ]
    st.session_state.refresh_count = 0
    st.session_state.quarantine_count = 0

# 5. DATAOPS INGESTION PROCESSING ENGINE
st.session_state.refresh_count += 1
clean_records = []

for flight in st.session_state.fleet_state:
    # Update locations smoothly
    flight["altitude_meters"] += random.choice([-20, 0, 20])
    flight["latitude"] += flight["speed_lat"]
    flight["longitude"] += flight["speed_lon"]
    
    # Boundary bounce rules
    if not (21.0 <= flight["latitude"] <= 27.0): flight["speed_lat"] *= -1
    if not (51.0 <= flight["longitude"] <= 58.0): flight["speed_lon"] *= -1

    # SCHEMA VALIDATION GATE (Data Quality by Design)
    try:
        validated_data = TelemetryRecord(**flight)
        clean_records.append(validated_data.model_dump())
    except ValidationError as e:
        st.session_state.quarantine_count += 1
        logger.warning(f"Data Contract Violation Deflected: {flight['flight_callsign']} quarantined. Context: {e.json()}")

# Convert clean records back to a production dataframe structure
df_clean_lakehouse = pd.DataFrame(clean_records)

# 6. RENDER THE INTERACTIVE APPLICATION UI
col_title, col_time = st.columns(2)
with col_title:
    st.markdown("<h2 style='color:#38bdf8;'>✈️ ETIHAD PIPELINE PLATFORM</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#4ade80; font-size:13px; font-weight:bold; margin-top:-15px;'>● PLATFORM PRODUCT CORE ENGINE RUNNING</p>", unsafe_allow_html=True)
with col_time:
    st.markdown(f"<p style='text-align:right; color:#9ca3af; font-family:monospace; margin-bottom:0;'>TOTAL REFRESHES: {st.session_state.refresh_count}</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:right; color:#e5e7eb; font-family:monospace; margin-top:0;'>🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>", unsafe_allow_html=True)

# Metric Summary Rows
m1, m2, m3, m4 = st.columns(4)
m1.metric("Active Streams", f"{len(df_clean_lakehouse)} Tracks")
m2.metric("Deflected Anomalies", f"{st.session_state.quarantine_count} Isolated", delta="-100% Corruption", delta_color="inverse")
m3.metric("Storage Framework", "Delta Lakehouse")
m4.metric("File Optimization", "Partitioned (Col)")

# Render UI Layout components
tab1, tab2 = st.tabs(["📊 Live Ingestion Table (Silver Layer)", "🌍 Airspace Spatial Mapping"])

with tab1:
    st.markdown("<p style='color:#38bdf8; font-size:14px; font-weight:bold;'>Validated, Clean Data Lakehouse Ledger</p>", unsafe_allow_html=True)
    st.dataframe(df_clean_lakehouse[["flight_callsign", "origin_country", "latitude", "longitude", "altitude_meters"]], use_container_width=True, hide_index=True)

with tab2:
    st.markdown("<p style='color:#38bdf8; font-size:14px; font-weight:bold;'>Real-Time Geographical Coordinate Tracking</p>", unsafe_allow_html=True)
    df_map = df_clean_lakehouse[["latitude", "longitude"]].rename(columns={"latitude": "lat", "longitude": "lon"})
    st.map(df_map, zoom=6, use_container_width=True)

# 7. AUTOMATED SYSTEM REFRESH TRIGGER LOGIC
time.sleep(3)
st.rerun()
