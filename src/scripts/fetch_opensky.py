import requests
import sqlite3
from datetime import datetime
import os

# 1. Get the directory where this script lives (.../src/scripts)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Step up one level to the main 'src' folder (.../src)
SRC_DIR = os.path.dirname(SCRIPT_DIR)

# 3. Step down into the backend folder where the real DB lives
DB_PATH = os.path.join(SRC_DIR, "backend", "aviation_data.db")

print(f"🔗 Connecting to database at: {DB_PATH}")
def fetch_live_flights_pakistan():
    """
    Fetches live flight data for Pakistan and saves it to the SQLite database.
    """
    url = "https://opensky-network.org/api/states/all"

    # Bounding Box for the pakistan
    params = {
        "lamin": 20.0, "lomin": 55.0,
        "lamax": 40.0, "lomax": 80.0
    }

    print("📡 Pinging OpenSky Network API for Pakistani Airspace...")
    
    try:
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            states = data.get("states")
            
            if not states:
                print("⚠️ No flights currently detected in this bounding box.")
                return

            print(f"✅ Success! Found {len(states)} live flights. Saving to database...")
            
            # --- DATABASE CONNECTION ---
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            inserted_count = 0
            limit = 50 # Let's only save 50 planes per cycle so we don't bloat the DB during tests

            for flight in states:
                if inserted_count >= limit:
                    break
                    
                # 1. EXTRACT DATA (Including the physical ICAO24 tail number)
                icao24_tail = str(flight[0]).strip().upper() if flight[0] else "UNKNOWN"
                active_callsign = str(flight[1]).strip().upper() if flight[1] else "NO_CALL"
                
                longitude = flight[5]
                latitude = flight[6]
                altitude = flight[7]
                velocity = flight[9]

                # Filter out planes on the ground or missing critical GPS data
                if altitude is not None and velocity is not None and latitude is not None and longitude is not None:
                    
                    # 2. INSERT INTO DATABASE
                    # Note: You mentioned you have an 'anomaly_flag' column. 
                    # We pass 0 (False) as the default value here.
                    cursor.execute("""
                        INSERT INTO flight_telemetry 
                        (tail_number, callsign, altitude, velocity, latitude, longitude, anomaly_flag, timestamp) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (icao24_tail, active_callsign, altitude, velocity, latitude, longitude, 0, datetime.now()))
                    
                    inserted_count += 1

            # 3. SAVE AND CLOSE
            conn.commit()
            conn.close()
            
            print(f"💾 Successfully saved {inserted_count} active flights to 'flight_telemetry' table.")

        elif response.status_code == 429:
            print("❌ Error 429: Rate limit exceeded. Wait a minute before running again.")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Connection Error: {e}")
    except sqlite3.Error as sql_e:
        print(f"❌ Database Error: {sql_e}")

if __name__ == "__main__":
    fetch_live_flights_pakistan()