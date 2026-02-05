import streamlit as st
import pandas as pd
import os
from PIL import Image, ImageDraw, ImageFont
import io

# === BRAND CONFIG ===
DATA_DIR = "data"  # GitHub-safe relative path

TEAM_COLORS = {
    "Red Bull Racing": "#0600EF", "Ferrari": "#DC0000", "McLaren": "#FF8700",
    "Mercedes": "#00D2BE", "Aston Martin": "#006F62", "Alpine": "#0090FF",
    "Williams": "#005AFF", "RB": "#6692FF", "Kick Sauber": "#52E252",
    "Haas F1 Team": "#B6BABD", "Haas": "#B6BABD", "Sauber": "#52E252",
    "AlphaTauri": "#2B4562", "Racing Bulls": "#6692FF"
}
DEFAULT_COLOR = "#FF4B4B"

CARD_BG = "#F3ECFF"   # Your brand card background
FONT_PRIMARY = "Viga" # Your brand font

st.set_page_config(page_title="F1 Qualifying", layout="centered")

# Inject Google Font (Viga)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Viga&display=swap');

html, body, [class*="css"] {
    font-family: 'Viga', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)

# === LOAD DATA ===
@st.cache_data
def load_data():
    try:
        path = os.path.join(DATA_DIR, "qualy_laps_2024_onwards.csv")
        return pd.read_csv(path)
    except FileNotFoundError:
        return None

df = load_data()
if df is None:
    st.error("Data not found in /data. Please upload qualy_laps_2024_onwards.csv.")
    st.stop()

# === FILTERS ===
years = sorted(df["Year"].unique(), reverse=True)
selected_year = st.selectbox("Season", years)

events = df[df["Year"] == selected_year]["EventName"].unique()
selected_event = st.selectbox("Grand Prix", events)

gap_mode = st.radio("Gap Mode", ["Gap to Pole", "Gap to Teammate"])

# === PROCESSING ===
session = df[(df["Year"] == selected_year) & (df["EventName"] == selected_event)].copy()

def parse_time(t):
    try:
        if pd.isna(t) or t == "":
            return None
        return pd.to_timedelta(t).total_seconds()
    except:
        return None

for col in ["LapTime", "Sector1Time", "Sector2Time", "Sector3Time"]:
    session[col] = session[col].apply(parse_time)

session = session.dropna(subset=["LapTime"])

best = session.sort_values("LapTime").drop_duplicates("Driver").reset_index(drop=True)
best["Color"] = best["Team"].map(TEAM_COLORS).fillna(DEFAULT_COLOR)
best["Pos"] = best.index + 1

def fmt_time(s):
    if pd.isna(s):
        return "-"
    m, sec = divmod(s, 60)
    return f"{int(m)}:{sec:06.3f}" if m > 0 else f"{sec:.3f}"

# === GAP CALCULATION ===
if gap_mode == "Gap to Pole":
    pole = best.iloc[0]["LapTime"]
    best["Gap"] = best["LapTime"] - pole
else:
    gaps = []
    for _, row in best.iterrows():
        team_laps = best[best["Team"] == row["Team"]].sort_values("LapTime")
        if len(team_laps) > 1:
            fastest = team_laps.iloc[0]["LapTime"]
            if row["LapTime"] == fastest:
                second = team_laps.iloc[1]["LapTime"]
                gap = row["LapTime"] - second
            else:
                gap = row["LapTime"] - fastest
        else:
            gap = 0
        gaps.append(gap)
    best["Gap"] = gaps

# === FORMATTED FIELDS FOR IMAGE EXPORT ===
best["LapTime_fmt"] = best["LapTime"].apply(fmt_time)
best["Gap_fmt"] = best["Gap"].apply(
    lambda g: "POLE" if g == 0 and gap_mode == "Gap to Pole" else f"{g:+.3f}s"
)

# === HEADER ===
st.title(f"{selected_event} — Qualifying")
st.caption(f"Season {selected_year}")

# === DRIVER CARDS (F1 App Style) ===
for _, row in best.iterrows():
    with st.container(border=True):
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:12px; background:{CARD_BG}; padding:12px; border-radius:10px;">
                <div style="width:6px; height:50px; background:{row['Color']}; border-radius:4px;"></div>
                <div style="flex:1;">
                    <div style="font-size:20px; font-weight:700;">{row['Pos']}. {row['Driver']}</div>
                    <div style="font-size:13px; opacity:0.7;">{row['Team']}</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:18px; font-weight:700;">{row['LapTime_fmt']}</div>
                    <div style="font-size:13px; opacity:0.7;">{row['Gap_fmt']}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div style="display:flex; justify-content:space-between; margin-top:6px; font-size:13px;">
                <div>S1: {row['Sector1Time']:.3f}</div>
                <div>S2: {row['Sector2Time']:.3f}</div>
                <div>S3: {row['Sector3Time']:.3f}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

# === IMAGE RENDERER (PORTRAIT) ===
def render_results_image(best, event, year):
    width = 1080
    card_height = 180
    padding = 40
    total_height = padding + len(best) * (card_height + 20)

    img = Image.new("RGB", (width, total_height), CARD_BG)
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("arial.ttf", 60)
        name_font = ImageFont.truetype("arial.ttf", 48)
        small_font = ImageFont.truetype("arial.ttf", 36)
    except:
        title_font = name_font = small_font = ImageFont.load_default()

    draw.text((padding, padding), f"{event} — Qualifying {year}", fill="black", font=title_font)
    y = padding + 100

    for _, row in best.iterrows():
        draw.rectangle([padding, y, width - padding, y + card_height], fill=CARD_BG)
        draw.rectangle([padding, y, padding + 12, y + card_height], fill=row["Color"])

        draw.text((padding + 30, y + 10), f"{row['Pos']}. {row['Driver']}", fill="black", font=name_font)
        draw.text((padding + 30, y + 80), row["Team"], fill="#555", font=small_font)

        draw.text((width - padding - 300, y + 20), row["LapTime_fmt"], fill="black", font=name_font)
        draw.text((width - padding - 300, y + 90), row["Gap_fmt"], fill="#444", font=small_font)

        y += card_height + 20

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# === EXPORT SECTION ===
st.markdown("---")
st.subheader("Export")

# CSV
csv_data = best.to_csv(index=False).encode("utf-8")
st.download_button(
    label="📊 Download CSV",
    data=csv_data,
    file_name=f"qualifying_{selected_event}_{selected_year}.csv",
    mime="text/csv"
)

# PNG IMAGE
image_bytes = render_results_image(best, selected_event, selected_year)
st.download_button(
    label="📸 Download as Image (PNG)",
    data=image_bytes,
    file_name=f"qualifying_{selected_event}_{selected_year}.png",
    mime="image/png"
)
