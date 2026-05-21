import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# ══════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════
API = "http://localhost:8000/api"

st.set_page_config(
    page_title="AeroTwin — Pakistan Digital Fleet",
    layout="wide",
    page_icon="🛫",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════
# DESIGN SYSTEM
# ══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;500;600&display=swap');

/* ── Root ── */
:root {
    --bg-deep:    #060810;
    --bg-card:    #0d1117;
    --bg-hover:   #161b22;
    --border:     #21262d;
    --border-glow:#1f6feb;
    --accent:     #1f6feb;
    --accent-2:   #388bfd;
    --green:      #3fb950;
    --yellow:     #d29922;
    --red:        #f85149;
    --text-prime: #e6edf3;
    --text-muted: #7d8590;
    --text-dim:   #484f58;
}

/* ── Global ── */
.stApp { background-color: var(--bg-deep) !important; }
* { font-family: 'Inter', sans-serif; }
section[data-testid="stSidebar"] {
    background: #0d1117 !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] * { color: var(--text-prime) !important; }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }

/* ── Header ── */
.aero-header {
    font-family: 'Orbitron', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 4px;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 4px;
}
.aero-title {
    font-family: 'Orbitron', monospace;
    font-size: 26px;
    font-weight: 900;
    color: var(--text-prime);
    letter-spacing: 2px;
    line-height: 1.2;
}
.aero-title span { color: var(--accent-2); }

/* ── KPI Cards ── */
.kpi-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 18px 20px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), var(--accent-2));
}
.kpi-card:hover { border-color: var(--border-glow); }
.kpi-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 8px;
}
.kpi-value {
    font-family: 'Orbitron', monospace;
    font-size: 28px;
    font-weight: 700;
    color: var(--text-prime);
    line-height: 1;
}
.kpi-unit {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 4px;
}
.kpi-green .kpi-value  { color: var(--green); }
.kpi-yellow .kpi-value { color: var(--yellow); }
.kpi-red .kpi-value    { color: var(--red); }
.kpi-blue .kpi-value   { color: var(--accent-2); }

/* ── Section headers ── */
.section-title {
    font-family: 'Orbitron', monospace;
    font-size: 11px;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border);
    padding-bottom: 8px;
    margin-bottom: 16px;
}

/* ── Status badges ── */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}
.badge-airborne { background: rgba(63,185,80,0.15); color: var(--green); border: 1px solid rgba(63,185,80,0.3); }
.badge-grounded { background: rgba(125,133,144,0.15); color: var(--text-muted); border: 1px solid rgba(125,133,144,0.3); }
.badge-high     { background: rgba(248,81,73,0.15); color: var(--red); border: 1px solid rgba(248,81,73,0.3); }
.badge-moderate { background: rgba(210,153,34,0.15); color: var(--yellow); border: 1px solid rgba(210,153,34,0.3); }
.badge-low      { background: rgba(63,185,80,0.15); color: var(--green); border: 1px solid rgba(63,185,80,0.3); }

/* ── Fleet aircraft cards ── */
.ac-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 8px;
    cursor: pointer;
    transition: all 0.15s;
}
.ac-card:hover { border-color: var(--accent); background: var(--bg-hover); }
.ac-card-tail {
    font-family: 'Orbitron', monospace;
    font-size: 13px;
    font-weight: 700;
    color: var(--accent-2);
}
.ac-card-type {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 2px;
}

/* ── Info rows ── */
.info-row {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
    font-size: 13px;
}
.info-label { color: var(--text-muted); }
.info-value { color: var(--text-prime); font-weight: 500; }

/* ── Divider ── */
.divider {
    border: none;
    border-top: 1px solid var(--border);
    margin: 20px 0;
}

/* ── Sidebar brand ── */
.sidebar-brand {
    font-family: 'Orbitron', monospace;
    font-size: 16px;
    font-weight: 900;
    color: var(--accent-2) !important;
    letter-spacing: 2px;
    padding: 8px 0 16px 0;
}
.sidebar-section {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--text-dim) !important;
    padding: 12px 0 6px 0;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# API HELPERS
# ══════════════════════════════════════════════════════════════
@st.cache_data(ttl=15)
def fetch_fleet():
    """Live Dashboard — always queries flight_telemetry callsigns directly."""
    try:
        r = requests.get(f"{API}/live_fleet", timeout=5)
        if r.status_code == 200:
            return r.json().get("fleet", [])
    except:
        pass
    return []

@st.cache_data(ttl=15)
def fetch_pak_fleet():
    try:
        r = requests.get(f"{API}/pak_fleet", timeout=5)
        if r.status_code == 200:
            return r.json().get("fleet", [])
    except:
        pass
    return []

def fetch_analysis(tail):
    try:
        r = requests.get(f"{API}/analyze/{tail}", timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def fetch_pak_analysis(tail):
    try:
        r = requests.get(f"{API}/pak_analyze/{tail}", timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def fetch_route(tail, pak=False):
    endpoint = "pak_route" if pak else "route"
    try:
        r = requests.get(f"{API}/{endpoint}/{tail}", timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def fetch_history(tail, pak=False):
    endpoint = "pak_history" if pak else "history"
    try:
        r = requests.get(f"{API}/{endpoint}/{tail}", timeout=5)
        if r.status_code == 200:
            return r.json().get("history", [])
    except:
        pass
    return []


def fetch_maintenance_history(tail):
    try:
        r = requests.get(f"{API}/maintenance_history/{tail}", timeout=5)
        if r.status_code == 200:
            return r.json().get("records", [])
    except:
        pass
    return []

def fetch_fleet_status():
    try:
        r = requests.get(f"{API}/fleet_status", timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return {}

def fetch_pipeline_logs():
    try:
        r = requests.get(f"{API}/pipeline_logs", timeout=5)
        if r.status_code == 200:
            return r.json().get("logs", [])
    except:
        pass
    return []

# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
st.sidebar.markdown('<div class="sidebar-brand">AEROTWIN</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="sidebar-section">Navigation</div>', unsafe_allow_html=True)

page = st.sidebar.radio(
    "",
    ["📡  Live Dashboard", "🇵🇰  Pakistan Fleet",
     "📋  Mission Logs", "🔧  Maintenance Portal", "🧮  Flight Simulator"],
    label_visibility="collapsed"
)

st.sidebar.markdown('<div class="sidebar-section">Aircraft Selection</div>', unsafe_allow_html=True)

# ── Aircraft selection depends on page ──
if page in ("🇵🇰  Pakistan Fleet", "🔧  Maintenance Portal",
            "🧮  Flight Simulator", "📋  Mission Logs"):
    pak_fleet = fetch_pak_fleet()

    # Group by airline
    airlines = sorted(set(p.get("airline", "Unknown") for p in pak_fleet))
    airline_icons = {
        "Pakistan International Airlines": "🟢 PIA",
        "AirBlue":   "🔵 AirBlue",
        "AirSial":   "🟠 AirSial",
        "Fly Jinnah":"🔴 FlyJinnah",
    }

    selected_airline = st.sidebar.selectbox(
        "Airline",
        airlines,
        format_func=lambda x: airline_icons.get(x, x)
    )

    airline_planes = [p for p in pak_fleet if p.get("airline") == selected_airline]
    plane_options  = {
        f"{'✈' if p.get('status')=='airborne' else '🅿'} {p['tail_number']} — {p.get('aircraft_type','').split('-')[0]}": p["tail_number"]
        for p in airline_planes
    }

    if not plane_options:
        st.sidebar.warning("No aircraft found for this airline.")
        st.stop()

    selected_label = st.sidebar.selectbox("Aircraft", list(plane_options.keys()))
    selected_plane = plane_options[selected_label]
    selected_pak_data = next((p for p in pak_fleet if p["tail_number"] == selected_plane), {})

else:
    # Live Dashboard / Mission Logs use flight_telemetry callsigns
    fleet_data = fetch_fleet()
    if not fleet_data:
        st.sidebar.error("⚠️ Backend offline.")
        st.stop()

    display_options = {}
    for plane in fleet_data:
        if isinstance(plane, dict):
            tail   = plane.get("tail_number", "Unknown")
            flight = plane.get("current_flight", "—")
            display_options[f"✈️  {tail}  ·  {flight}"] = tail
        else:
            display_options[f"✈️  {plane}"] = plane

    selected_label = st.sidebar.selectbox("Callsign", list(display_options.keys()))
    selected_plane = display_options[selected_label]

st.sidebar.markdown("---")
st.sidebar.caption(f"AeroTwin v2.0  ·  Sprint 3")


# ══════════════════════════════════════════════════════════════
# SHARED: MAP BUILDER
# ══════════════════════════════════════════════════════════════
def build_map(lat, lon, tail, speed, alt, route_data=None, callsign=None):

    # ── Convert ICAO callsign → public IATA flight number ──
    ICAO_TO_IATA = {
        "PIA": "PK", "ABQ": "PA", "FJL": "9P",
        "SIF": "PF", "ERD": "PF", "SAI": "ER",
    }
    def to_iata_flight(cs):
        if not cs:
            return cs
        cs = cs.strip().upper()
        for icao_prefix, iata_prefix in ICAO_TO_IATA.items():
            if cs.startswith(icao_prefix):
                number = cs[len(icao_prefix):]
                return f"{iata_prefix}{number}"
        return cs   # unknown airline — return as-is

    display_callsign = to_iata_flight(callsign or tail)
    label = display_callsign

    m = folium.Map(
        location=[lat, lon],
        zoom_start=6,
        tiles="CartoDB dark_matter"
    )

    if route_data and len(route_data.get("route_points", [])) > 1:
        points = route_data["route_points"]
        coords = [[p["lat"], p["lon"]] for p in points]

        folium.PolyLine(
            coords, color="#1f6feb", weight=2,
            opacity=0.8, dash_array="6 4",
            tooltip=f"{label} — flight path"
        ).add_to(m)

        # ── Origin marker ──
        folium.CircleMarker(
            location=coords[0], radius=5,
            color="#7d8590", fill=True,
            fill_color="#7d8590", fill_opacity=0.9,
            tooltip=f"Origin"
        ).add_to(m)

        # ── Waypoint callsign labels every few points ──
        step = max(1, len(coords) // 4)
        for pt in coords[1:-1:step]:
            folium.Marker(
                location=pt,
                icon=folium.DivIcon(
                    html=f'<div style="font-family:monospace;font-size:9px;'
                         f'color:#388bfd;background:rgba(13,17,23,0.75);'
                         f'padding:1px 4px;border-radius:3px;white-space:nowrap;'
                         f'border:1px solid #1f6feb">{label}</div>',
                    icon_size=(60, 16),
                    icon_anchor=(30, 8),
                ),
                tooltip=f"{label}"
            ).add_to(m)

    # ── Current position — plane icon with callsign popup ──
    folium.Marker(
        [lat, lon],
        tooltip=f"✈ {label} | {speed} m/s | {alt} m",
        popup=folium.Popup(
            f"<b style='font-family:monospace'>{label}</b><br>"
            f"Reg: {tail}<br>"
            f"Alt: {alt} m<br>"
            f"Speed: {speed} m/s",
            max_width=160
        ),
        icon=folium.Icon(color="red", icon="plane", prefix="fa")
    ).add_to(m)

    return m


# ══════════════════════════════════════════════════════════════
# SHARED: SHAP CHART
# ══════════════════════════════════════════════════════════════
def build_shap_chart(shap_data):
    fig = go.Figure(go.Waterfall(
        orientation="h",
        measure=["relative"] * len(shap_data),
        y=[d["feature"] for d in shap_data],
        x=[d["impact"]  for d in shap_data],
        connector={"line": {"color": "#21262d"}},
        decreasing={"marker": {"color": "#f85149"}},
        increasing={"marker": {"color": "#3fb950"}},
    ))
    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#7d8590", size=11),
        xaxis=dict(gridcolor="#21262d", zerolinecolor="#388bfd"),
        yaxis=dict(gridcolor="rgba(0,0,0,0)"),
    )
    return fig


# ══════════════════════════════════════════════════════════════
# PAGE 1 — LIVE DASHBOARD
# ══════════════════════════════════════════════════════════════
if page == "📡  Live Dashboard":

    data = fetch_analysis(selected_plane)
    if not data:
        st.error(f"Could not fetch analysis for **{selected_plane}**. Is the backend running?")
        st.stop()

    # ── Header ──
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown('<div class="aero-header">Live Digital Twin</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="aero-title"><span>{selected_plane}</span></div>', unsafe_allow_html=True)
    with col_h2:
        phase = data.get("flight_phase", "unknown").replace("_", " ").title()
        risk  = data.get("risk_level", "Low")
        badge_class = {"High": "badge-high", "Moderate": "badge-moderate", "Low": "badge-low"}.get(risk, "badge-low")
        st.markdown(f"""
            <div style="text-align:right;padding-top:12px">
                <span class="badge badge-airborne">● {phase}</span><br><br>
                <span class="badge {badge_class}">{risk} Risk</span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── KPI Strip ──
    k1, k2, k3, k4, k5 = st.columns(5)
    kpis = [
        (k1, "Predicted RUL",  f"{data['predicted_rul_cycles']}", "cycles",  "kpi-blue"),
        (k2, "Health Score",   f"{data.get('health_score', 0)}",  "/ 100",   "kpi-green" if data.get('health_score',0) > 60 else "kpi-red"),
        (k3, "Altitude",       f"{data['live_telemetry']['alt_m']:.0f}", "metres", ""),
        (k4, "Airspeed",       f"{data['live_telemetry']['speed_ms']:.1f}", "m/s", ""),
        (k5, "Fuel Burn Est.", f"{data['route_and_emissions']['predicted_fuel_liters']:,.0f}", "litres", ""),
    ]
    for col, label, value, unit, cls in kpis:
        with col:
            st.markdown(f"""
                <div class="kpi-card {cls}">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value">{value}</div>
                    <div class="kpi-unit">{unit}</div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Map + SHAP ──
    map_col, shap_col = st.columns([1, 1])

    with map_col:
        st.markdown('<div class="section-title">Live Position & Flight Path</div>', unsafe_allow_html=True)
        lat = data["live_telemetry"]["lat"]
        lon = data["live_telemetry"]["lon"]
        route_data = fetch_route(selected_plane)
        m = build_map(lat, lon, selected_plane,
                      data["live_telemetry"]["speed_ms"],
                      data["live_telemetry"]["alt_m"],
                      route_data,
                      callsign=selected_plane)
        st_folium(m, width=None, height=400, returned_objects=[])

    with shap_col:
        st.markdown('<div class="section-title">ML Diagnostics — Feature Attribution</div>', unsafe_allow_html=True)
        st.plotly_chart(
            build_shap_chart(data["explainability_shap"]),
            use_container_width=True
        )

        # ── Emissions ──
        st.markdown('<div class="section-title" style="margin-top:16px">Emissions Estimate</div>', unsafe_allow_html=True)
        e1, e2, e3 = st.columns(3)
        e1.metric("Wind", f"{data['route_and_emissions']['weather_wind_ms']} m/s")
        e2.metric("Temp", f"{data['route_and_emissions']['temp_c']}°C")
        e3.metric("CO₂", f"{data['route_and_emissions']['predicted_co2_kg']:,.0f} kg")


# ══════════════════════════════════════════════════════════════
# PAGE 2 — PAKISTAN FLEET
# ══════════════════════════════════════════════════════════════
elif page == "🇵🇰  Pakistan Fleet":

    data = fetch_pak_analysis(selected_plane)
    if not data:
        st.error(f"No analysis data for **{selected_plane}**. Run `fetch_opensky.py` first.")
        st.stop()

    # ── Header ──
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown('<div class="aero-header">Pakistan Fleet — Digital Twin</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="aero-title"><span>{selected_plane}</span> '
            f'<span style="font-size:14px;color:#7d8590;font-family:Inter">'
            f'{selected_pak_data.get("aircraft_type","")} · {selected_pak_data.get("airline","")}'
            f'</span></div>',
            unsafe_allow_html=True
        )
    with col_h2:
        risk  = data.get("risk_level", "Low")
        status = selected_pak_data.get("status", "grounded")
        badge_class = {"High": "badge-high", "Moderate": "badge-moderate", "Low": "badge-low"}.get(risk, "badge-low")
        st.markdown(f"""
            <div style="text-align:right;padding-top:12px">
                <span class="badge {'badge-airborne' if status=='airborne' else 'badge-grounded'}">
                    {'● Airborne' if status=='airborne' else '○ Grounded'}
                </span><br><br>
                <span class="badge {badge_class}">{risk} Risk</span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── KPI Strip ──
    k1, k2, k3, k4, k5 = st.columns(5)
    health = data.get("health_score", 0)
    kpis = [
        (k1, "Predicted RUL",  f"{data['predicted_rul_cycles']}", "cycles",  "kpi-blue"),
        (k2, "Health Score",   f"{health}",  "/ 100", "kpi-green" if health > 60 else "kpi-yellow" if health > 30 else "kpi-red"),
        (k3, "Altitude",       f"{data['live_telemetry']['alt_m']:.0f}", "metres", ""),
        (k4, "Airspeed",       f"{data['live_telemetry']['speed_ms']:.1f}", "m/s", ""),
        (k5, "Fuel Burn Est.", f"{data['route_and_emissions']['predicted_fuel_liters']:,.0f}", "litres", ""),
    ]
    for col, label, value, unit, cls in kpis:
        with col:
            st.markdown(f"""
                <div class="kpi-card {cls}">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value">{value}</div>
                    <div class="kpi-unit">{unit}</div>
                </div>
            """, unsafe_allow_html=True)

    # ── Maintenance Warning ──
    if data.get("risk_level") == "High" or health < 30:
        st.markdown("<br>", unsafe_allow_html=True)
        st.error(
            f"⚠️ **Maintenance Advisory** — {selected_plane} shows elevated risk. "
            f"RUL: {data['predicted_rul_cycles']} cycles. Health: {health}/100. "
            f"Recommend inspection before next flight."
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Map + SHAP ──
    map_col, shap_col = st.columns([1, 1])

    with map_col:
        st.markdown('<div class="section-title">Live Position & Flight Path</div>', unsafe_allow_html=True)
        lat = data["live_telemetry"]["lat"] or 30.3753
        lon = data["live_telemetry"]["lon"] or 69.3451
        route_data = fetch_route(selected_plane, pak=True)
        pak_callsign = selected_pak_data.get("callsign") or selected_plane
        m = build_map(lat, lon, selected_plane,
                      data["live_telemetry"]["speed_ms"],
                      data["live_telemetry"]["alt_m"],
                      route_data,
                      callsign=pak_callsign)
        st_folium(m, width=None, height=400, returned_objects=[])

        # ── Soft estimated position notice ──
        if data.get("anomaly_flag") == 1 or selected_pak_data.get("status") != "airborne":
            st.markdown(
                '<p style="font-size:11px;color:#484f58;margin-top:6px;'
                'letter-spacing:0.5px;">&#x26A0; position estimated from scheduled route '
                '— live GPS unavailable on free data tier</p>',
                unsafe_allow_html=True
            )

    with shap_col:
        st.markdown('<div class="section-title">ML Diagnostics — Feature Attribution</div>', unsafe_allow_html=True)
        st.plotly_chart(
            build_shap_chart(data["explainability_shap"]),
            use_container_width=True
        )

        st.markdown('<div class="section-title" style="margin-top:16px">Aircraft Info</div>', unsafe_allow_html=True)
        info_rows = [
            ("Registration",   selected_plane),
            ("Type",           selected_pak_data.get("aircraft_type", "—")),
            ("Airline",        selected_pak_data.get("airline", "—")),
            ("ICAO24 Hex",     selected_pak_data.get("hex_code", "—")),
            ("Flight Phase",   data.get("flight_phase", "—").replace("_", " ").title()),
            ("ADS-B Score",    str(data.get("iforest_score", "—"))),
            ("Records Used",   str(data.get("records_used", "—"))),
        ]
        for label, value in info_rows:
            st.markdown(f"""
                <div class="info-row">
                    <span class="info-label">{label}</span>
                    <span class="info-value">{value}</span>
                </div>
            """, unsafe_allow_html=True)

    # ── Fleet Overview Table ──
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">{selected_pak_data.get("airline","")} Fleet Status</div>', unsafe_allow_html=True)

    airline_fleet = [
        p for p in fetch_pak_fleet()
        if p.get("airline") == selected_pak_data.get("airline")
    ]
    if airline_fleet:
        df_fleet = pd.DataFrame([{
            "Tail":    p["tail_number"],
            "Type":    p.get("aircraft_type", "—"),
            "Status":  p.get("status", "grounded").title(),
            "Callsign":p.get("callsign", "—"),
            "Alt (m)": p.get("altitude") or "—",
            "Speed":   p.get("velocity") or "—",
        } for p in airline_fleet])

        st.dataframe(
            df_fleet,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.TextColumn("Status"),
                "Alt (m)": st.column_config.NumberColumn("Alt (m)", format="%.0f"),
                "Speed": st.column_config.NumberColumn("Speed (m/s)", format="%.1f"),
            }
        )


# ══════════════════════════════════════════════════════════════
# PAGE 3 — MISSION LOGS
# ══════════════════════════════════════════════════════════════
elif page == "📋  Mission Logs":

    st.markdown('<div class="aero-header">Flight Records</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="aero-title">Mission Logs — <span>{selected_plane}</span>'
        f'<span style="font-size:14px;color:#7d8590;font-family:Inter"> · '
        f'{selected_pak_data.get("airline","")}</span></div>',
        unsafe_allow_html=True
    )
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Always use pak_history for fleet aircraft
    history = fetch_history(selected_plane, pak=True)
    if not history:
        history = fetch_history(selected_plane, pak=False)

    if history:
        df = pd.DataFrame(history)
        st.markdown('<div class="section-title">Flight History</div>', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # ── Health Trend ──
        if "health_score" in df.columns:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="section-title">Health Score Trend</div>', unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df.get("flight_id", df.index),
                y=df["health_score"],
                mode="lines+markers",
                line=dict(color="#388bfd", width=2),
                marker=dict(size=6, color="#f85149",
                            line=dict(color="#388bfd", width=1)),
                fill="tozeroy",
                fillcolor="rgba(31,111,235,0.05)",
            ))
            fig.update_layout(
                height=220,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#7d8590", size=11),
                xaxis=dict(gridcolor="#21262d"),
                yaxis=dict(gridcolor="#21262d", range=[0, 105]),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

        st.download_button(
            label="📥  Export CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"{selected_plane}_mission_log.csv",
            mime="text/csv",
        )

    else:
        st.info("No mission logs yet for this aircraft.")
        if st.button("🔧  Insert Test Flight Record"):
            requests.post(f"{API}/complete_flight/{selected_plane}", json={
                "origin": "KHI", "destination": "LHE",
                "fuel_liters": 8500, "co2_kg": 21500, "health_score": 62.0
            })
            st.success("Test record inserted — refresh to see it.")
            st.rerun()

# ══════════════════════════════════════════════════════════════
# PAGE 4 — MAINTENANCE PORTAL
# ══════════════════════════════════════════════════════════════
elif page == "🔧  Maintenance Portal":

    data = fetch_pak_analysis(selected_plane)
    health = data.get("health_score", 50) if data else 50
    risk   = data.get("risk_level", "Low") if data else "Low"

    st.markdown('<div class="aero-header">Mechanic Portal</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="aero-title"><span>{selected_plane}</span> '
        f'<span style="font-size:14px;color:#7d8590;font-family:Inter">'
        f'{selected_pak_data.get("aircraft_type","")} · {selected_pak_data.get("airline","")}'
        f'</span></div>',
        unsafe_allow_html=True
    )
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Current health strip ──
    h1, h2, h3 = st.columns(3)
    h1.markdown(f"""<div class="kpi-card {'kpi-red' if health < 40 else 'kpi-yellow' if health < 70 else 'kpi-green'}">
        <div class="kpi-label">Current Health</div>
        <div class="kpi-value">{health}</div>
        <div class="kpi-unit">/ 100</div></div>""", unsafe_allow_html=True)
    h2.markdown(f"""<div class="kpi-card {'kpi-red' if risk=='High' else 'kpi-yellow' if risk=='Moderate' else ''}">
        <div class="kpi-label">Risk Level</div>
        <div class="kpi-value">{risk}</div>
        <div class="kpi-unit">current</div></div>""", unsafe_allow_html=True)
    rul = data.get("predicted_rul_cycles", "—") if data else "—"
    h3.markdown(f"""<div class="kpi-card kpi-blue">
        <div class="kpi-label">Predicted RUL</div>
        <div class="kpi-value">{rul}</div>
        <div class="kpi-unit">cycles</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    left_col, right_col = st.columns([1, 2])

    # ── Left: component selector ──
    with left_col:
        st.markdown('<div class="section-title">Aircraft Components</div>', unsafe_allow_html=True)

        COMPONENTS = [
            "Engine 1", "Engine 2", "APU",
            "Landing Gear", "Avionics", "Windshield", "Fuel System"
        ]

        maint_hist = fetch_maintenance_history(selected_plane)
        maintained_components = {r["component"] for r in maint_hist}

        selected_component = st.radio(
            "",
            COMPONENTS,
            label_visibility="collapsed",
            format_func=lambda c: f"✅ {c}" if c in maintained_components else f"⚪ {c}"
        )

    # ── Right: component detail + maintenance form ──
    with right_col:
        st.markdown(f'<div class="section-title">{selected_component} — Maintenance Log</div>',
                    unsafe_allow_html=True)

        # Show history for this component
        comp_history = [r for r in maint_hist if r["component"] == selected_component]
        if comp_history:
            last = comp_history[0]
            st.markdown(f"""
                <div class="info-row"><span class="info-label">Last Maintained</span>
                <span class="info-value">{last['performed_at'][:10]}</span></div>
                <div class="info-row"><span class="info-label">Type</span>
                <span class="info-value">{last['maintenance_type']}</span></div>
                <div class="info-row"><span class="info-label">Location</span>
                <span class="info-value">{last['location']}</span></div>
                <div class="info-row"><span class="info-label">Notes</span>
                <span class="info-value">{last['notes'] or '—'}</span></div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(
                '<p style="color:#484f58;font-size:12px">No maintenance record found for this component.</p>',
                unsafe_allow_html=True
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">Log New Maintenance</div>', unsafe_allow_html=True)

        maint_type = st.selectbox(
            "Maintenance Type",
            ["A-check", "B-check", "C-check", "Component replacement", "Inspection"]
        )
        location = st.text_input("Location (Airport Code)", value="KHI")
        notes    = st.text_area("Technician Notes", height=80, placeholder="Optional notes...")

        if st.button("✅  Submit Maintenance Log", use_container_width=True):
            resp = requests.post(f"{API}/log_maintenance", json={
                "tail_number":       selected_plane,
                "component":         selected_component,
                "maintenance_type":  maint_type,
                "location":          location,
                "notes":             notes,
            })
            if resp.status_code == 200:
                result = resp.json()
                st.success(
                    f"✅ Maintenance logged! Health reset to **{result['health_reset_to']}%**. "
                    f"RUL reset to **{result['rul_reset_to']} cycles**."
                )
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"Failed to log maintenance: {resp.text}")

    # ── Full maintenance history table ──
    if maint_hist:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">Full Maintenance History</div>', unsafe_allow_html=True)
        df_maint = pd.DataFrame(maint_hist)[
            ["component", "maintenance_type", "location", "performed_at", "notes"]
        ]
        df_maint.columns = ["Component", "Type", "Location", "Date", "Notes"]
        st.dataframe(df_maint, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════
# PAGE 5 — FLIGHT SIMULATOR
# ══════════════════════════════════════════════════════════════
elif page == "🧮  Flight Simulator":

    st.markdown('<div class="aero-header">Predictive Flight Simulator</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="aero-title"><span>{selected_plane}</span> '
        f'<span style="font-size:14px;color:#7d8590;font-family:Inter">What-If Analysis</span></div>',
        unsafe_allow_html=True
    )
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    st.markdown(
        '<p style="color:#7d8590;font-size:13px;margin-bottom:1.5rem">'
        'Adjust the parameters below to simulate a hypothetical flight and predict '
        'fuel consumption, CO₂ emissions, and engine health impact.</p>',
        unsafe_allow_html=True
    )

    PAK_AIRPORTS = {
        "KHI - Karachi":      "KHI",
        "LHE - Lahore":       "LHE",
        "ISB - Islamabad":    "ISB",
        "PEW - Peshawar":     "PEW",
        "MUX - Multan":       "MUX",
        "LYP - Faisalabad":   "LYP",
        "SKT - Sialkot":      "SKT",
        "DXB - Dubai":        "DXB",
        "DOH - Doha":         "DOH",
        "JED - Jeddah":       "JED",
        "LHR - London":       "LHR",
        "IST - Istanbul":     "IST",
    }

    f1, f2 = st.columns(2)
    with f1:
        dep_label = st.selectbox("Departure Airport", list(PAK_AIRPORTS.keys()), index=0)
        age       = st.slider("Aircraft Age (years)", 0.0, 30.0,
                              float(selected_pak_data.get("age_years") or 8.0), 0.5)
        weather   = st.selectbox("Weather Conditions", ["Clear", "Moderate Wind", "Stormy"])

    with f2:
        arr_label = st.selectbox("Arrival Airport", list(PAK_AIRPORTS.keys()), index=1)
        cargo     = st.slider("Cargo Weight (kg)", 0, 50000, 15000, 500)
        st.markdown("<br>", unsafe_allow_html=True)
        run_sim   = st.button("🚀  Run Simulation", use_container_width=True)

    if run_sim:
        with st.spinner("Running simulation..."):
            resp = requests.post(f"{API}/simulate", json={
                "tail_number":       selected_plane,
                "aircraft_age_yrs":  age,
                "departure_iata":    PAK_AIRPORTS[dep_label],
                "arrival_iata":      PAK_AIRPORTS[arr_label],
                "weather":           weather,
                "cargo_kg":          float(cargo),
            })

        if resp.status_code == 200:
            sim = resp.json()["predictions"]
            flags = [f for f in resp.json().get("risk_flags", []) if f]

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="section-title">Simulation Results</div>', unsafe_allow_html=True)

            r1, r2, r3, r4 = st.columns(4)
            metrics = [
                (r1, "Estimated Fuel",    f"{sim['estimated_fuel_litres']:,.0f}", "litres",  "kpi-blue"),
                (r2, "CO₂ Emissions",     f"{sim['estimated_co2_kg']:,.0f}",      "kg",      ""),
                (r3, "Health Impact",     f"{sim['health_impact']}",              "pts",
                 "kpi-red" if sim["health_impact"] < -5 else "kpi-yellow"),
                (r4, "Flight Distance",   f"{sim['distance_km']:,.0f}",           "km",      ""),
            ]
            for col, label, value, unit, cls in metrics:
                with col:
                    st.markdown(f"""<div class="kpi-card {cls}">
                        <div class="kpi-label">{label}</div>
                        <div class="kpi-value">{value}</div>
                        <div class="kpi-unit">{unit}</div></div>""",
                        unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            detail1, detail2 = st.columns(2)
            with detail1:
                st.markdown('<div class="section-title">Flight Details</div>', unsafe_allow_html=True)
                details = [
                    ("Route",          f"{PAK_AIRPORTS[dep_label]} → {PAK_AIRPORTS[arr_label]}"),
                    ("Flight Time",    f"{sim['flight_hours']:.1f} hours"),
                    ("Next Maintenance",sim["next_maintenance_interval"]),
                    ("Aircraft Age",   f"{age} years"),
                    ("Cargo",          f"{cargo:,} kg"),
                    ("Weather",        weather),
                ]
                for label, value in details:
                    st.markdown(f"""<div class="info-row">
                        <span class="info-label">{label}</span>
                        <span class="info-value">{value}</span></div>""",
                        unsafe_allow_html=True)

            with detail2:
                if flags:
                    st.markdown('<div class="section-title">Risk Flags</div>', unsafe_allow_html=True)
                    for flag in flags:
                        st.warning(flag)
                else:
                    st.markdown('<div class="section-title">Risk Assessment</div>', unsafe_allow_html=True)
                    st.success("✅ No risk flags for this configuration.")
        else:
            st.error(f"Simulation failed: {resp.text}")
    else:
        st.markdown(
            '<div style="text-align:center;padding:3rem;color:#484f58;font-size:13px">'
            'Configure parameters above and click <b style="color:#388bfd">Run Simulation</b> to see predictions.'
            '</div>',
            unsafe_allow_html=True
        )