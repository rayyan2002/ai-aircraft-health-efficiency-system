import sqlite3
from datetime import datetime

# 1. Connect to your database
db_path = "aviation_data.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 2. Pick a plane that is currently flying (use a real callsign from your DB)
# If you aren't sure, let's just use the fallback one!
target_tail_number = "AIC1713" 

print(f"Injecting fake landing data for {target_tail_number}...")

# 3. Insert a row with 0 altitude and 0 velocity to simulate a landing
cursor.execute("""
    INSERT INTO flight_telemetry 
    (callsign, altitude, velocity, latitude, longitude, timestamp) 
    VALUES (?, ?, ?, ?, ?, ?)
""", (target_tail_number, 0, 0, 24.86, 67.00, datetime.now()))

# 4. Save and close
conn.commit()
conn.close()

print("✅ Fake landing injected! Watch your FastAPI terminal...")