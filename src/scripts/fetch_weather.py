import requests

def get_airport_weather(city_name="nuremberg", api_key="0f10ee70fb62baea45cca9ddad1d2da5"):
    """
    Fetches live weather data for a specific city/airport from OpenWeatherMap.
    """
    # We use metric units to get Temperature in Celsius and Wind in meter/sec
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={api_key}&units=metric"
    
    print(f"🌤️ Fetching live weather for {city_name.upper()} Airport...")

    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract the specific data we need for fuel calculations
            temp_celsius = data["main"]["temp"]
            wind_speed_ms = data["wind"]["speed"]
            wind_direction_deg = data["wind"]["deg"]
            weather_desc = data["weather"][0]["description"].title()
            
            print("✅ Weather Data Retrieved Successfully!\n")
            print("-" * 40)
            print(f"📍 Location:       {data['name']}, {data['sys']['country']}")
            print(f"🌡️ Temperature:    {temp_celsius}°C")
            print(f"💨 Wind Speed:     {wind_speed_ms} m/s")
            print(f"🧭 Wind Direction: {wind_direction_deg}°")
            print(f"☁️ Conditions:     {weather_desc}")
            print("-" * 40)
            
            # Return this as a dictionary so FastAPI can use it later
            return {
                "temperature": temp_celsius,
                "wind_speed": wind_speed_ms,
                "wind_direction": wind_direction_deg,
                "description": weather_desc
            }
            
        elif response.status_code == 401:
            print("❌ Error 401: Invalid API Key. Did Maiz activate it?")
        elif response.status_code == 404:
            print(f"❌ Error 404: City '{city_name}' not found.")
        else:
            print(f"❌ API Error: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    # Test it with Karachi (OPKC) and maybe New York (JFK)
    get_airport_weather("nuremberg", "4f7ba9337ae4f2f8bd338f49f323662d")