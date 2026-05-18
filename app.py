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
    latitude: float = Field(..., ge=10.0, le=40.0)  # Expanded boundaries to protect valid paths
    longitude: float = Field(..., ge=40.0, le=80.0)
    altitude_feet: int = Field(..., ge=0)

# 3. VERIFIED HAVERSINE FORMULA DISTANCE CALCULATOR ENGINE
def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """Calculates the absolute great-circle distance between two global points in Nautical Miles (NM)."""
    # Radians transformation layer
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Global Radius Constant: 3440.065 Nautical Miles
    nautical_miles = 3440.065 * c
    return int(nautical_miles)

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

# 5. REGIONAL AIRPORT OPERATIONS REFERENCE SCHEMA (True Airspace Coordinates)
AIRPORT_COORDINATES = {
    "AUH": {"lat": 24.4539, "lon": 54.3773}, # Abu Dhabi Zayed International
    "DXB": {"lat": 25.2532, "lon": 55.3657}, # Dubai International
    "DOH": {"lat": 25.2611, "lon": 51.5651}, # Doha Hamad International
    "BOM": {"lat": 19.0896, "lon": 72.8656}, # Mumbai International
    "DEL": {"lat": 28.5562, "lon": 77.1000}, # Delhi International
    "MCT": {"lat": 23.5933, "lon": 58.2844}  # Muscat International
}

# 6. STATEFUL DATA REPOSITORY INITIALIZATION
if "fleet_state" not in st.session_state:
    st.session_state.fleet_state = [
        # Inbound and Outbound tracks configured within the Gulf/Subcontinent region for accurate map view
        {"flight_callsign": "EY/ETD151", "origin_station": "AUH", "destination_station": "BOM", "latitude": 24.4539, "longitude": 54.3773, "altitude_feet": 0, "status": "CLIMB"},
        {"flight_callsign": "EY/ETD101", "origin_station": "AUH", "destination_station": "DEL", "latitude": 24.4539, "longitude": 54.3773, "altitude_feet": 0, "status": "CLIMB"},
        {"flight_callsign": "EK/UAE72",  "origin_station": "DXB", "destination_station": "MCT", "latitude": 25.2532, "longitude": 55.3657, "altitude_feet": 0, "status": "CLIMB"},
        {"flight_callsign": "QR/QTR319", "origin_station": "DOH", "destination_station": "AUH", "latitude": 25.2611, "longitude": 51.5651, "altitude_feet": 0, "status": "CLIMB"},
        {"flight_callsign": "EY/ETD502", "origin_station": "BOM", "destination_station": "AUH", "latitude": 19.0896, "longitude": 72.8656, "altitude_feet": 0, "status": "CLIMB"},
        {"flight_callsign": "MALFORMED_X", "origin_station": "UNKNOWN_HUB", "destination_station": "INVALID", "latitude": 5.0, "longitude": 12.0, "altitude_feet": -500, "status": "CRUISE"}
    ]
    st.session_state.refresh_count = 0
    st.session_state.quarantine_count = 0

# 7. METRIC INGESTION PROCESSING & GEODESIC TRACKING LAYER
st.session_state.refresh_count += 1
clean_records = []

for flight in st.session_state.fleet_state:
    orig = flight["origin_station"]
    dest = flight["destination_station"]
    
    # Isolate system crash tests
    if flight["flight_callsign"] == "MALFORMED_X":
        try: TelemetryRecord(**flight)
        except ValidationError: st.session_state.quarantine_count += 1
        continue

    if orig in AIRPORT_COORDINATES and dest in AIRPORT_COORDINATES:
        start_coord = AIRPORT_COORDINATES[orig]
        target_coord = AIRPORT_COORDINATES[dest]
        
        # Calculate full distance boundary baseline
        total_route_nm = calculate_haversine_distance(start_coord["lat"], start_coord["lon"], target_coord["lat"], target_coord["lon"])
        
        # Calculate dynamic distances from current coordinates
        dist_from_orig = calculate_haversine_distance(flight["latitude"], flight["longitude"], start_coord["lat"], start_coord["lon"])
        dist_to_dest = calculate_haversine_distance(flight["latitude"], flight["longitude"], target_coord["lat"], target_coord["lon"])

        # 🛩️ PHYSICS ENGINE: PROGRESS COORDINATES TOWARDS DESTINATION
        if flight["status"] != "LANDED":
            # Calculate directional angle (bearing vector) to slide coordinates smoothly
            lat_diff = target_coord["lat"] - flight["latitude"]
            lon_diff = target_coord["lon"] - flight["longitude"]
            distance_vector = math.sqrt(lat_diff**2 + lon_diff**2)
            
            if distance_vector > 0.15: # Standard directional cruise step
                flight["latitude"] += (lat_diff / distance_vector) * 0.15
                flight["longitude"] += (lon_diff / distance_vector) * 0.15
            else:
                flight["latitude"] = target_coord["lat"]
                flight["longitude"] = target_coord["lon"]
                flight["status"] = "LANDED"

        # 📐 REALISTIC ALTITUDE CONTROL ENGINES
        if flight["status"] != "LANDED":
            if dist_from_orig < 60: # Within 60 Nautical Miles of Departure: Climb Out
                flight["status"] = "CLIMB"
                flight["altitude_feet"] = int((dist_from_orig / 60) * 34000)
                flight["altitude_feet"] = max(1500, flight["altitude_feet"])
            elif dist_to_dest < 100: # Within 100 Nautical Miles of Arrival: Progressive Descent
                flight["status"] = "DESCENT"
                flight["altitude_feet"] = int((dist_to_dest / 100) * 34000)
                flight["altitude_feet"] = max(1000, flight["altitude_feet"])
            else: # Main Cruise Phase
                flight["status"] = "CRUISE"
                flight["altitude_feet"] = 34000 + random.choice([-100, 0, 100])
        else:
            flight["altitude_feet"] = 0

        # Reset completed tracks to recycle the loop smoothly
        if flight["status"] == "LANDED" and random.random() < 0.2:
            flight["latitude"] = start_coord["lat"]
            flight["longitude"] = start_coord["lon"]
            flight["altitude_feet"] = 0
            flight["status"] = "CLIMB"

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

# 8. RENDER INTERACTIVE APPLICATION UI
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
    st.map(df_map, zoom=5, use_container_width=True)

time.sleep(3)
st.rerun()
