import requests
import sqlite3
from datetime import datetime

# Define where the database will live (Ruhab's domain)
DB_PATH = "src/backend/aviation_data.db"

def setup_database():
    """Creates the database and table if Ruhab hasn't given it to us yet."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create the flight_telemetry table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flight_telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            callsign TEXT,
            altitude REAL,
            velocity REAL,
            latitude REAL,
            longitude REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def fetch_and_store_flights():
    """Fetches live flights and inserts them into the SQLite database."""
    url = "https://opensky-network.org/api/states/all"
    params = {"lamin": -10.0, "lomin": 40.0, "lamax": 55.0, "lomax": 150.0}
    
    print("📡 Pinging OpenSky Network API...")
    
    try:
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            states = response.json().get("states")
            
            if not states:
                print("⚠️ No flights detected.")
                return

            print(f"✅ Success! Found {len(states)} flights. Inserting into Database...")
            
            # Connect to DB
            conn = setup_database()
            cursor = conn.cursor()
            
            insert_count = 0
            for flight in states:
                callsign = flight[1].strip() if flight[1] else "UNKNOWN"
                longitude = flight[5]
                latitude = flight[6]
                altitude = flight[7]
                velocity = flight[9]

                # Only insert valid, airborne flights
                if altitude is not None and velocity is not None:
                    cursor.execute('''
                        INSERT INTO flight_telemetry (callsign, altitude, velocity, latitude, longitude)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (callsign, altitude, velocity, latitude, longitude))
                    insert_count += 1
            
            # Save the changes to the database!
            conn.commit()
            conn.close()
            
            print(f"💾 Successfully saved {insert_count} flights into 'aviation_data.db'!")

        else:
            print(f"❌ Error {response.status_code}: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    fetch_and_store_flights()