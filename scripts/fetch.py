"""Fetch ECMWF / GFS / ICON forecasts from Open-Meteo and save raw JSON (runs on GitHub Actions)."""
import json, time, urllib.request, urllib.parse
from datetime import datetime, timezone

LOCATIONS = {
    "samcheok": {"name": "삼척 정상동", "lat": 37.43, "lon": 129.17},
    "seokpo": {"name": "봉화 석포면", "lat": 37.05, "lon": 129.06},
}
MODELS = "ecmwf_ifs025,gfs_seamless,icon_seamless"
HOURLY = "temperature_2m,precipitation,precipitation_probability,weather_code,wind_gusts_10m"
DAILY = "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max"


def get(url):
    for i in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            err = e
            time.sleep(5 * (i + 1))
    raise err


out = {"fetched_utc": datetime.now(timezone.utc).isoformat(timespec="minutes"), "locations": {}}
for key, L in LOCATIONS.items():
    q = urllib.parse.urlencode({
        "latitude": L["lat"], "longitude": L["lon"], "models": MODELS,
        "hourly": HOURLY, "daily": DAILY, "timezone": "Asia/Seoul",
        "forecast_days": 8, "wind_speed_unit": "ms",
    })
    data = get("https://api.open-meteo.com/v1/forecast?" + q)
    out["locations"][key] = {"name": L["name"], "data": data}

with open("data/latest.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
print("ok", out["fetched_utc"])
