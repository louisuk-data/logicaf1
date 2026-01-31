import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# === CONFIG: EXACT FILE PATHS ===
DATA_DIR = r"C:\Users\louie\OneDrive\Desktop\F1_Data"

# === BRAND CONFIG ===
TEAM_COLORS = {
    "Red Bull Racing": "#0600EF", "Ferrari": "#DC0000", "McLaren": "#FF8700",
    "Mercedes": "#00D2BE", "Aston Martin": "#006F62", "Alpine": "#0090FF",
    "Williams": "#005AFF", "RB": "#6692FF", "Kick Sauber": "#52E252",
    "Haas F1 Team": "#B6BABD", "Haas": "#B6BABD", "Sauber": "#52E252",
    "AlphaTauri": "#2B4562", "Racing Bulls": "#6692FF"
}
DEFAULT_COLOR = "#FF4B4B"
TEXT_COLOR = "#332166"
BRAND_BG_COLOR = "#F3ECFF"

st.set_page_config(page_title="F1 Race Dashboard", layout="wide")

# === STYLES ===
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Viga&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');

html, body, [class*="css"], h1, h2, h3, p, div, span {{ 
    font-family: 'Viga', sans-serif !important; 
    color: {TEXT_COLOR}; 
}}
.stApp {{ background-color: #FFFFFF; }}

/* Result Row Styling */
.result-row {{ 
    display: flex; 
    align-items: center; 
    padding: 12px 0; 
    border-bottom: 2px solid {BRAND_BG_COLOR}; 
    font-family: 'Roboto', sans-serif; 
}}

.pos-col {{ width: 40px; font-size: 18px; font-weight: bold; text-align: center; margin-right: 15px; }}
.driver-col {{ width: 260px; display: flex; flex-direction: column; }}
.driver-name {{ font-size: 16px; font-weight: 700; margin-bottom: 2px; }}
.team-name {{ font-size: 12px; color: #666; text-transform: uppercase; }}
.points-col {{ width: 60px; text-align: center; font-size: 16px; font-weight: bold; color: {TEXT_COLOR}; }}

/* WIDENED COLUMNS FOR NEW NAMES */
.seas-col {{ width: 130px; text-align: center; font-size: 14px; color: #666; border-left: 1px solid #EEE; }}
.time-col {{ width: 110px; text-align: right; font-size: 14px; color: #444; font-family: 'Roboto', monospace; }}
.team-border {{ width: 4px; height: 35px; margin-right: 15px; border-radius: 2px; }}
</style>
""", unsafe_allow_html=True)

st.title("F1 Race Analysis")

# === LOAD DATA ===
@st.cache_data
def load_data():
    frames = []
    
    race_path = os.path.join(DATA_DIR, "race_laps_2024_onwards.csv")
    sprint_path = os.path.join(DATA_DIR, "sprint_laps_2024_onwards.csv")

    if os.path.exists(race_path):
        r = pd.read_csv(race_path)
        if "Session" not in r.columns: r["Session"] = "Race"
        if "Round" in r.columns: r = r.rename(columns={"Round": "RoundNumber"})
        frames.append(r)

    if os.path.exists(sprint_path):
        s = pd.read_csv(sprint_path)
        if "Session" not in s.columns: s["Session"] = "Sprint"
        if "Round" in s.columns: s = s.rename(columns={"Round": "RoundNumber"})
        frames.append(s)
        
    if not frames: return None
    df = pd.concat(frames, ignore_index=True)
    
    if "RoundNumber" in df.columns:
        df["RoundNumber"] = pd.to_numeric(df["RoundNumber"], errors='coerce')
        
    return df

df = load_data()

if df is None:
    st.error(f"No data found in {DATA_DIR}")
    st.stop()

# === SIDEBAR ===
st.sidebar.header("Data Audit")
years = sorted(df["Year"].unique(), reverse=True)
selected_year = st.sidebar.selectbox("Year", years)

# === FILTER LOGIC ===
year_df = df[df["Year"] == selected_year].copy()
year_df = year_df.sort_values(by=["RoundNumber"]) 

events = year_df["EventName"].unique()
selected_event = st.sidebar.selectbox("Event", events)

avail_sessions = year_df[year_df["EventName"] == selected_event]["Session"].unique()
default_idx = list(avail_sessions).index("Race") if "Race" in avail_sessions else 0
selected_session_type = st.sidebar.selectbox("Session", avail_sessions, index=default_idx)

session = year_df[
    (year_df["EventName"] == selected_event) & 
    (year_df["Session"] == selected_session_type)
].copy()

if session.empty:
    st.warning("No data found for this session.")
    st.stop()

# === CALCULATIONS ===
def get_session_order(s):
    return 1 if "Sprint" in str(s) else 2

year_df["SessionOrder"] = year_df["Session"].apply(get_session_order)

# Group & Sort
season_results = year_df.groupby(["Driver", "RoundNumber", "SessionOrder", "Session"])["OfficialPoints"].max().reset_index()
season_results = season_results.sort_values(by=["RoundNumber", "SessionOrder"])

# Calculate Totals
season_results["RunningTotal"] = season_results.groupby("Driver")["OfficialPoints"].cumsum()
season_results["SeasonTotal"] = season_results.groupby("Driver")["OfficialPoints"].transform("sum")

# Current Round Stats
current_round = session["RoundNumber"].iloc[0]
current_order = get_session_order(selected_session_type)

current_stats = season_results[
    (season_results["RoundNumber"] == current_round) & 
    (season_results["SessionOrder"] == current_order)
]

# === DISPLAY DATA PREP ===
session["LapTimeSeconds"] = pd.to_timedelta(session["LapTime"]).dt.total_seconds()
drivers = session.groupby("Driver").first().reset_index()
drivers["SortPos"] = pd.to_numeric(drivers["OfficialPos"], errors='coerce').fillna(999)
drivers = drivers.sort_values("SortPos").reset_index(drop=True)

total_times = session.groupby("Driver")["LapTimeSeconds"].sum().reset_index().rename(columns={"LapTimeSeconds": "TotalRaceTime"})
drivers = drivers.merge(total_times, on="Driver", how="left")
drivers = drivers.merge(current_stats[["Driver", "RunningTotal", "SeasonTotal"]], on="Driver", how="left")

if not drivers.empty:
    winner_time = drivers.iloc[0]["TotalRaceTime"]
    drivers["GapToWinner"] = drivers["TotalRaceTime"] - winner_time
else:
    drivers["GapToWinner"] = 0

drivers["Color"] = drivers["Team"].map(TEAM_COLORS).fillna(DEFAULT_COLOR)

# Helper Functions
def format_result(row):
    status = str(row["Status"])
    if status not in ["Finished", "nan", "+1 Lap", "+2 Laps", "+3 Laps"]: return status
    if row["SortPos"] == 1:
        t = row["TotalRaceTime"]
        if pd.isna(t): return "N/A"
        m, s = divmod(t, 60)
        h, m = divmod(m, 60)
        ms = int((t * 1000) % 1000)
        if h > 0: return f"{int(h)}:{int(m):02}:{int(s):02}.{ms:03}"
        return f"{int(m)}:{int(s):02}.{ms:03}"
    return f"+{row['GapToWinner']:.3f}s"

def format_pts(p):
    if pd.isna(p): return "0"
    return str(int(p)) if float(p).is_integer() else str(p)

# === HTML TABLE (Interactive Main View) ===
st.subheader(f"Results - {selected_session_type}")
st.markdown("""
<div style="display:flex; color:#888; font-size:12px; font-weight:bold; padding-bottom:5px; border-bottom:2px solid #333;">
    <div style="width:70px; text-align:center;">Pos</div>
    <div style="width:260px;">Driver / Team</div>
    <div style="width:60px; text-align:center;">Pts</div>
    <div style="width:130px; text-align:center;">Cumulative Total</div>
    <div style="width:130px; text-align:center;">Season Total</div>
    <div style="width:110px; text-align:right;">Time</div>
</div>
""", unsafe_allow_html=True)

html_content = ""
for _, row in drivers.iterrows():
    pos = row["OfficialPos"] if not pd.isna(row["OfficialPos"]) else "NC"
    
    html_content += f"""<div class="result-row">
<div class="team-border" style="background-color: {row['Color']};"></div>
<div class="pos-col">{pos}</div>
<div class="driver-col"><span class="driver-name">{row['Driver']}</span><span class="team-name">{row['Team']}</span></div>
<div class="points-col">{format_pts(row["OfficialPoints"])}</div>
<div class="seas-col">{format_pts(row["RunningTotal"])}</div>
<div class="seas-col" style="font-weight:bold;">{format_pts(row["SeasonTotal"])}</div>
<div class="time-col">{format_result(row)}</div>
</div>"""

st.markdown(html_content, unsafe_allow_html=True)

# === PACE CHART ===
st.markdown("---")
st.subheader("📈 Pace Evolution")
pace = session.groupby(["LapNumber", "Driver"])["LapTimeSeconds"].mean().reset_index().merge(drivers[["Driver", "Color"]], on="Driver", how="left")
fig_pace = go.Figure()
max_laps = pace["LapNumber"].max()
valid_drivers = pace.groupby("Driver")["LapNumber"].max()
valid_drivers = valid_drivers[valid_drivers > (max_laps * 0.2)].index
for driver in valid_drivers:
    d = pace[pace["Driver"] == driver].sort_values("LapNumber")
    if d.empty: continue
    fig_pace.add_trace(go.Scatter(x=d["LapNumber"], y=d["LapTimeSeconds"].cumsum(), mode="lines", name=driver, line=dict(color=d["Color"].iloc[0], width=2)))
fig_pace.update_layout(xaxis_title="Lap", yaxis_title="Cumulative Time (s)", plot_bgcolor=BRAND_BG_COLOR, paper_bgcolor=BRAND_BG_COLOR, font=dict(family="Viga", size=12, color=TEXT_COLOR), height=500, margin=dict(l=20, r=20, t=30, b=40))
st.plotly_chart(fig_pace, use_container_width=True)

# === DOWNLOADABLE IMAGE SECTION (HIGH FIDELITY) ===
st.markdown("---")
with st.expander("📷 Get Image of Results"):
    
    driver_team_cells = [
        f"<b>{row['Driver']}</b><br><span style='font-size:11px; color:#555'>{row['Team']}</span>"
        for _, row in drivers.iterrows()
    ]
    
    strip_colors = drivers["Color"].tolist()
    
    fig_table = go.Figure(data=[go.Table(
        columnorder = [0, 1, 2, 3, 4, 5, 6],
        columnwidth = [6, 40, 250, 60, 130, 130, 100], 
        
        header=dict(
            values=['', '<b>POS</b>', '<b>DRIVER / TEAM</b>', '<b>PTS</b>', '<b>CUMULATIVE TOTAL</b>', '<b>SEASON TOTAL</b>', '<b>TIME</b>'],
            line_color='white',
            fill_color='#332166',
            align=['center', 'center', 'left', 'center', 'center', 'center', 'right'],
            font=dict(color='white', size=12, family="Viga"),
            height=30
        ),
        
        cells=dict(
            values=[
                ['' for _ in range(len(drivers))], 
                drivers['OfficialPos'],
                driver_team_cells,                 
                drivers['OfficialPoints'].apply(format_pts),
                drivers['RunningTotal'].apply(format_pts),
                drivers['SeasonTotal'].apply(format_pts),
                drivers.apply(format_result, axis=1)
            ],
            fill_color=[
                strip_colors, 
                'white', 'white', 'white', 'white', 'white', 'white'
            ],
            font=dict(
                color=['#333', '#333', '#333', '#333', '#666', '#333', '#444'], 
                size=13, 
                family="Roboto"
            ),
            line_color='#E0E0E0',
            align=['center', 'center', 'left', 'center', 'center', 'center', 'right'],
            height=45 
        )
    )])

    fig_table.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=len(drivers) * 45 + 40,
        dragmode=False 
    )

    my_config = {
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['zoom', 'pan', 'select', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d']
    }

    st.plotly_chart(fig_table, use_container_width=True, config=my_config)
    st.caption("Hover over the table header to see the 📷 download button in the top-right.")