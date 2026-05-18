# ✈️ Etihad Flight Operations Telemetry Pipeline

An enterprise-grade, real-time aviation monitoring dashboard and data quality pipeline built with Streamlit. The system ingests mock telemetry feeds, enforces rigid data-quality schemas using Pydantic data contracts, computes real-time geodesic vectors using the Haversine formula, and visualizes live regional airspace operations.

🔗 **Live Production App:** [etihad-telemetry-pipeline.streamlit.app](https://etihad-telemetry-pipeline-hoxpbysyd8exh9xwrwjezj.streamlit.app/)  
🧑‍💻 **Developer:** [srinivasta](https://github.com/srinivasta)

---

## 🚀 Key Features & System Architecture

### 1. Data Quality Contract Layer (Pydantic Gate)
Prevents downstream data lakehouse corruption. The pipeline enforces an explicit structural contract (`TelemetryRecord`) validating data boundaries:
*   **Callsign & Station IDs:** Strict length checks conforming to ICAO/IATA formatting.
*   **Geospatial Boundaries:** Coordinates strictly locked to valid regional airspace boxes (Latitude \(10.0^\circ\) to \(40.0^\circ\) N, Longitude \(40.0^\circ\) to \(80.0^\circ\) E).
*   **Negative Altitude Protection:** Blocks anomalous telemetry (e.g., automated rejection of `MALFORMED_X` test payloads).

### 2. Physics & Geodesic Calculation Engine
*   **Haversine Math:** Computes exact global great-circle distances in Nautical Miles (NM) dynamically as coordinates shift.
*   **Dynamic Kinematics:** Simulates realistic flight trajectories, continuous fuel burn tracking (\(\approx 12\text{ kg/NM}\)), and adaptive stage transitions (`CLIMB` \(\rightarrow\) `CRUISE` \(\rightarrow\) `DESCENT` \(\rightarrow\) `LANDED`).

### 3. Observability & UI Layer
*   **Automated Radar Sweeps:** Integrated background thread refresh rendering immediate position adjustments without user friction.
*   **Interactive Spatial View:** High-density Pydeck 3D map plotting airframe coordinates against standard regional aviation hubs (AUH, DXB, DOH, BOM, DEL, MCT).
*   **Quarantine Operations Log:** Built-in observability container isolating corrupted payloads for troubleshooting.

---

## 🛠️ Tech Stack & Dependencies

*   **Core Language:** Python 3.10+
*   **Frontend Framework:** Streamlit (Stateful Session Management)
*   **Data Validation:** Pydantic v2
*   **Geospatial Rendering:** Pydeck & Mapbox
*   **Data Manipulation:** Pandas

---

## 📦 Local Deployment & Installation

Follow these steps to run the Flight Operations Center locally:

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/etihad-telemetry-pipeline.git
   cd etihad-telemetry-pipeline
   ```

2. **Install Dependencies:**
   ```bash
   pip install streamlit pydantic pandas pydeck streamlit-autorefresh
   ```

3. **Launch the Core Application:**
   ```bash
   streamlit run app.py
   ```

---

## 📊 Telemetry Data Contract Preview

```python
class TelemetryRecord(BaseModel):
    flight_callsign: str = Field(..., min_length=3)
    origin_station: str = Field(..., min_length=3, max_length=4) 
    destination_station: str = Field(..., min_length=3, max_length=4) 
    latitude: float = Field(..., ge=10.0, le=40.0)  
    longitude: float = Field(..., ge=40.0, le=80.0)
    altitude_feet: int = Field(..., ge=0)
```

---
💡 *Developed as a high-utility demonstration of real-time stream simulation and robust architectural data safety by **[srinivasta](https://github.com)**.*
