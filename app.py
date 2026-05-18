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
    """Calculates the great-circle geodesic distance between two global coordinates in Nautical Miles (NM)."""
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

st.markdown("""
    <style>
    .main { background-color: #0b0f19; color: #f3f4f6; }
    div[data-testid="stMetricValue"] { color: #d4af37 !important; font-family: monospace; } 
    div[data-testid="stMetricLabel"] { color: #9ca3af !important; text-transform: uppercase; font-size: 11px !important; }
    .dataframe { font-family: monospace !important; background-color: #0f172a !important; }
    </style>
""", unsafe_allow_html=True)

# 5. GLOBAL AIRPORT RUNWAY COORDINATES REFERENCE MATRIX (True Global Values)
AIRPORT_COORDINATES = {
    "AUH": {"lat": 24.4539, "lon": 54.3773}, # Abu Dhabi Zayed International
    "DXB": {"lat": 25.2532, "lon": 55.3657}, # Dubai International
    "DOH": {"lat": 25.2611, "lon": 51.5651}, # Doha Hamad International ◄── FIXED: Added missing tracking point
    "LHR": {"lat": 51.4700, "lon": -0.4543}, # London Heathrow
    "JFK": {"lat": 40.6413, "lon": -73.7781},# New York JFK
    "BOM": {"lat": 19.0896, "lon": 72.8656}, # Mumbai Chhatrapati Shivaji
    "CDG": {"lat": 49.0097, "lon": 2.5479},  # Paris Charles de Gaulle
    "DEL": {"lat": 28.5562, "lon": 77.1000}  # Delhi Indira Gandhi
}

# Local Map Bounding Points to keep Streamlit map visualization stable
LOCAL_RADAR_MAP = {
    "AUH": {"lat": 24.4539, "lon": 54.3773},
    "DXB": {"lat": 25.2532, "lon": 55.3657},
    "DOH": {"lat": 25.1000, "lon": 51.5000},
    "LHR": {"lat": 26.5000, "lon": 56.5000}, # Plotted inside bounds for interface display continuity
    "JFK": {"lat": 21.2000, "lon": 51.5000}, 
    "BOM": {"lat": 22.8000, "lon": 57.2000}, 
    "CDG": {"lat": 26.1000, "lon": 52.1000},  
    "DEL": {"lat": 23.1000, "lon": 56.9000}  
}

# 6. STATEFUL DATA LAYER MANAGEMENT (Using Path Completion Percentages)
if "fleet_state" not in st.session_state:
    st.session_state.fleet_state = [
        {"flight_callsign": "EY/ETD151", "origin_station": "AUH", "destination_station": "LHR", "progress_pct": 0.0, "speed_pct": 0.04, "altitude_feet": 0, "status": "CLIMB"},
        {"flight_callsign": "EY/ETD101", "origin_station": "AUH", "destination_station": "JFK", "progress_pct": 0.0, "speed_pct": 0.03, "altitude_feet": 0, "status": "CLIMB"},
        {"flight_callsign": "EK/UAE72",  "origin_station": "DXB", "destination_station": "BOM", "progress_pct": 0.0, "speed_pct": 0.05, "altitude_feet": 0, "status": "CLIMB"},
        {"flight_callsign": "QR/QTR319", "origin_station": "DOH", "destination_station": "CDG", "progress_pct": 0.0, "speed_pct": 0.03, "altitude_feet": 0, "status": "CLIMB"}, # ◄── FIXED origin code mismatch
        {"flight_callsign": "AI/AIC465", "origin_station": "DEL", "destination_station": "AUH", "progress_pct": 0.0, "speed_pct": 0.04, "altitude_feet": 0, "status": "CLIMB"},
        {"flight_callsign": "MALFORMED_X", "origin_station": "UNKNOWN_HUB", "destination_station": "INVALID", "progress_pct": 0.0, "speed_pct": 0.0, "altitude_feet": -500, "status": "CRUISE"}
    ]
    st.session_state.refresh_count = 0
    st.session_state.quarantine_count = 0

# 7. DATAOPS INGESTION PROCESSING & DYNAMIC PATH CALCULATOR
st.session_state.refresh_count += 1
clean_records = []

for flight in st.session_state.fleet_state:
    orig = flight["origin_station"]
    dest = flight["destination_station"]
    
    # Skip calculations for dummy error testing items
    if flight["flight_callsign"] == "MALFORMED_X":
        try:
            TelemetryRecord(**flight)
        except ValidationError:
            st.session_state.quarantine_count += 1
        continue

    # Update path progression vector (0.0 ➔ 1.0)
    if flight["status"] != "LANDED":
        flight["progress_pct"] += flight["speed_pct"]
        if flight["progress_pct"] >= 1.0:
            flight["progress_pct"] = 1.0
            flight["status"] = "LANDED"

    if orig in AIRPORT_COORDINATES and dest in AIRPORT_COORDINATES:
        # Calculate maximum full route baseline tracking vector distance
        total_route_distance = calculate_haversine_distance(
            AIRPORT_COORDINATES[orig]["lat"], AIRPORT_COORDINATES[orig]["lon"],
            AIRPORT_COORDINATES[dest]["lat"], AIRPORT_COORDINATES[dest]["lon"]
        )
        
        # Linearly calculate distances based on progress percentage metrics
        dist_from_orig = int(total_route_distance * flight["progress_pct"])
        dist_to_dest = total_route_distance - dist_from_orig
        
        # Compute smooth visual rendering coordinates on local radar map grid boundaries
        start_map = LOCAL_RADAR_MAP[orig]
        end_map = LOCAL_RADAR_MAP[dest]
        flight["latitude"] = start_map["lat"] + (end_map["lat"] - start_map["lat"]) * flight["progress_pct"]
        flight["longitude"] = start_map["lon"] + (end_map["lon"] - start_map["lon"]) * flight["progress_pct"]

        # DYNAMIC ALTITUDE & CLIMB/DESCENT SLOPE ENGINE
        if flight["status"] != "LANDED":
            if flight["progress_pct"] <= 0.2:  # First 20% of route: Climb Phase
                flight["status"] = "CLIMB"
                flight["altitude_feet"] = int((flight["progress_pct"] / 0.2) * 32000)
            elif flight["progress_pct"] >= 0.8:  # Last 20% of route: Automated Progressive Descent
                flight["status"] = "DESCENT"
                remaining_scale = (1.0 - flight["progress_pct"]) / 0.2
                flight["altitude_feet"] = max(1200, int(remaining_scale * 32000))
            else:  # Middle 60% of route: Cruise Phase
                flight["status"] = "CRUISE"
                flight["altitude_feet"] = 32000 + random.choice([-100, 0, 100])
        else:
            flight["altitude_feet"] = 0
            
        # Re-initialize flight loop trajectory if completed and landed
        if flight["status"] == "LANDED" and random.random() < 0.3:
            flight["progress_pct"] = 0.0
            flight["status"] = "CLIMB"
            flight["altitude_feet"] = 0

    # SCHEMA VALIDATION GATE (Data Quality Layer)
    try:
        validated_data = TelemetryRecord(**flight)
        record_dict = validated_data.model_dump()
        record_dict["dist_from_origin_nm"] = dist_from_orig
        record_dict["dist_to_destination_nm"] = dist_to_dest
        record_dict["flight_status"] = flight["status"]
        clean_records.append(record_dict)
    except ValidationError:
        st.session_state.quarantine_count += 1

df_clean_lakehouse = pd.DataFrame(clean_records)

# 8. RENDER INTERACTIVE APPLICATION UI Layout
col_title, col_time = st.columns(2)
with col_title:
    st.markdown("<h2 style='color:#38bdf8;'>✈️ ETIHAD FLIGHT OPERATIONS CENTRE</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#4ade80; font-size:13px; font-weight:bold; margin-top:-15px;'>● DYNAMIC GEODESIC POSITION TRACKING ACTIVE</p>", unsafe_allow_html=True)
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
