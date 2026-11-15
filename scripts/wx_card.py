import json, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle, FancyBboxPatch

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK KR"
plt.rcParams["axes.unicode_minus"] = False

d = json.load(open(sys.argv[1], encoding="utf-8"))
prefix = sys.argv[2]


def kind(code, t, p):
    if code in (71, 73, 75, 77, 85, 86): return "snow"
    if code in (95, 96, 99): return "storm"
    if p >= 0.1 or code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "snow" if t <= 0.5 else "rain"
    if code in (45, 48): return "fog"
    if code == 0: return "sun"
    if code in (1, 2): return "partly"
    return "cloud"


KOR = {"sun": "맑음", "partly": "구름조금", "cloud": "흐림", "rain": "비", "snow": "눈", "storm": "뇌우", "fog": "안개"}


def cloud(ax, x, y, s, col="white"):
    for dx, dy, r in ((-0.35, -0.05, 0.32), (0.05, 0.12, 0.42), (0.42, -0.05, 0.3)):
        ax.add_patch(Circle((x + dx * s, y + dy * s), r * s, color=col, zorder=5))
    ax.add_patch(FancyBboxPatch((x - 0.65 * s, y - 0.35 * s), 1.3 * s, 0.32 * s,
                                boxstyle="round,pad=0,rounding_size=0.15", color=col, zorder=5, lw=0))


def icon(ax, x, y, k, s=0.42, night=False):
    if k == "sun":
        ax.add_patch(Circle((x, y), 0.32 * s, color="#ffe9a8" if night else "#ffc928", zorder=5))
        if not night:
            for a in np.linspace(0, 2 * np.pi, 8, endpoint=False):
                ax.plot([x + 0.45 * s * np.cos(a), x + 0.6 * s * np.cos(a)],
                        [y + 0.45 * s * np.sin(a), y + 0.6 * s * np.sin(a)], color="#ffc928", lw=1.6, zorder=5)
        return
    if k == "partly":
        ax.add_patch(Circle((x + 0.3 * s, y + 0.25 * s), 0.28 * s, color="#ffe9a8" if night else "#ffc928", zorder=4))
        cloud(ax, x - 0.05 * s, y - 0.05 * s, s * 0.9)
        return
    grey = k in ("rain", "snow", "storm")
    cloud(ax, x, y + 0.1 * s, s, "#dfe6ee" if grey else "white")
    if k == "fog":
        for i in range(3):
            ax.plot([x - 0.5 * s, x + 0.5 * s], [y - (0.45 + 0.15 * i) * s] * 2, color="white", lw=1.4, zorder=5)
    if k == "rain":
        for dx in (-0.35, 0, 0.35):
            ax.plot([x + dx * s, x + (dx - 0.12) * s], [y - 0.4 * s, y - 0.68 * s], color="#7cc4ff", lw=2, zorder=5)
    if k == "snow":
        for dx in (-0.35, 0, 0.35):
            ax.text(x + dx * s, y - 0.58 * s, "*", color="white", fontsize=13, ha="center", va="center", zorder=6, fontweight="bold")
    if k == "storm":
        ax.plot([x, x - 0.15 * s, x + 0.1 * s, x - 0.05 * s], [y - 0.3 * s, y - 0.55 * s, y - 0.55 * s, y - 0.8 * s],
                color="#ffd400", lw=2, zorder=6)


for li, L in enumerate(d["locations"]):
    models = L["models"]
    names = list(models)
    ref = models[names[0]]
    n = len(ref["time"])
    arr = lambda key: np.array([[v if v is not None else np.nan for v in models[m][key]] for m in names], float)
    T, P, G = arr("temp"), arr("precip"), arr("gust_ms")
    tmean, tmin, tmax = np.nanmean(T, 0), np.nanmin(T, 0), np.nanmax(T, 0)
    pmean = np.nanmean(P, 0)
    agree = (np.nan_to_num(P) >= 0.1).sum(0) / len(names) * 100
    pagree = agree.copy()
    POP = np.array([[v if v is not None else np.nan for v in (models[m].get("pop") or [None] * n)] for m in names], float)
    with np.errstate(all="ignore"):
        popm = np.nanmean(POP, 0)
    pagree = np.where(np.isnan(popm), pagree, popm)
    gmax = np.nanmax(G, 0)
    em = models.get("ECMWF", ref)
    wetflag = (agree >= 50) | (pagree >= 50)
    kinds = [kind(em["code"][i], tmean[i], pmean[i] if wetflag[i] else 0) for i in range(n)]
    hours = [int(str(t).replace("시", "")[:2]) for t in ref["time"]]
    night = [h >= 18 or h < 6 for h in hours]

    wk = L.get("week")
    WKH = 5.6 if wk else 0.0
    W, H = 7.2, 15.0 + WKH
    fig = plt.figure(figsize=(W, H))
    bg = fig.add_axes([0, 0, 1, 1]); bg.axis("off")
    grad = np.linspace(0, 1, 256).reshape(-1, 1)
    bg.imshow(grad, aspect="auto", cmap=matplotlib.colors.LinearSegmentedColormap.from_list(
        "g", ["#b9cad8", "#6f8aa0", "#3f5f7a", "#2c4a68"]), extent=(0, 1, 0, 1))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

    lo, hi = np.nanmin(tmean), np.nanmax(tmean)
    ax.text(0.55, H - 0.75, "◉ " + L["name"], fontsize=24, color="white", fontweight="bold", va="center")
    ax.text(0.5, H - 2.05, f"{tmean[0]:.0f}°", fontsize=78, color="white", va="center", fontweight="normal")
    icon(ax, W - 1.6, H - 2.0, kinds[0], s=1.3, night=night[0])
    ax.text(0.6, H - 3.35, KOR[kinds[0]], fontsize=22, color="white", fontweight="bold", va="center")
    ax.text(0.6, H - 4.0, f"↑ {hi:.0f}°  /  ↓ {lo:.0f}°", fontsize=15, color="white", va="center")
    ax.text(W - 0.5, H - 4.0, f"{d['generated']} 기준", fontsize=11, color="#eef3f8", va="center", ha="right")

    rainy = [i for i in range(n) if wetflag[i]]
    if rainy:
        k = "눈" if any(kinds[i] == "snow" for i in rainy) else "비"
        summ = f"{ref['time'][rainy[0]]}~{ref['time'][rainy[-1]]} {k} 예상 · 최고 {hi:.0f}°C"
    else:
        summ = f"강수 없음 · 최고 {hi:.0f}°C, 최저 {lo:.0f}°C"
    ax.text(0.6, H - 4.7, summ, fontsize=14, color="white", fontweight="bold", va="center")

    warn = [w for w in (d.get("warnings") or []) if L["name"].split()[0] in w or not any(
        x["name"].split()[0] in w for x in d["locations"])]
    top = H - 5.25
    if warn:
        wh = 0.45 + 0.42 * len(warn)
        ax.add_patch(FancyBboxPatch((0.35, top - wh), W - 0.7, wh, boxstyle="round,pad=0,rounding_size=0.25",
                                    color="#c62828", alpha=0.85, lw=0, zorder=2))
        for j, w in enumerate(warn):
            ax.text(0.6, top - 0.42 - 0.42 * j, "⚠ " + w, fontsize=12.5, color="white", fontweight="bold", va="center", zorder=3)
        top -= wh + 0.2

    rows, per = 3, 8
    rh = (top - 0.9 - WKH) / rows
    for r in range(rows):
        y0 = top - (r + 1) * rh
        ax.add_patch(FancyBboxPatch((0.3, y0 + 0.08), W - 0.6, rh - 0.16, boxstyle="round,pad=0,rounding_size=0.3",
                                    color="white", alpha=0.13, lw=0, zorder=1))
        idx = list(range(r * per, min(n, (r + 1) * per)))
        xs = [0.3 + (W - 0.6) * (j + 0.5) / per for j in range(len(idx))]
        for x, i in zip(xs, idx):
            ax.text(x, y0 + rh - 0.3, ref["time"][i], fontsize=11, color="white", ha="center", va="center")
            icon(ax, x, y0 + rh - 0.8, kinds[i], s=0.38, night=night[i])
            ax.text(x, y0 + 1.33, f"{tmean[i]:.0f}°", fontsize=15, color="white", ha="center", va="center", fontweight="bold")
            if tmax[i] - tmin[i] >= 3:
                ax.text(x + 0.27, y0 + 1.46, f"{tmin[i]:.0f}~{tmax[i]:.0f}", fontsize=6.5, color="#ffd28a", ha="left", va="center")
        tl = tmean[idx]
        cy = y0 + 0.9 + (tl - lo) / max(hi - lo, 1) * 0.2
        ax.plot(xs, cy, color="#ffe28a", lw=1.8, zorder=3)
        ax.scatter(xs, cy, color="white", s=16, zorder=4)
        for x, i in zip(xs, idx):
            wet = bool(wetflag[i])
            ax.text(x, y0 + 0.66, f"{pagree[i]:.0f}%", fontsize=10, color="#9fd6ff" if wet else "#dce6ef",
                    ha="center", va="center", fontweight="bold" if wet else "normal")
            if pmean[i] >= 0.1:
                ax.text(x, y0 + 0.43, f"{pmean[i]:.1f}mm", fontsize=7.5, color="#9fd6ff", ha="center", va="center")
            ax.text(x, y0 + 0.2, f"{gmax[i]:.0f}m/s", fontsize=7.5,
                    color="#ff8a80" if gmax[i] >= 14 else "#e6edf3", ha="center", va="center",
                    fontweight="bold" if gmax[i] >= 14 else "normal")


    if wk:
        wn = list(wk)
        wref = wk[wn[0]]
        warr = lambda key: np.array([[v if v is not None else np.nan for v in wk[m][key]] for m in wn], float)
        WX, WN, WP = np.nanmean(warr("tmax"), 0), np.nanmean(warr("tmin"), 0), warr("precip")
        wpm = np.nanmean(WP, 0)
        wagree = (np.nan_to_num(WP) >= 1.0).sum(0) / len(wn) * 100
        wag = wagree.copy()
        nd0 = len(wref["date"])
        WPOP = np.array([[v if v is not None else np.nan for v in (wk[m].get("pop") or [None] * nd0)] for m in wn], float)
        with np.errstate(all="ignore"):
            wpop = np.nanmean(WPOP, 0)
        wag = np.where(np.isnan(wpop), wag, wpop)
        wem = wk.get("ECMWF", wref)
        y1 = 0.9 + WKH - 0.1
        ax.add_patch(FancyBboxPatch((0.3, 1.0), W - 0.6, WKH - 0.2, boxstyle="round,pad=0,rounding_size=0.3",
                                    color="white", alpha=0.13, lw=0, zorder=1))
        ax.text(0.6, y1 - 0.35, "주간 예보 (7일)", fontsize=13, color="white", fontweight="bold", va="center")
        gl, gh = np.nanmin(WN), np.nanmax(WX)
        nd = len(wref["date"])
        rr = (WKH - 1.0) / nd
        for i in range(nd):
            yy = y1 - 0.85 - i * rr
            ax.text(0.6, yy, wref["date"][i], fontsize=12, color="white", va="center", fontweight="bold" if i == 0 else "normal")
            wet = wagree[i] >= 50 or wag[i] >= 50
            ax.text(2.35, yy, f"{wag[i]:.0f}%", fontsize=10.5, color="#9fd6ff" if wet else "#dce6ef", va="center", ha="right",
                    fontweight="bold" if wet else "normal")
            if wpm[i] >= 1:
                ax.text(2.45, yy, f"{wpm[i]:.0f}mm", fontsize=8, color="#9fd6ff", va="center")
            kd = kind(wem["code"][i], (WX[i] + WN[i]) / 2, wpm[i] if wet else 0)
            icon(ax, 3.55, yy + 0.05, kd, s=0.34)
            x0, x1 = 4.35, 6.05
            sc = lambda t: x0 + (t - gl) / max(gh - gl, 1) * (x1 - x0)
            ax.plot([x0, x1], [yy, yy], color="white", alpha=0.18, lw=5, solid_capstyle="round", zorder=2)
            ax.plot([sc(WN[i]), sc(WX[i])], [yy, yy], color="#ffd28a", lw=5, solid_capstyle="round", zorder=3)
            ax.text(x0 - 0.12, yy, f"{WN[i]:.0f}°", fontsize=11, color="#cfe3f5", va="center", ha="right")
            ax.text(x1 + 0.12, yy, f"{WX[i]:.0f}°", fontsize=11, color="white", va="center", fontweight="bold")
    ax.text(0.45, 0.62, f"기온 = {'·'.join(names)} 평균 (노란 숫자: 모델 간 범위, 차이 3℃↑)", fontsize=8.5, color="#e6edf3")
    ax.text(0.45, 0.38, "% = 모델 강수확률 평균(확률 없으면 비·눈 예측 모델 비율) · 아래줄 = 강수량 / 돌풍", fontsize=8.5, color="#e6edf3")
    ax.text(0.45, 0.14, "출처: Open-Meteo (ECMWF·GFS·ICON) · 기상청 자료 미사용", fontsize=8.5, color="#c9d6e2")
    out = f"{prefix}_{li + 1}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(out)
