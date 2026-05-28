import urllib.request
import urllib.parse
import json
import ssl

def get_weather(city: str) -> str:
    context = ssl._create_unverified_context()
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # 1. Geocoding
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1&language=id&format=json"
    req_geo = urllib.request.Request(geo_url, headers=headers)
    try:
        with urllib.request.urlopen(req_geo, context=context, timeout=5) as response:
            geo_data = json.loads(response.read().decode('utf-8'))
            results = geo_data.get("results", [])
            if not results:
                return f"Kota '{city}' tidak ditemukan."
            
            location = results[0]
            lat = location.get("latitude")
            lon = location.get("longitude")
            name = location.get("name")
            country = location.get("country", "")
            
        # 2. Get Weather
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        req_weather = urllib.request.Request(weather_url, headers=headers)
        with urllib.request.urlopen(req_weather, context=context, timeout=5) as response:
            weather_data = json.loads(response.read().decode('utf-8'))
            current = weather_data.get("current_weather", {})
            temp = current.get("temperature")
            windspeed = current.get("windspeed")
            weathercode = current.get("weathercode")
            
            # Simple weather code mapping
            weather_desc = {
                0: "Cerah",
                1: "Utamanya Cerah", 2: "Berawan Sebagian", 3: "Mendung",
                45: "Berkabut", 48: "Kabut Rime",
                51: "Gerimis Ringan", 53: "Gerimis Sedang", 55: "Gerimis Lebat",
                61: "Hujan Ringan", 63: "Hujan Sedang", 65: "Hujan Lebat",
                80: "Hujan Shower Ringan", 81: "Hujan Shower Sedang", 82: "Hujan Shower Lebat",
                95: "Badai Petir"
            }
            desc = weather_desc.get(weathercode, "Tidak diketahui")
            
            return f"Cuaca saat ini di {name}, {country}:\nSuhu: {temp}°C\nKondisi: {desc}\nKecepatan Angin: {windspeed} km/h"
            
    except Exception as e:
        return f"Gagal mendapatkan cuaca: {str(e)}"

if __name__ == "__main__":
    print(get_weather("Jakarta"))
    print("\n---\n")
    print(get_weather("London"))
