import streamlit as st
import time
import random
import pandas as pd
import logging
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError

# 1. ENTERPRISE OBSERVABILITY & LOGGING CONFIGURATION
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s]: %(message)s')
logger = logging.getLogger("EtihadFlightOps")

# 2. DATA QUALITY CONTRACT LAYER (Pydantic Schema Gate)
class TelemetryRecord(BaseModel):
    flight_callsign: str = Field(..., min_length=3, description="Official Aviation ATC Registration Number")
    origin_station: str = Field(..., min_length=3, max_length=4, description="Departure IATA/ICAO Code") # ◄── UPDATED: Aviation Terminology
    destination_station: str = Field(..., min_length=3, max_length=4, description="Arrival IATA/ICAO Code") # ◄── ADDED: Destination Contract
    latitude: float = Field(..., ge=15.0, le=35.0)  # Bounded within real UAE flight paths
    longitude: float = Field(..., ge=45.0, le=65.0)
    altitude_feet: int = Field(..., ge=0) # ◄── UPDATED: Aviation units change to Feet

# 3. CONFIGURE INTERFACE SYSTEM LAYOUT
st.set_page_config(
    page_title="Etihad Flight Operations Control Room",
    page_icon="✈️",
    layout="wide"
)

# Custom Style sheets to match an airport radar operations screen
st.markdown("""
    <style>
    .main { background-color: #0b0f19; color: #f3f4f6; }
    div[data-testid="stMetricValue"] { color: #d4af37 !important; font-family: monospace; } /* Etihad Gold Accent Color */
    div[data-testid="stMetricLabel"] { color: #9ca3af !important; text-transform: uppercase; font-size: 11px !important; }
    .dataframe { font-family: monospace !important; background-color: #0f172a !important; }
    </style>
""", unsafe_allow_html=True)

# 4. STATEFUL DATA LAYER MANAGEMENT (With Origin & Destination Flight Tracks)
if "fleet_state" not in st.session_state:
    st.session_state.fleet_state = [
        {"flight_callsign": "EY/ETD151", "origin_station": "AUH", "destination_station": "LHR", "latitude": 24.4539, "longitude": 54.3773, "speed_lat": 0.04, "speed_lon": 0.03, "altitude_feet": 28000},
        {"flight_callsign": "EY/ETD101", "origin_station": "AUH", "destination_station": "JFK", "latitude": 24.1200, "longitude": 53.9500, "speed_lat": -0.03, "speed_lon": 0.05, "altitude_feet": 32000},
        {"flight_callsign": "EK/UAE72",  "origin_station": "DXB", "destination_station": "BOM", "latitude": 25.2048, "longitude": 55.2708, "speed_lat": -0.05, "speed_lon": -0.04, "altitude_feet": 34000},
        {"flight_callsign": "QR/QTR319", "origin_station": "DOH", "destination_station": "CDG", "latitude": 24.8900, "longitude": 54.1200, "speed_lat": 0.02, "speed_lon": -0.06, "altitude_feet": 26000},
        {"flight_callsign": "AI/AIC465", "origin_station": "DEL", "destination_station": "AUH", "latitude": 23.5000, "longitude": 53.2000, "speed_lat": 0.06, "speed_lon": 0.02, "altitude_feet": 36000},
        {"flight_callsign": "MALFORMED_X", "origin_station": "UNKNOWN_HUB", "destination_station": "INVALID_STATION_CODE", "latitude": 5.0, "longitude": 12.0, "speed_lat": 0.0, "speed_lon": 0.0, "altitude_feet": -1500} # ❌ Fails Contract
    ]
    st.session_state.refresh_count = 0
    st.session_state.quarantine_count = 0

# 5. DATAOPS INGESTION PROCESSING ENGINE
st.session_state.refresh_count += 1
clean_records = []

for flight in st.session_state.fleet_state:
    # Update telemetry tracking vectors smoothly
    flight["altitude_feet"] += random.choice([-200, 0, 200])
    flight["latitude"] += flight["speed_lat"]
    flight["longitude"] += flight["speed_lon"]
    
    # Airspace boundary limits
    if not (21.0 <= flight["latitude"] <= 27.0): flight["speed_lat"] *= -1
    if not (51.0 <= flight["longitude"] <= 58.0): flight["speed_lon"] *= -1

    # SCHEMA VALIDATION GATE (Data Quality by Design)
    try:
        validated_data = TelemetryRecord(**flight)
        clean_records.append(validated_data.model_dump())
    except ValidationError as e:
        st.session_state.quarantine_count += 1
        logger.warning(f"Flight Operations Data Drop Deflected: {flight['flight_callsign']} isolated.")

# Convert clean records back to a production dataframe structure
df_clean_lakehouse = pd.DataFrame(clean_records)

# 6. RENDER THE INTERACTIVE APPLICATION UI (Aviation Style Layout)
col_title, col_time = st.columns(2)
with col_title:
    st.markdown("<h2 style='color:#38bdf8;'>✈️ ETIHAD FLIGHT OPERATIONS CENTRE</h2>", unsafe_allow_html=True) # ◄── UPDATED Language
    st.markdown("<p style='color:#4ade80; font-size:13px; font-weight:bold; margin-top:-15px;'>● REAL-TIME DISPATCH FEED ACTIVE</p>", unsafe_allow_html=True)
with col_time:
    st.markdown(f"<p style='text-align:right; color:#9ca3af; font-family:monospace; margin-bottom:0;'>RADAR SWEEPS: {st.session_state.refresh_count}</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:right; color:#e5e7eb; font-family:monospace; margin-top:0;'>🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>", unsafe_allow_html=True)

# Metric Summary Rows
m1, m2, m3, m4 = st.columns(4)
m1.metric("Airborne Sectors Monitored", f"{len(df_clean_lakehouse)} Active") # ◄── UPDATED Language
m2.metric("Telemetry Deflections", f"{st.session_state.quarantine_count} Isolated", delta="-100% Stream Corruption", delta_color="inverse")
m3.metric("Data Engine Layer", "Delta Lakehouse")
m4.metric("File Storage Layout", "Partitioned Columnar")

# Render UI Layout components
tab1, tab2 = st.tabs(["📊 Sector Ingestion Matrix (Silver Tier)", "🌍 Spatial Airspace Visualizer"]) # ◄── UPDATED Language

with tab1:
    st.markdown("<p style='color:#38bdf8; font-size:14px; font-weight:bold;'>Validated, Clean Flight Operations Data Ledger</p>", unsafe_allow_html=True)
    # Displays Originating and Terminating airports side-by-side
    st.dataframe(
        df_clean_lakehouse[["flight_callsign", "origin_station", "destination_station", "latitude", "longitude", "altitude_feet"]].rename(
            columns={"origin_station": "ORIGINATING STATION", "destination_station": "TERMINATING STATION", "altitude_feet": "ALTITUDE (FT)"}
        ), 
        use_container_width=True, 
        hide_index=True
    )

with tab2:
    st.markdown("<p style='color:#38bdf8; font-size:14px; font-weight:bold;'>Real-Time Geographical Transponder Radar Plot</p>", unsafe_allow_html=True)
    df_map = df_clean_lakehouse[["latitude", "longitude"]].rename(columns={"latitude": "lat", "longitude": "lon"})
    st.map(df_map, zoom=6, use_container_width=True)

# 7. AUTOMATED SYSTEM REFRESH TRIGGER LOGIC
time.sleep(3)
st.rerun()
