import fastf1
import pandas as pd
from datetime import datetime
import os

# === CONFIGURATION ===
OUTPUT_DIR = r"C:\Users\louie\OneDrive\Desktop\F1_Data"
CACHE_DIR = os.path.join(OUTPUT_DIR, 'cache')

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

fastf1.Cache.enable_cache(CACHE_DIR)

def get_data_for_years(start_year):
    # Current date (Jan 31, 2026)
    current_year = datetime.now().year
    
    # We will build these lists up year by year
    all_race_laps = []
    all_sprint_laps = []

    print(f"Target Folder: {OUTPUT_DIR}")

    # Loop through 2024, 2025, 2026
    for year in range(start_year, current_year + 1):
        print(f"\n=== PROCESSING YEAR {year} ===")
        
        try:
            # 1. Get Schedule
            try:
                schedule = fastf1.get_event_schedule(year)
            except Exception as e:
                print(f"⚠️ Could not fetch schedule for {year} (Data might not exist yet). Skipping.")
                continue

            # 2. Filter for completed events
            completed_events = schedule[schedule['EventDate'] < pd.Timestamp(datetime.now())]
            
            if completed_events.empty:
                print(f"No completed events found for {year}.")
                continue

            # 3. Process Events
            for _, event in completed_events.iterrows():
                # Skip testing
                if event['EventFormat'] == 'testing': continue

                rnd = event['RoundNumber']
                name = event['EventName']
                print(f"  Round {rnd}: {name}")

                # --- HELPER FUNCTION ---
                def load_session(code, label):
                    try:
                        session = fastf1.get_session(year, rnd, code)
                        session.load(telemetry=False, weather=False, messages=False)
                        
                        if not hasattr(session, 'laps') or session.laps.empty:
                            return None

                        laps = session.laps
                        
                        # Merge Points/Positions
                        if hasattr(session, 'results') and not session.results.empty:
                            res = session.results.reset_index()
                            # Keep only available columns
                            cols = ['Abbreviation', 'ClassifiedPosition', 'Points', 'Status']
                            res = res[[c for c in cols if c in res.columns]]
                            res = res.rename(columns={'Abbreviation': 'Driver', 'ClassifiedPosition': 'OfficialPos', 'Points': 'OfficialPoints'})
                            laps = laps.merge(res, on='Driver', how='left')

                        laps['Year'] = year
                        laps['RoundNumber'] = rnd
                        laps['EventName'] = name
                        laps['Session'] = label
                        return laps
                    except Exception:
                        return None

                # Load Race
                r = load_session('R', 'Race')
                if r is not None: all_race_laps.append(r)

                # Load Sprint
                if event['EventFormat'] in ['sprint', 'sprint_shootout', 'sprint_qualifying']:
                    s = load_session('S', 'Sprint')
                    if s is not None: all_sprint_laps.append(s)

            # === CRITICAL FIX: SAVE AFTER EVERY YEAR ===
            # This ensures that if 2026 crashes, 2025 is already saved.
            if all_race_laps:
                path_r = os.path.join(OUTPUT_DIR, 'race_laps_2024_onwards.csv')
                pd.concat(all_race_laps).to_csv(path_r, index=False)
                print(f"  >> Saved progress to {path_r}")
            
            if all_sprint_laps:
                path_s = os.path.join(OUTPUT_DIR, 'sprint_laps_2024_onwards.csv')
                pd.concat(all_sprint_laps).to_csv(path_s, index=False)
                print(f"  >> Saved progress to {path_s}")

        except Exception as e:
            print(f"❌ CRASHED while processing {year}: {e}")
            print("Don't worry, previous years were saved.")

if __name__ == "__main__":
    get_data_for_years(2024)