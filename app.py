import streamlit as st
import time
import random
import pandas as pd
import logging
import math
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError

# 1. ENTERPRISE OBSERVABILITY & LOGGING CONFIGURATION
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s]: %(message)s')
logger = logging.getLogger("EtihadFlightOps")

# 2. DATA QUALITY CONTRACT LAYER (Pydantic Schema Gate)
class TelemetryRecord(BaseModel):
    flight_callsign: str = Field(..., min_length=3)
    origin_station: str = Field(..., min_length=3, max_length=4) 
    destination_station: str = Field(..., min_length=3, max_length=4) 
    latitude: float = Field(..., ge=15.0, le=35.0)  
    longitude: float = Field(..., ge=45.0, le=65.0)
    altitude_feet: int = Field(..., ge=0)

# 3. HAVERSINE FORMULA DISTANCE CALCULATOR ENGINE
def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """Calculates the great-circle geodesic distance between two coordinates in Nautical Miles (NM)."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return int(3440.065 * c)

# 4. CONFIGURE INTERFACE SYSTEM LAYOUT
st.set_page_config(
    page_title="Etihad Flight Operations Control Room",
    page_icon="✈️",
    layout="wide"
)

# Custom Style sheets to match an airport radar operations screen
st.markdown("""
    <style>
    .main { background-color: #0b0f19; color: #f3f4f6; }
    div[data-testid="stMetricValue"] { color: #d4af37 !important; font-family: monospace; } 
    div[data-testid="stMetricLabel"] { color: #9ca3af !important; text-transform: uppercase; font-size: 11px !important; }
    .dataframe { font-family: monospace !important; background-color: #0f172a !important; }
    </style>
""", unsafe_allow_html=True)

# 5. GLOBAL AIRPORT RUNWAY COORDINATES REFERENCE MATRIX
AIRPORT_COORDINATES = {
    "AUH": {"lat": 24.4539, "lon": 54.3773}, # Abu Dhabi Zayed International
    "LHR": {"lat": 26.5000, "lon": 56.5000}, # Adjusted inside grid for tracking simulation
    "JFK": {"lat": 21.2000, "lon": 51.5000}, 
    "BOM": {"lat": 22.8000, "lon": 57.2000}, 
    "CDG": {"lat": 26.1000, "lon": 52.1000},  
    "DXB": {"lat": 25.2532, "lon": 55.3657}, 
    "DEL": {"lat": 23.1000, "lon": 56.9000}  
}

# 6. STATEFUL DATA LAYER MANAGEMENT
if "fleet_state" not in st.session_state:
    st.session_state.fleet_state = [
        {"flight_callsign": "EY/ETD151", "origin_station": "AUH", "destination_station": "LHR", "latitude": 24.4539, "longitude": 54.3773, "speed_lat": 0.15, "speed_lon": 0.12, "altitude_feet": 32000, "status": "CRUISE"},
        {"flight_callsign": "EY/ETD101", "origin_station": "AUH", "destination_station": "JFK", "latitude": 24.1200, "longitude": 53.9500, "speed_lat": -0.11, "speed_lon": -0.14, "altitude_feet": 30000, "status": "CRUISE"},
        {"flight_callsign": "EK/UAE72",  "origin_station": "DXB", "destination_station": "BOM", "latitude": 25.2048, "longitude": 55.2708, "speed_lat": -0.14, "speed_lon": 0.11, "altitude_feet": 34000, "status": "CRUISE"},
        {"flight_callsign": "QR/QTR319", "origin_station": "DXB", "destination_station": "CDG", "latitude": 24.8900, "longitude": 54.1200, "speed_lat": 0.09, "speed_lon": -0.15, "altitude_feet": 28000, "status": "CRUISE"},
        {"flight_callsign": "AI/AIC465", "origin_station": "DEL", "destination_station": "AUH", "latitude": 23.5000, "longitude": 53.2000, "speed_lat": 0.08, "speed_lon": 0.09, "altitude_feet": 36000, "status": "CRUISE"},
        {"flight_callsign": "MALFORMED_X", "origin_station": "UNKNOWN_HUB", "destination_station": "INVALID_STATION_CODE", "latitude": 5.0, "longitude": 12.0, "speed_lat": 0.0, "speed_lon": 0.0, "altitude_feet": -1500, "status": "CRUISE"}
    ]
    st.session_state.refresh_count = 0
    st.session_state.quarantine_count = 0

# 7. DATAOPS INGESTION PROCESSING & DYNAMIC ALTITUDE ENGINE
st.session_state.refresh_count += 1
clean_records = []

for flight in st.session_state.fleet_state:
    # Progress flight path location vectors
    if flight["status"] != "LANDED":
        flight["latitude"] += flight["speed_lat"]
        flight["longitude"] += flight["speed_lon"]
    
    dest_code = flight["destination_station"]
    
    # Calculate exact real-time distance remaining to destination airport
    if dest_code in AIRPORT_COORDINATES:
        dist_to_dest = calculate_haversine_distance(
            flight["latitude"], flight["longitude"],
            AIRPORT_COORDINATES[dest_code]["lat"], AIRPORT_COORDINATES[dest_code]["lon"]
        )
        orig_code = flight["origin_station"]
        dist_from_orig = calculate_haversine_distance(
            flight["latitude"], flight["longitude"],
            AIRPORT_COORDINATES[orig_code]["lat"], AIRPORT_COORDINATES[orig_code]["lon"]
        ) if orig_code in AIRPORT_COORDINATES else 100
    else:
        dist_to_dest = 500
        dist_from_orig = 500

    # 🛩️ AUTOMATED ALTITUDE VECTOR ENGINE (CRUISE ➔ DESCENT ➔ TOUCHDOWN)
    if flight["flight_callsign"] != "MALFORMED_X":
        if dist_to_dest <= 10:  # Touchdown zone
            flight["altitude_feet"] = 0
            flight["status"] = "LANDED"
        elif dist_to_dest <= 80:  # Near destination: Execute descent slope
            flight["status"] = "DESCENT"
            # Scale down altitude linearly based on remaining proximity distance
            flight["altitude_feet"] = max(1500, int((dist_to_dest / 80) * 15000))
        elif dist_from_orig <= 40:  # Near departure: Simulate climb phase
            flight["status"] = "CLIMB"
            flight["altitude_feet"] = min(24000, int((dist_from_orig / 40) * 24000))
        else:
            flight["status"] = "CRUISE"
            flight["altitude_feet"] += random.choice([-100, 0, 100]) # Normal cruise variance

    # Map variables to boundary gates
    if not (21.0 <= flight["latitude"] <= 27.0) or not (51.0 <= flight["longitude"] <= 58.0):
        # Reset completed flight trajectories back to origin coordinates to maintain loop continuity
        if dest_code in AIRPORT_COORDINATES:
            flight["latitude"] = AIRPORT_COORDINATES[flight["origin_station"]]["lat"]
            flight["longitude"] = AIRPORT_COORDINATES[flight["origin_station"]]["lon"]
            flight["altitude_feet"] = 30000
            flight["status"] = "CLIMB"

    # SCHEMA VALIDATION GATE (Data Quality Layer)
    try:
        validated_data = TelemetryRecord(**flight)
        record_dict = validated_data.model_dump()
        record_dict["dist_from_origin_nm"] = dist_from_orig
        record_dict["dist_to_destination_nm"] = dist_to_dest
        record_dict["flight_status"] = flight["status"]
        clean_records.append(record_dict)
    except ValidationError as e:
        st.session_state.quarantine_count += 1

df_clean_lakehouse = pd.DataFrame(clean_records)

# 8. RENDER THE INTERACTIVE APPLICATION UI
col_title, col_time = st.columns(2)
with col_title:
    st.markdown("<h2 style='color:#38bdf8;'>✈️ ETIHAD FLIGHT OPERATIONS CENTRE</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#4ade80; font-size:13px; font-weight:bold; margin-top:-15px;'>● REAL-TIME DISPATCH TRK FEED ACTIVE</p>", unsafe_allow_html=True)
with col_time:
    st.markdown(f"<p style='text-align:right; color:#9ca3af; font-family:monospace; margin-bottom:0;'>RADAR SWEEPS: {st.session_state.refresh_count}</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:right; color:#e5e7eb; font-family:monospace; margin-top:0;'>🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Airborne Sectors Monitored", f"{len(df_clean_lakehouse)} Active")
m2.metric("Telemetry Deflections", f"{st.session_state.quarantine_count} Isolated", delta="-100% Stream Corruption", delta_color="inverse")
m3.metric("Data Engine Layer", "Delta Lakehouse")
m4.metric("File Storage Layout", "Partitioned Columnar")

tab1, tab2 = st.tabs(["📊 Sector Ingestion Matrix (Silver Tier)", "🌍 Spatial Airspace Visualizer"])

with tab1:
    st.dataframe(
        df_clean_lakehouse[[
            "flight_callsign", "origin_station", "destination_station", 
            "dist_from_origin_nm", "dist_to_destination_nm", "altitude_feet", "flight_status"
        ]].rename(
            columns={
                "flight_callsign": "FLIGHT IDENT", "origin_station": "DEP", "destination_station": "ARR", 
                "altitude_feet": "PRESSURE ALTITUDE (FT)", "dist_from_origin_nm": "DIST FROM DEP (NM)", 
                "dist_to_destination_nm": "DIST TO ARR (NM)", "flight_status": "OPERATIONAL STATUS"
            }
        ), 
        use_container_width=True, 
        hide_index=True
    )

with tab2:
    df_map = df_clean_lakehouse[["latitude", "longitude"]].rename(columns={"latitude": "lat", "longitude": "lon"})
    st.map(df_map, zoom=6, use_container_width=True)

time.sleep(3)
st.rerun()
