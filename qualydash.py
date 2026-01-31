import streamlit as st
import pandas as pd
import os

# === CONFIG: CLOUD COMPATIBLE PATH ===
# This tells the server to look for the 'data' folder in the same directory as this script
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

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

st.set_page_config(page_title="F1 Qualifying Analysis", layout="wide")

# === CSS STYLES ===
MAIN_STYLES = f"""
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
    padding: 10px 0; 
    border-bottom: 2px solid {BRAND_BG_COLOR}; 
    font-family: 'Roboto', sans-serif; 
    font-size: 14px;
}}

.pos-col {{ width: 40px; font-size: 16px; font-weight: bold; text-align: center; margin-right: 10px; }}
.driver-col {{ width: 200px; display: flex; flex-direction: column; }}
.driver-name {{ font-size: 15px; font-weight: 700; margin-bottom: 2px; }}
.team-name {{ font-size: 11px; color: #666; text-transform: uppercase; }}
.time-col {{ width: 90px; text-align: right; font-weight: bold; font-family: 'Roboto', monospace; }}
.gap-txt-col {{ width: 80px; text-align: right; color: #666; font-size: 13px; margin-right: 15px; font-family: 'Roboto', monospace; }}
.sector-col {{ width: 70px; text-align: center; color: #888; font-size: 12px; border-left: 1px solid #EEE; }}

/* BAR CHART STYLES */
.visual-col {{ width: 160px; padding: 0 5px; display: flex; align-items: center; justify-content: center; }}
.bar-container {{ width: 100%; height: 6px; background-color: #EEE; border-radius: 3px; overflow: hidden; }}
.bar-fill {{ height: 100%; border-radius: 3px; }}
.team-border {{ width: 4px; height: 35px; margin-right: 10px; border-radius: 2px; }}
"""

st.markdown(f"<style>{MAIN_STYLES}</style>", unsafe_allow_html=True)
st.title("F1 Qualifying Analysis")

# === DATA LOADING ===
@st.cache_data
def load_data():
    try:
        path = os.path.join(DATA_DIR, "qualy_laps_2024_onwards.csv")
        return pd.read_csv(path)
    except FileNotFoundError:
        return None

df = load_data()
if df is None:
    st.error(f"Data not found. I looked for 'qualy_laps_2024_onwards.csv' inside: {DATA_DIR}")
    st.stop()

# --- FILTERING ---
years = sorted(df["Year"].unique(), reverse=True)
selected_year = st.sidebar.selectbox("Year", years)
events = df[df["Year"] == selected_year]["EventName"].unique()
selected_event = st.sidebar.selectbox("Event", events)

gap_mode = st.sidebar.radio("Analysis Mode", ["Gap to Pole", "Gap to Teammate"])
sort_mode = st.sidebar.radio("Sort By", ["Classification", "Biggest Gap"]) if gap_mode == "Gap to Teammate" else "Classification"

# --- DATA PROCESSING ---
session = df[(df["Year"] == selected_year) & (df["EventName"] == selected_event)].copy()

def parse_time(t):
    try:
        if pd.isna(t) or t == "": return None
        return pd.to_timedelta(t).total_seconds()
    except:
        return None

for col in ["LapTime", "Sector1Time", "Sector2Time", "Sector3Time"]:
    session[col] = session[col].apply(parse_time)

session = session.dropna(subset=["LapTime"])

# Get Best Lap
best = session.sort_values("LapTime").drop_duplicates("Driver").reset_index(drop=True)
best["Color"] = best["Team"].map(TEAM_COLORS).fillna(DEFAULT_COLOR)
best["Q_Pos"] = best.index + 1

# Format Helper
def fmt_time(s):
    if pd.isna(s): return "-"
    m, sec = divmod(s, 60)
    return f"{int(m)}:{sec:06.3f}" if m > 0 else f"{sec:.3f}"

# --- CALCULATE GAPS ---
max_gap = 1.0

if gap_mode == "Gap to Pole":
    pole = best.iloc[0]["LapTime"]
    best["Gap"] = best["LapTime"] - pole
    max_gap = best["Gap"].max()
    if max_gap == 0: max_gap = 1
else:
    teammate_gaps = []
    for _, row in best.iterrows():
        team_laps = best[best["Team"] == row["Team"]].sort_values("LapTime")
        if len(team_laps) > 1:
            fastest_in_team = team_laps.iloc[0]["LapTime"]
            if row["LapTime"] == fastest_in_team:
                second_fastest = team_laps.iloc[1]["LapTime"]
                gap = row["LapTime"] - second_fastest
            else:
                gap = row["LapTime"] - fastest_in_team
        else:
            gap = 0
        teammate_gaps.append(gap)

    best["Gap"] = teammate_gaps
    if sort_mode == "Biggest Gap":
        best["AbsGap"] = best["Gap"].abs()
        best = best.sort_values("AbsGap", ascending=False).drop(columns=["AbsGap"])

# === HTML GENERATION LOGIC ===
visual_header = '<div style="width:160px; text-align:center;">Visual</div>' if gap_mode == "Gap to Pole" else ''

table_html = f"""
<div style="display:flex; color:#888; font-size:12px; font-weight:bold; padding-bottom:5px; border-bottom:2px solid #333;">
<div style="width:40px; text-align:center;">Pos</div>
<div style="width:200px;">Driver / Team</div>
<div style="width:90px; text-align:right;">Time</div>
<div style="width:80px; text-align:right; margin-right:15px;">Gap</div>
{visual_header}
<div style="width:70px; text-align:center;">S1</div>
<div style="width:70px; text-align:center;">S2</div>
<div style="width:70px; text-align:center;">S3</div>
</div>
"""

for _, row in best.iterrows():
    gap_val = row["Gap"]
    
    # Visual Column Logic
    visual_html = ""
    if gap_mode == "Gap to Pole":
        pct = (gap_val / max_gap) * 100 if max_gap > 0 else 0
        bar_div = f'<div class="bar-fill" style="width:{pct}%; background-color:{row["Color"]};"></div>'
        visual_html = f'<div class="visual-col"><div class="bar-container">{bar_div}</div></div>'
        gap_str = "POLE" if gap_val == 0 else f"+{gap_val:.3f}s"
    else:
        visual_html = "" 
        gap_str = f"{gap_val:+.3f}s" if gap_val != 0 else "-"

    table_html += f"""
<div class="result-row">
<div class="team-border" style="background-color:{row['Color']};"></div>
<div class="pos-col">{row['Q_Pos']}</div>
<div class="driver-col">
<span class="driver-name">{row['Driver']}</span>
<span class="team-name">{row['Team']}</span>
</div>
<div class="time-col">{fmt_time(row['LapTime'])}</div>
<div class="gap-txt-col">{gap_str}</div>
{visual_html}
<div class="sector-col">{row['Sector1Time']:.3f}</div>
<div class="sector-col">{row['Sector2Time']:.3f}</div>
<div class="sector-col">{row['Sector3Time']:.3f}</div>
</div>
"""

# === DISPLAY TABLE ===
st.subheader(f"{gap_mode} — {selected_event}")
st.markdown(table_html, unsafe_allow_html=True)

# === DOWNLOAD SECTION ===
st.markdown("---")
st.subheader("Downloads")

col1, col2 = st.columns(2)

# 1. HTML Download
full_html_file = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>F1 Results - {selected_event}</title>
<style>
body {{ font-family: sans-serif; padding: 20px; background-color: white; }}
{MAIN_STYLES}
</style>
</head>
<body>
<h2>{gap_mode} — {selected_event} ({selected_year})</h2>
{table_html}
<p style="margin-top:20px; font-size:12px; color:#888;">Generated by F1 Race Analysis</p>
</body>
</html>
"""

with col1:
    st.download_button(
        label="📄 Download Formatted HTML",
        data=full_html_file,
        file_name=f"qualifying_results_{selected_event}_{selected_year}.html",
        mime="text/html"
    )

# 2. CSV Download
with col2:
    csv_data = best.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📊 Download Data (CSV)",
        data=csv_data,
        file_name=f"qualifying_data_{selected_event}_{selected_year}.csv",
        mime="text/csv"
    )
