import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import pandas as pd

# ================== CONFIG & CSS ==================
API_BASE_URL = "http://localhost:8000/api"

st.set_page_config(page_title="Aircraft Digital Twin Dashboard", layout="wide", page_icon="✈️")

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
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ================== API CONNECTION ==================
@st.cache_data(ttl=10) # Caches for 10 seconds to avoid spamming the backend
def fetch_fleet():
    try:
        response = requests.get(f"{API_BASE_URL}/fleet")
        if response.status_code == 200:
            return response.json().get("fleet", ["No API Connection"])
    except:
        pass
    return ["Backend Offline"]

def fetch_analysis(tail_number):
    try:
        response = requests.get(f"{API_BASE_URL}/analyze/{tail_number}")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

# ================== SIDEBAR ==================
st.sidebar.title("✈️ Fleet Control")
FLEET_LIST = fetch_fleet()

if "Backend Offline" in FLEET_LIST:
    st.sidebar.error("⚠️ FastAPI Backend is offline. Please run `uvicorn main:app --reload`.")
    st.stop()

selected_plane = st.sidebar.selectbox("Select Aircraft", FLEET_LIST)
page = st.sidebar.radio("Navigation", ["Live Dashboard", "Mission Logs"])

# Fetch Data for selected plane
API_DATA = fetch_analysis(selected_plane)

if not API_DATA:
    st.error(f"Failed to fetch ML analysis for {selected_plane}.")
    st.stop()

# ================== PAGE 1: LIVE DASHBOARD ==================
if page == "Live Dashboard":
    st.markdown(f'<div class="main-header">Live Digital Twin: {selected_plane}</div>', unsafe_allow_html=True)
    
    # --- Top Metrics ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><h3>Predicted RUL</h3><h2>{API_DATA["predicted_rul_cycles"]} cycles</h2></div>', unsafe_allow_html=True)
    with col2:
        risk_color = "red" if API_DATA['risk_level'] == "High" else "green"
        st.markdown(f'<div class="metric-card"><h3>Health Risk</h3><h2 style="color:{risk_color};">{API_DATA["risk_level"]}</h2></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><h3>Altitude</h3><h2>{API_DATA["live_telemetry"]["alt_ft"]} ft</h2></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><h3>Airspeed</h3><h2>{API_DATA["live_telemetry"]["speed_knots"]} kts</h2></div>', unsafe_allow_html=True)

    st.write("---")

    # --- Map & SHAP Charts ---
    map_col, chart_col = st.columns([1, 1])

    with map_col:
        st.subheader("📍 Live Telemetry")
        lat = API_DATA['live_telemetry']['lat']
        lon = API_DATA['live_telemetry']['lon']
        
        # Create Folium Map
        m = folium.Map(location=[lat, lon], zoom_start=6, tiles="CartoDB dark_matter")
        folium.Marker(
            [lat, lon], 
            tooltip=f"{selected_plane} | {API_DATA['live_telemetry']['speed_knots']} kts", 
            icon=folium.Icon(color="red", icon="plane")
        ).add_to(m)
        
        # Render in Streamlit
        st_folium(m, width=600, height=400, returned_objects=[])

    with chart_col:
        st.subheader("🧠 ML Diagnostics (SHAP)")
        shap_data = API_DATA['explainability_shap']
        
        # Create Plotly Waterfall Chart
        fig = go.Figure(go.Waterfall(
            orientation="h",
            measure=["relative"] * len(shap_data),
            y=[item['feature'] for item in shap_data],
            x=[item['impact'] for item in shap_data],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            decreasing={"marker": {"color": "#ff4b4b"}},
            increasing={"marker": {"color": "#00cc96"}}
        ))
        
        fig.update_layout(
            height=400, 
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        st.plotly_chart(fig, use_container_width=True)

# ================== PAGE 2: MISSION LOGS ==================
# ================== PAGE 2: MISSION LOGS ==================
elif page == "Mission Logs":
    st.markdown(f'<div class="main-header">Historical Flight Logs: {selected_plane}</div>', unsafe_allow_html=True)
    
    # Fetch live history from the API
    try:
        hist_response = requests.get(f"{API_BASE_URL}/history/{selected_plane}")
        history_data = hist_response.json().get("history", [])
    except:
        history_data = []

    if history_data:
        df = pd.DataFrame(history_data)
        # Rename columns for the UI
        df.columns = ["Flight ID", "Date", "Route", "Fuel Consumed (L)", "CO2 (kg)", "End Health Score"]
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.download_button(
            label="📥 Download Mission Log (CSV)",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name=f"{selected_plane}_history.csv",
            mime='text/csv',
        )
    else:
        st.info("No historical flights logged for this aircraft yet. Wait for a flight to complete!")
        
        # --- HIDDEN TECH LEAD BUTTON ---
        # A button just for you to test inserting data into Ruhab's table!
        if st.button("🔧 Force Log a Dummy Flight (Test DB)"):
            test_data = {
                "origin": "KHI", "destination": "DXB", 
                "fuel_liters": 15000, "co2_kg": 38000, "health_score": 45.2
            }
            requests.post(f"{API_BASE_URL}/complete_flight/{selected_plane}", json=test_data)
            st.success("Flight Logged! Refresh the page.")
            st.rerun()