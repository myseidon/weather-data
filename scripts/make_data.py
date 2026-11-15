"""Turn data/latest.json (Open-Meteo raw) into the chart input JSON.

usage: python scripts/make_data.py OUT.json [--week auto|yes|no]
"""
import json, sys
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
MODELS = {"ECMWF": "ecmwf_ifs025", "GFS": "gfs_seamless", "ICON": "icon_seamless"}
WD = "월화수목금토일"

out_path = sys.argv[1]
week_mode = sys.argv[sys.argv.index("--week") + 1] if "--week" in sys.argv else "auto"
now = datetime.now(KST)
want_week = week_mode == "yes" or (week_mode == "auto" and 4 <= now.hour < 7)

raw = json.load(open("data/latest.json", encoding="utf-8"))
fetched = datetime.fromisoformat(raw["fetched_utc"]).astimezone(KST)


def num(v):
    return None if v is None else float(v)


locs, warnings, notes = [], [], []
short = {"samcheok": "삼척", "seokpo": "석포"}
for key, L in raw["locations"].items():
    h, dly = L["data"]["hourly"], L["data"]["daily"]
    times = [datetime.fromisoformat(t).replace(tzinfo=KST) for t in h["time"]]
    start = now.replace(minute=0, second=0, microsecond=0)
    i0 = next(i for i, t in enumerate(times) if t >= start)
    idx = range(i0, i0 + 24)
    models, week = {}, {}
    for label, m in MODELS.items():
        temp = [num(h[f"temperature_2m_{m}"][i]) for i in idx]
        if all(v is None for v in temp):
            notes.append(f"{short[key]} {label} 데이터 없음")
            continue
        pop = [num(h[f"precipitation_probability_{m}"][i]) for i in idx]
        models[label] = {
            "time": [f"{times[i].hour:02d}시" for i in idx],
            "temp": temp,
            "precip": [num(h[f"precipitation_{m}"][i]) or 0.0 for i in idx],
            "pop": None if all(v is None for v in pop) else pop,
            "gust_ms": [num(h[f"wind_gusts_10m_{m}"][i]) for i in idx],
            "code": [int(h[f"weather_code_{m}"][i] or 0) for i in idx],
        }
        if want_week:
            ds = [datetime.fromisoformat(d) for d in dly["time"]]
            j0 = next(j for j, d in enumerate(ds) if d.date() >= now.date())
            jdx = range(j0, min(j0 + 7, len(ds)))
            wpop = [num(dly[f"precipitation_probability_max_{m}"][j]) for j in jdx]
            week[label] = {
                "date": ["오늘" if j == j0 else f"{WD[ds[j].weekday()]} {ds[j].month}/{ds[j].day}" for j in jdx],
                "tmax": [num(dly[f"temperature_2m_max_{m}"][j]) for j in jdx],
                "tmin": [num(dly[f"temperature_2m_min_{m}"][j]) for j in jdx],
                "precip": [num(dly[f"precipitation_sum_{m}"][j]) or 0.0 for j in jdx],
                "pop": None if all(v is None for v in wpop) else wpop,
                "code": [int(dly[f"weather_code_{m}"][j] or 0) for j in jdx],
            }
    entry = {"name": L["name"], "models": models}
    if want_week and week:
        entry["week"] = week
    locs.append(entry)

    # warnings (24h)
    s = short[key]
    allT = [v for md in models.values() for v in md["temp"] if v is not None]
    allG = [v for md in models.values() for v in md["gust_ms"] if v is not None]
    wet_cold = any(p >= 0.1 and t is not None and t <= 1
                   for md in models.values() for p, t in zip(md["precip"], md["temp"]))
    if allG and max(allG) >= 14:
        warnings.append(f"{s} 강풍 (돌풍 최대 {max(allG):.0f}m/s)")
    snow = sum(p for md in models.values() for p, c in zip(md["precip"], md["code"]) if c in (71, 73, 75, 77, 85, 86)) / max(len(models), 1)
    if snow >= 5:
        warnings.append(f"{s} 대설 가능 (강수 환산 {snow:.0f}mm)")
    if allT and min(allT) <= -10:
        warnings.append(f"{s} 한파 (최저 {min(allT):.0f}℃)")
    if wet_cold or (allT and min(allT) <= 0):
        warnings.append(f"{s} 영하권·도로 결빙 주의")
    if len(models) >= 2:
        spread = max((max(v) - min(v)) for v in zip(*[md["temp"] for md in models.values()]) if None not in v)
        wet = [[p >= 0.1 for p in md["precip"]] for md in models.values()]
        split = any(len(set(col)) > 1 and sum(col) >= 1 and sum(col) < len(col) and
                    max(md["precip"][k] for md in models.values()) >= 1.0 for k, col in enumerate(zip(*wet)))
        if spread >= 3 or split:
            warnings.append(f"{s} 예보 불확실 (모델 간 차이 큼)")

data = {"generated": now.strftime("%m/%d %H:%M"), "fetched": fetched.strftime("%m/%d %H:%M"),
        "warnings": warnings, "notes": notes, "locations": locs}
json.dump(data, open(out_path, "w", encoding="utf-8"), ensure_ascii=False)

# one-line summary for the push notification
parts = []
for L in locs:
    T = [v for md in L["models"].values() for v in md["temp"] if v is not None]
    pops = [max((md["pop"] or [0])) for md in L["models"].values()]
    parts.append(f"{'삼척' if '삼척' in L['name'] else '석포'} {min(T):.0f}~{max(T):.0f}℃ 강수확률최대 {sum(pops)/len(pops):.0f}%")
print(" / ".join(parts) + (" ⚠" + ", ".join(warnings) if warnings else ""))
print("NOTES:", "; ".join(notes) if notes else "none", "| fetched", data["fetched"], "| week", want_week)
