import requests

class WeatherTool:
    def __init__(self):
        self.ToolName = "GetWeather"
        self.Schema = {
            "type": "function",
            "function": {
                "name": self.ToolName,
                "description": "Mengambil informasi cuaca saat ini dari seluruh dunia secara akurat menggunakan Open-Meteo. Gunakan ini jika pengguna menanyakan cuaca, suhu, hujan, dll di suatu lokasi.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "Nama kota, kabupaten, atau daerah. (Contoh: 'Jakarta', 'Tangsel', 'Pamulang', 'Tokyo')",
                        }
                    },
                    "required": ["location"],
                },
            },
        }

    def _get_weather_description(self, wmo_code):
        # WMO Weather interpretation codes (WW)
        # https://open-meteo.com/en/docs
        codes = {
            0: "Cerah (Clear sky)",
            1: "Sebagian Besar Cerah (Mainly clear)",
            2: "Berawan Sebagian (Partly cloudy)",
            3: "Mendung / Berawan Penuh (Overcast)",
            45: "Berkabut (Fog)",
            48: "Kabut Tebal (Depositing rime fog)",
            51: "Gerimis Ringan (Light Drizzle)",
            53: "Gerimis Sedang (Moderate Drizzle)",
            55: "Gerimis Lebat (Dense Drizzle)",
            61: "Hujan Ringan (Slight Rain)",
            63: "Hujan Sedang (Moderate Rain)",
            65: "Hujan Lebat (Heavy Rain)",
            71: "Salju Ringan (Slight Snow)",
            73: "Salju Sedang (Moderate Snow)",
            75: "Salju Lebat (Heavy Snow)",
            95: "Badai Petir Ringan/Sedang (Thunderstorm)",
            96: "Badai Petir dengan Hujan Es Ringan",
            99: "Badai Petir dengan Hujan Es Lebat"
        }
        return codes.get(wmo_code, "Tidak diketahui")

    def Execute(self, Arguments):
        location = Arguments.get("location")
        if not location:
            return "Error: Argumen 'location' kosong."

        try:
            # Step 1: Geocoding (Convert city name to coordinates)
            geo_url = "https://geocoding-api.open-meteo.com/v1/search"
            geo_params = {
                "name": location,
                "count": 1,
                "language": "id",
                "format": "json"
            }
            geo_res = requests.get(geo_url, params=geo_params, timeout=10)
            geo_data = geo_res.json()
            
            if "results" not in geo_data or not geo_data["results"]:
                return f"Maaf, lokasi '{location}' tidak ditemukan dalam database cuaca."
            
            city_info = geo_data["results"][0]
            lat = city_info["latitude"]
            lon = city_info["longitude"]
            city_name = city_info.get("name", location)
            country = city_info.get("country", "")
            
            # Step 2: Fetch Weather Forecast
            weather_url = "https://api.open-meteo.com/v1/forecast"
            weather_params = {
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true",
                "timezone": "auto"
            }
            
            weather_res = requests.get(weather_url, params=weather_params, timeout=10)
            weather_data = weather_res.json()
            
            if "current_weather" not in weather_data:
                return f"Gagal mengambil data cuaca untuk {city_name}."
                
            current = weather_data["current_weather"]
            temp = current.get("temperature")
            windspeed = current.get("windspeed")
            weathercode = current.get("weathercode")
            
            condition = self._get_weather_description(weathercode)
            
            return (
                f"Laporan Cuaca untuk {city_name}, {country}:\n"
                f"- Kondisi: {condition}\n"
                f"- Suhu: {temp}°C\n"
                f"- Kecepatan Angin: {windspeed} km/h\n"
            )
            
        except Exception as e:
            return f"Terjadi kesalahan saat mengecek cuaca: {str(e)}"
