import streamlit as st
import random
import pandas as pd
import logging
import math
import pydeck as pdk
import io
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, ValidationError

# Optional component for seamless auto-refreshing (pip install streamlit-autorefresh)
try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

# 1. ENTERPRISE OBSERVABILITY & LOGGING CONFIGURATION
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s]: %(message)s')
logger = logging.getLogger("EtihadFlightOps")

# 2. DATA QUALITY CONTRACT LAYER (Pydantic Schema Gate)
class TelemetryRecord(BaseModel):
    flight_callsign: str = Field(..., min_length=3)
    origin_station: str = Field(..., min_length=3, max_length=4) 
    destination_station: str = Field(..., min_length=3, max_length=4) 
    latitude: float = Field(..., ge=10.0, le=40.0)  
    longitude: float = Field(..., ge=40.0, le=80.0)
    altitude_feet: int = Field(..., ge=0)

# 3. VERIFIED HAVERSINE FORMULA DISTANCE CALCULATOR ENGINE
def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """Calculates the absolute great-circle distance between two global points in Nautical Miles (NM)."""
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

if st_autorefresh:
    st_autorefresh(interval=3000, key="radar_sweep_heartbeat")

st.markdown("""
    <style>
    .main { background-color: #0b0f19; color: #f3f4f6; }
    div[data-testid="stMetricValue"] { color: #d4af37 !important; font-family: monospace; } 
    div[data-testid="stMetricLabel"] { color: #9ca3af !important; text-transform: uppercase; font-size: 11px !important; }
    .dataframe { font-family: monospace !important; background-color: #0f172a !important; }
    .stAlert { background-color: #1e1b4b !important; color: #f87171 !important; border: 1px solid #dc2626 !important; }
    </style>
""", unsafe_allow_html=True)

# 5. REGIONAL AIRPORT OPERATIONS REFERENCE SCHEMA
AIRPORT_COORDINATES = {
    "AUH": {"lat": 24.4539, "lon": 54.3773}, 
    "DXB": {"lat": 25.2532, "lon": 55.3657}, 
    "DOH": {"lat": 25.2611, "lon": 51.5651}, 
    "BOM": {"lat": 19.0896, "lon": 72.8656}, 
    "DEL": {"lat": 28.5562, "lon": 77.1000}, 
    "MCT": {"lat": 23.5933, "lon": 58.2844}  
}

# 6. STATEFUL DATA REPOSITORY INITIALIZATION (Maintained strictly between 5 and 10 active profiles)
if "fleet_state" not in st.session_state:
    st.session_state.fleet_state = [
        {"flight_callsign": "EY/ETD151", "origin_station": "AUH", "destination_station": "BOM", "latitude": 24.4539, "longitude": 54.3773, "altitude_feet": 0, "status": "CLIMB", "fuel_burned_kg": 0, "total_fuel_capacity": 45000},
        {"flight_callsign": "EY/ETD101", "origin_station": "AUH", "destination_station": "DEL", "latitude": 24.4539, "longitude": 54.3773, "altitude_feet": 0, "status": "CLIMB", "fuel_burned_kg": 0, "total_fuel_capacity": 42000},
        {"flight_callsign": "EK/UAE72",  "origin_station": "DXB", "destination_station": "MCT", "latitude": 25.2532, "longitude": 55.3657, "altitude_feet": 0, "status": "CLIMB", "fuel_burned_kg": 0, "total_fuel_capacity": 38000},
        {"flight_callsign": "QR/QTR319", "origin_station": "DOH", "destination_station": "AUH", "latitude": 25.2611, "longitude": 51.5651, "altitude_feet": 0, "status": "CLIMB", "fuel_burned_kg": 0, "total_fuel_capacity": 40000},
        {"flight_callsign": "EY/ETD502", "origin_station": "BOM", "destination_station": "AUH", "latitude": 19.0896, "longitude": 72.8656, "altitude_feet": 0, "status": "CLIMB", "fuel_burned_kg": 0, "total_fuel_capacity": 46000},
        {"flight_callsign": "EY/ETD224", "origin_station": "DEL", "destination_station": "DXB", "latitude": 28.5562, "longitude": 77.1000, "altitude_feet": 0, "status": "CLIMB", "fuel_burned_kg": 0, "total_fuel_capacity": 44000},
        {"flight_callsign": "EY/ETD803", "origin_station": "MCT", "destination_station": "DOH", "latitude": 23.5933, "longitude": 58.2844, "altitude_feet": 0, "status": "CLIMB", "fuel_burned_kg": 0, "total_fuel_capacity": 39000},
        {"flight_callsign": "MALFORMED_X", "origin_station": "UNKNOWN_HUB", "destination_station": "INVALID", "latitude": 5.0, "longitude": 12.0, "altitude_feet": -500, "status": "CRUISE", "fuel_burned_kg": 0, "total_fuel_capacity": 10000}
    ]
    st.session_state.refresh_count = 0
    st.session_state.quarantine_count = 0
    st.session_state.trajectory_history = {}

# 7. INTERACTIVE ICAO FLIGHT PLAN INGESTION CONTAINER
st.sidebar.markdown("### 📥 Ingestion Node")
uploaded_file = st.sidebar.file_uploader("Upload .txt / .icao rows", type=["txt", "icao"])

if uploaded_file is not None:
    stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
    for line in stringio:
        tokens = line.strip().split(",")
        if len(tokens) >= 4:
            callsign, origin, destination, base_capacity = tokens[0], tokens[1], tokens[2], tokens[3]
            if origin in AIRPORT_COORDINATES and destination in AIRPORT_COORDINATES:
                active_count = len([f for f in st.session_state.fleet_state if f["flight_callsign"] != "MALFORMED_X"])
                if active_count >= 10:
                    st.sidebar.error("Stream Cap Reached (Max 10 Flights Allowed).")
                    break
                if not any(f['flight_callsign'] == callsign for f in st.session_state.fleet_state):
                    st.session_state.fleet_state.append({
                        "flight_callsign": callsign, "origin_station": origin, "destination_station": destination,
                        "latitude": AIRPORT_COORDINATES[origin]["lat"], "longitude": AIRPORT_COORDINATES[origin]["lon"],
                        "altitude_feet": 0, "status": "CLIMB", "fuel_burned_kg": 0, "total_fuel_capacity": int(base_capacity)
                    })
                    st.sidebar.success(f"Added Sector: {callsign}")

# 8. METRIC INGESTION PROCESSING & GEODESIC TRACKING LAYER
st.session_state.refresh_count += 1
clean_records = []
alerts_triggered = []

for flight in st.session_state.fleet_state:
    callsign = flight["flight_callsign"]
    orig = flight["origin_station"]
    dest = flight["destination_station"]
    
    if callsign == "MALFORMED_X":
        try: TelemetryRecord(**flight)
        except ValidationError: st.session_state.quarantine_count += 1
        continue

    if orig in AIRPORT_COORDINATES and dest in AIRPORT_COORDINATES:
        start_coord = AIRPORT_COORDINATES[orig]
        target_coord = AIRPORT_COORDINATES[dest]
        
        dist_from_orig = calculate_haversine_distance(flight["latitude"], flight["longitude"], start_coord["lat"], start_coord["lon"])
        dist_to_dest = calculate_haversine_distance(flight["latitude"], flight["longitude"], target_coord["lat"], target_coord["lon"])
        previous_altitude = flight["altitude_feet"]

        # 🌍 GEOMETRIC GEODATA ARRAYS (50 NM Terminal Hold Boundary Detection Engine)
        if dist_to_dest <= 50 and flight["status"] != "LANDED":
            flight["status"] = f"HOLD_{dest}"

        # 🛩️ PHYSICS DIRECTION ENGINE
        if flight["status"] != "LANDED":
            lat_diff = target_coord["lat"] - flight["latitude"]
            lon_diff = target_coord["lon"] - flight["longitude"]
            distance_vector = math.sqrt(lat_diff**2 + lon_diff**2)
            
            if distance_vector > 0.15: 
                next_lat = flight["latitude"] + (lat_diff / distance_vector) * 0.15
                next_lon = flight["longitude"] + (lon_diff / distance_vector) * 0.15
                flight["latitude"] = max(10.0, min(40.0, next_lat))
                flight["longitude"] = max(40.0, min(80.0, next_lon))
                flight["fuel_burned_kg"] += int(0.15 * 60 * 12) 
            else:
                flight["latitude"] = target_coord["lat"]
                flight["longitude"] = target_coord["lon"]
                flight["status"] = "LANDED"

        # 📐 REALISTIC ALTITUDE CONTROL ENGINES
        if "HOLD" in flight["status"]:
            flight["altitude_feet"] = 7000 + random.choice([-200, 0, 200]) # Holding Stack Altitude Lock
        elif flight["status"] != "LANDED":
            if dist_from_orig < 60: 
                flight["status"] = "CLIMB"
                flight["altitude_feet"] = max(1500, int((dist_from_orig / 60) * 34000))
            elif dist_to_dest < 100: 
                flight["status"] = "DESCENT"
                flight["altitude_feet"] = max(1000, int((dist_to_dest / 100) * 34000))
            else: 
                flight["status"] = "CRUISE"
                flight["altitude_feet"] = 34000 + random.choice([-100, 0, 100])
        else:
            flight["altitude_feet"] = 0

        vertical_rate = flight["altitude_feet"] - previous_altitude
        remaining_fuel = flight["total_fuel_capacity"] - flight["fuel_burned_kg"]

        if flight["status"] != "LANDED" and dist_to_dest > 0:
            eta_string = (datetime.now() + timedelta(minutes=(dist_to_dest / 450) * 60)).strftime("%H:%M UTC")
        else:
            eta_string = "ON APRON"

        # Trajectory Log Pipeline Execution
        if callsign not in st.session_state.trajectory_history:
            st.session_state.trajectory_history[callsign] = []
        st.session_state.trajectory_history[callsign].append((flight["longitude"], flight["latitude"]))
        if len(st.session_state.trajectory_history[callsign]) > 40:
            st.session_state.trajectory_history[callsign].pop(0)

        # Alert Profile Triggers
        if flight["status"] != "LANDED":
            if remaining_fuel < 5000:
                alerts_triggered.append(f"🚨 **CRITICAL FUEL EMERGENCY**: {callsign} reports {remaining_fuel:,} KG left.")
            if vertical_rate < -2500:
                alerts_triggered.append(f"⚠️ **TERRAIN AVOIDANCE**: {callsign} plunging at {vertical_rate:,} FT/sweep.")

        if flight["status"] == "LANDED" and random.random() < 0.2:
            flight["latitude"], flight["longitude"] = start_coord["lat"], start_coord["lon"]
            flight["altitude_feet"], flight["fuel_burned_kg"], flight["status"] = 0, 0, "CLIMB"

    try:
        validated_data = TelemetryRecord(**flight)
        record_dict = validated_data.model_dump()
        record_dict.update({
            "dist_from_origin_nm": dist_from_orig, "dist_to_destination_nm": dist_to_dest, "flight_status": flight["status"],
            "remaining_fuel_kg": remaining_fuel, "vertical_speed_profile": vertical_rate, "fuel_burned": f"{flight['fuel_burned_kg']:,} KG",
            "origin_lat": start_coord["lat"], "origin_lon": start_coord["lon"], "dest_lat": target_coord["lat"], "dest_lon": target_coord["lon"], "eta": eta_string
        })
        clean_records.append(record_dict)
    except ValidationError:
        st.session_state.quarantine_count += 1

df_clean_lakehouse = pd.DataFrame(clean_records)

# 9. AUTOMATIC CSV EXPORTER SNAPSHOT NODE
csv_buffer = io.StringIO()
df_clean_lakehouse.to_csv(csv_buffer, index=False)
st.sidebar.download_button(
    label="💾 Dump Telemetry Lakehouse (.CSV)",
    data=csv_buffer.getvalue(),
    file_name=f"ETHD_FLIGHTOPS_SNAPSHOT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv"
)

# 10. RENDER INTERACTIVE APPLICATION UI
col_title, col_time = st.columns(2)
with col_title:
    st.markdown("<h2 style='color:#38bdf8;'>✈️ ETIHAD FLIGHT OPERATIONS CENTRE</h2>", unsafe_allow_html=True)
with col_time:
    st.markdown(f"<p style='text-align:right; color:#e5e7eb; font-family:monospace; margin-top:15px;'>🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>", unsafe_allow_html=True)

if alerts_triggered:
    st.markdown("### ⚠️ Tactical Airspace Exceptions")
    for alert in alerts_triggered: st.error(alert)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Airborne Sectors Monitored", f"{len(df_clean_lakehouse)} Active")
m2.metric("Telemetry Deflections", f"{st.session_state.quarantine_count} Isolated")
m3.metric("Data Engine Layer", "Delta Lakehouse")
m4.metric("File Storage Layout", "Partitioned Columnar")

tab1, tab2, tab3 = st.tabs(["📊 Sector Ingestion Matrix", "🌍 3D Pydeck Spatial Arc Layer", "📈 Plotly Historical Trajectory Curves"])

with tab1:
    st.dataframe(df_clean_lakehouse[["flight_callsign", "origin_station", "destination_station", "dist_from_origin_nm", "dist_to_destination_nm", "altitude_feet", "vertical_speed_profile", "remaining_fuel_kg", "flight_status"]], use_container_width=True, hide_index=True)

with tab2:
    if not df_clean_lakehouse.empty:
        # Building visual landing hold rings via Pydeck Polygon Layer mapping logic
        hold_rings = []
        for code, coords in AIRPORT_COORDINATES.items():
            num_points = 24
            ring_points = []
            for i in range(num_points):
                angle = (i / num_points) * 2 * math.pi
                ring_points.append([coords["lon"] + 0.8 * math.cos(angle), coords["lat"] + 0.8 * math.sin(angle)])
            hold_rings.append({"polygon": ring_points, "name": f"HOLD_ZONE_{code}"})

        st.pydeck_chart(pdk.Deck(
            map_style="mapbox://styles/mapbox/dark-v10",
            initial_view_state=pdk.ViewState(latitude=23.0, longitude=65.0, zoom=4, pitch=45),
            layers=[
                pdk.Layer("ArcLayer", df_clean_lakehouse, get_source_position="[origin_lon, origin_lat]", get_target_position="[dest_lon, dest_lat]", get_source_color="[56, 189, 248, 140]", get_target_color="[212, 175, 55, 200]", get_width="3"),
                pdk.Layer("ScatterplotLayer", df_clean_lakehouse, get_position="[longitude, latitude]", get_color="[74, 222, 128]", get_radius=25000),
                pdk.Layer("PolygonLayer", hold_rings, get_polygon="polygon", get_fill_color="[220, 38, 38, 40]", get_line_color="[220, 38, 38, 200]", line_width_min_pixels=2, stroked=True, filled=True)
            ],
            tooltip={"text": "Asset: {flight_callsign}\nStatus: {flight_status}\nAltitude: {altitude_feet} FT"}
        ))

with tab3:
    fig = go.Figure()
    # Populate background station nodes
    fig.add_trace(go.Scatter(x=[c["lon"] for c in AIRPORT_COORDINATES.values()], y=[c["lat"] for c in AIRPORT_COORDINATES.values()], mode='markers+text', text=list(AIRPORT_COORDINATES.keys()), textposition="top center", marker=dict(color='#d4af37', size=10), name="Aviation Hub"))
    
    # Process historical trail records
    for name, route in st.session_state.trajectory_history.items():
        if route:
            lons, lats = zip(*route)
            fig.add_trace(go.Scatter(x=lons, y=lats, mode='lines+markers', name=name, line=dict(width=2), marker=dict(size=4)))
            
    fig.update_layout(title="Historical Radar Ingestion Curves", xaxis_title="Longitude", yaxis_title="Latitude", template="plotly_dark", height=500)
    st.plotly_chart(fig, use_container_width=True)

if not st_autorefresh:
    import time
    time.sleep(3)
    st.rerun()
