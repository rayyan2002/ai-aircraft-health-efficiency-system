import streamlit as st
import plotly.graph_objects as go
import requests

# ================== CONFIG ==================
API_URL = "http://localhost:8000"

st.set_page_config(page_title="AI-Powered Aircraft Dashboard", layout="wide")

# ================== CUSTOM CSS ==================
st.markdown("""
<style>
    .stApp { background-color: #0a0e1a; }
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a7b 100%);
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        color: white;
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .metric-card {
        background: linear-gradient(135deg, #1a2332 0%, #2a3447 100%);
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #2d4263;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# ================== HELPER: CALL FASTAPI ==================
def call_api(endpoint, method="GET", data=None):
    try:
        url = f"{API_URL}{endpoint}"
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        else:
            st.error("Unsupported HTTP method")
            return None

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Cannot connect to API. Make sure FastAPI is running on port 8000.")
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

# ================== SESSION STATE ==================
if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None

# ================== HEADER ==================
st.markdown(
    '<div class="main-header">AI-Powered Aircraft Health & Efficiency Dashboard</div>',
    unsafe_allow_html=True
)

# ================== FETCH STATIC DATA FROM API ==================
aircraft_data = call_api("/api/aircraft")
airports_data = call_api("/api/airports")

aircraft_list = aircraft_data.get("aircraft", []) if aircraft_data else ["Boeing 737-800"]
airports_list = airports_data.get("airports", []) if airports_data else ["JFK - New York", "LAX - Los Angeles"]

# ================== TOP CONTROLS ==================
col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1.5])

with col1:
    aircraft = st.selectbox("Select Aircraft", aircraft_list)

with col2:
    departure = st.selectbox("Select Departure Airport", airports_list)

with col3:
    arrival = st.selectbox("Select Arrival Airport", airports_list)

with col4:
    weather = st.selectbox("Weather Conditions", ["Clear & Calm", "Moderate Wind", "Stormy"])

with col5:
    st.markdown("<br>", unsafe_allow_html=True)
    run_clicked = st.button("Run Analysis", use_container_width=True)

# ---- Additional aircraft & maintenance context (FYP-1) ----
ctx_col1, ctx_col2, ctx_col3, ctx_col4, ctx_col5 = st.columns([2, 1.2, 1.2, 1.2, 1.5])

with ctx_col1:
    aircraft_id = st.text_input("Aircraft ID (ICAO24 / Reg)", value="800736")

with ctx_col2:
    aircraft_age_years = st.number_input("Aircraft Age (years)", value=8.0, min_value=0.0)

with ctx_col3:
    flight_hours_input = st.number_input("Total Flight Hours", value=12000.0, min_value=0.0)

with ctx_col4:
    last_maintenance_days = st.number_input("Last Maintenance (days ago)", value=45.0, min_value=0.0)

with ctx_col5:
    last_maintenance_type = st.text_input("Last Maintenance Type", value="A-check")

# Trigger analysis after all inputs are defined
if run_clicked:
    with st.spinner("Analyzing..."):
        payload = {
            "aircraft": aircraft,
            "departure_airport": departure,
            "arrival_airport": arrival,
            "weather_conditions": weather,
            "aircraft_id": aircraft_id or None,
            "aircraft_age_years": aircraft_age_years,
            "flight_hours_input": flight_hours_input,
            "last_maintenance_days": last_maintenance_days,
            "last_maintenance_type": last_maintenance_type,
        }
        result = call_api("/api/analyze", method="POST", data=payload)
        if result:
            st.session_state.analysis_data = result
            st.success("Analysis complete!")

# ================== MAIN DASHBOARD ==================
if st.session_state.analysis_data:
    data = st.session_state.analysis_data

    st.markdown("<br>", unsafe_allow_html=True)

    row1_col1, row1_col2, row1_col3 = st.columns([1, 2, 1.3])

    # ---------- Aircraft Health Score ----------
    with row1_col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### Aircraft Health Score")

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=data["health_score"],
            domain={"x": [0, 1], "y": [0, 1]},
            number={"font": {"size": 48, "color": "white"}},
            title={"text": "Health Index", "font": {"size": 16, "color": "#b0bec5"}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "rgba(0,0,0,0)"},
                "steps": [
                    {"range": [0, 33], "color": "#ef5350"},
                    {"range": [33, 66], "color": "#ffa726"},
                    {"range": [66, 100], "color": "#7cb342"},
                ],
                "threshold": {
                    "line": {"color": "white", "width": 4},
                    "thickness": 0.75,
                    "value": data["health_score"],
                },
            },
        ))

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            height=250,
            margin=dict(l=20, r=20, t=30, b=10),
        )

        st.plotly_chart(fig, use_container_width=True)

        # Aircraft ID / type + context
        if data.get("aircraft_id"):
            if data.get("aircraft_type_exact"):
                st.markdown(f"✓ **Aircraft ID:** {data['aircraft_id']} (mapped to {data['aircraft_type']})")
            else:
                st.markdown(
                    f"✓ **Aircraft ID:** {data['aircraft_id']} "
                    f"(fallback type {data['aircraft_type']})"
                )
        else:
            st.markdown(f"✓ **Aircraft Type:** {data.get('aircraft_type', aircraft)}")

        st.markdown(f"✓ **Aircraft Age:** {data.get('aircraft_age_years', 0)} years")
        st.markdown(f"✓ **Flight Hours:** {data['flight_hours']:,} hrs")
        st.markdown(f"✓ **Cycles:** {data['cycles']:,}")
        st.markdown(f"✓ **Fuel Efficiency:** {data['fuel_efficiency']} L/NM")
        st.markdown(f"✓ **Maintenance Risk:** {data['maintenance_risk']}")
        st.markdown('</div>', unsafe_allow_html=True)

    # ---------- Optimal Route Recommendation ----------
    with row1_col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### Optimal Route Recommendation")
        st.markdown(f"*Route from {departure} to {arrival}*")
        st.markdown('</div>', unsafe_allow_html=True)

    # ---------- Route Analysis ----------
    with row1_col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### Route Analysis")

        st.markdown("**Recommended Route**")
        st.markdown(f"Distance: **{data['recommended_route']['distance']:,.0f} Miles**")
        st.markdown(f"Estimated Fuel: **{data['recommended_route']['estimated_fuel']:,.0f} L**")

        st.markdown("<br>**Alternative Route**", unsafe_allow_html=True)
        st.markdown(f"Distance: **{data['alternative_route']['distance']:,.0f} Miles**")
        st.markdown(f"Estimated Fuel: **{data['alternative_route']['estimated_fuel']:,.0f} L**")

        st.markdown("<br>**Model-based Risk**", unsafe_allow_html=True)
        st.markdown(f"ADS-B Anomaly Risk: **{data['turbulence_risk']}**")
        st.markdown(f"Stress Level: **{data['stress_level']}**")

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------- Bottom Metrics ----------
    row2_col1, row2_col2, row2_col3, row2_col4 = st.columns(4)

    with row2_col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### ⛽ Fuel Consumption")
        st.markdown(f"# {data['fuel_consumption']:,.0f} L")
        st.markdown("Predicted")
        st.markdown('</div>', unsafe_allow_html=True)

    with row2_col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### ⬇️ CO2 Emissions")
        st.markdown(f"# {data['co2_emissions']:,.0f}")
        st.markdown("kg CO₂")
        st.markdown('</div>', unsafe_allow_html=True)

    with row2_col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### ✓ Maintenance")
        st.markdown(f"## {data['maintenance_advisory']}")
        st.markdown('</div>', unsafe_allow_html=True)

    with row2_col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### ⚡ Stress Level")
        st.markdown(f"# {data['stress_level']}")
        st.markdown("Current Status")
        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.info("👆 Select parameters and click 'Run Analysis' to see results")
