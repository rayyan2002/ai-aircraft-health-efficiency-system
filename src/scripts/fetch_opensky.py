import requests
import time

def fetch_live_flights_asia():
    """
    Fetches live flight data from OpenSky Network using a Bounding Box for Asia.
    """
    url = "https://opensky-network.org/api/states/all"

    # Bounding Box for the Asian Continent
    # lamin (South - Indonesia), lomin (West - Middle East), 
    # lamax (North - Russia/China border), lomax (East - Japan)
    params = {
        "lamin": -10.0,
        "lomin": 40.0,
        "lamax": 55.0,
        "lomax": 150.0
    }
    
    print(f"📡 Pinging OpenSky Network API for Asian Airspace...")
    
    try:
        # 15-second timeout because querying a whole continent takes a moment
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            states = data.get("states")
            
            if not states:
                print("⚠️ No flights currently detected in this bounding box.")
                return

            print(f"✅ Success! Found {len(states)} live flights across Asia.\n")
            print("-" * 65)
            print(f"{'CALLSIGN':<12} | {'ALTITUDE (m)':<12} | {'VELOCITY (m/s)':<15} | {'LATITUDE':<10} | {'LONGITUDE':<10}")
            print("-" * 65)

            # Let's just print the first 20 flights so we don't flood your terminal
            display_limit = 20
            count = 0

            for flight in states:
                if count >= display_limit:
                    break
                    
                # OpenSky indices: 1=Callsign, 5=Longitude, 6=Latitude, 7=Altitude, 9=Velocity
                callsign = flight[1].strip() if flight[1] else "UNKNOWN"
                longitude = flight[5]
                latitude = flight[6]
                altitude = flight[7]
                velocity = flight[9]

                # Filter out planes on the ground (where altitude or velocity is None)
                if altitude is not None and velocity is not None:
                     print(f"{callsign:<12} | {altitude:<12} | {velocity:<15} | {latitude:<10.4f} | {longitude:<10.4f}")
                     count += 1
            
            print("-" * 65)
            print(f"... and {len(states) - display_limit} more flights currently in the air.")

        elif response.status_code == 429:
            print("❌ Error 429: Rate limit exceeded. OpenSky allows anonymous users a limited number of requests. Please wait a minute.")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    fetch_live_flights_asia()