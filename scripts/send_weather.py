import requests
import os

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def get_weather_emoji(desc):
    desc = desc.lower()
    if "thunder" in desc: return "⛈️"
    if "heavy rain" in desc: return "🌧️"
    if "rain" in desc or "drizzle" in desc: return "🌦️"
    if "cloud" in desc: return "⛅"
    if "fog" in desc or "mist" in desc: return "🌫️"
    if "snow" in desc: return "❄️"
    if "sunny" in desc or "clear" in desc: return "☀️"
    return "🌤️"

resp = requests.get("https://wttr.in/Hanoi?format=j1", timeout=10)
data = resp.json()

c = data["current_condition"][0]
w = data["weather"][0]

current_desc = c["weatherDesc"][0]["value"]
emoji = get_weather_emoji(current_desc)

hourly_lines = []
for h in w["hourly"]:
    t = str(h["time"]).zfill(4)
    hour = int(t[:2])
    if hour in [6, 9, 12, 15, 18]:
        desc = h["weatherDesc"][0]["value"]
        rain = int(h["chanceofrain"])
        e = get_weather_emoji(desc)
        rain_txt = f" 🌂{rain}%" if rain > 30 else ""
        hourly_lines.append(f"  `{hour:02d}h` {h['tempC']}°C {e}{rain_txt}")

hourly_text = "\n".join(hourly_lines)

feels = int(c["FeelsLikeC"])
temp = int(c["temp_C"])
heat_warn = "\n⚠️ _Nắng nóng, nhớ uống nước và chống nắng!_" if feels >= 38 else ""
rain_warn = "\n☂️ _Có thể mưa, nhớ mang ô!_" if int(w.get("hourly", [{}])[0].get("chanceofrain", 0)) > 50 else ""

message = f"""{emoji} *Thời tiết Hà Nội hôm nay*

🌡 Hiện tại: *{temp}°C* (cảm giác *{feels}°C*)
🌈 Trời: {current_desc}
💧 Độ ẩm: {c["humidity"]}%
💨 Gió: {c["windspeedKmph"]} km/h

📊 *Dự báo trong ngày*
  🔺 Cao nhất: *{w["maxtempC"]}°C*
  🔻 Thấp nhất: *{w["mintempC"]}°C*

{hourly_text}{heat_warn}{rain_warn}"""

resp = requests.post(
    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
    json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"},
    timeout=10
)
print(f"Telegram response: {resp.status_code} - {resp.text[:100]}")
