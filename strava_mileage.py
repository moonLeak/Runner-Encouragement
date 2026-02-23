import os
import requests
import json
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

# =========================
# 环境变量（来自 GitHub Secrets 或本地 .env）
# =========================

CLIENT_ID = os.environ["STRAVA_CLIENT_ID"]
CLIENT_SECRET = os.environ["STRAVA_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["STRAVA_REFRESH_TOKEN"]
VOLCANO_API_KEY = os.environ["VOLCANO_AI_API_KEY"]

# =========================
# 时区配置
# HOME_TZ: 常驻统计口径（稳定周报）
# TRAVEL_TZ: 当前所在地（旅行时在 .env 或 GitHub Secrets 设置 USER_TZ）
# =========================

HOME_TZ = ZoneInfo(os.environ.get("HOME_TZ", "America/New_York"))
TRAVEL_TZ = ZoneInfo(os.environ.get("USER_TZ", str(HOME_TZ)))

# =========================
# Step 1: 获取 Strava access_token
# =========================

token_response = requests.post(
    "https://www.strava.com/oauth/token",
    data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    },
)

if token_response.status_code != 200:
    raise Exception(f"Strava token error: {token_response.text}")

access_token = token_response.json()["access_token"]

# =========================
# Step 2: 获取 Strava activities
# =========================

activities_response = requests.get(
    "https://www.strava.com/api/v3/athlete/activities?per_page=200",
    headers={"Authorization": f"Bearer {access_token}"}
)

if activities_response.status_code != 200:
    raise Exception(f"Strava activities error: {activities_response.text}")

activities = activities_response.json()

# =========================
# Step 3: 时间边界（周一 00:00 归零，各时区独立计算）
# =========================

now_utc = datetime.now(timezone.utc)
now_home = now_utc.astimezone(HOME_TZ)
now_travel = now_utc.astimezone(TRAVEL_TZ)

def week_start(now_local):
    monday = now_local - timedelta(days=now_local.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)

def month_start(now_local):
    return now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

sw_home   = week_start(now_home)
sm_home   = month_start(now_home)
sw_travel = week_start(now_travel)
sm_travel = month_start(now_travel)

# =========================
# Step 4: 统计数据
# =========================

# 近三个月分桶（用 HOME_TZ，趋势统计更稳定）
trend_months = []
for i in range(3):
    m = now_home.month - i
    y = now_home.year
    if m <= 0:
        m += 12
        y -= 1
    trend_months.append((y, m))

monthly_run      = {m: 0.0 for _, m in trend_months}
monthly_strength = {m: 0   for _, m in trend_months}

home_week_m   = home_month_m   = 0
travel_week_m = travel_month_m = 0
home_weekly_strength   = 0
travel_weekly_strength = 0

for act in activities:
    dt_utc   = datetime.fromisoformat(act["start_date"].replace("Z", "+00:00"))
    dt_home   = dt_utc.astimezone(HOME_TZ)
    dt_travel = dt_utc.astimezone(TRAVEL_TZ)
    act_type  = act.get("type", "")

    if act_type == "Run":
        dist = act["distance"]
        if dt_home   >= sw_home:   home_week_m   += dist
        if dt_home   >= sm_home:   home_month_m  += dist
        if dt_travel >= sw_travel: travel_week_m += dist
        if dt_travel >= sm_travel: travel_month_m += dist
        for y, m in trend_months:
            if dt_home.year == y and dt_home.month == m:
                monthly_run[m] += dist

    if act_type == "WeightTraining":
        if dt_home   >= sw_home:   home_weekly_strength   += 1
        if dt_travel >= sw_travel: travel_weekly_strength += 1
        for y, m in trend_months:
            if dt_home.year == y and dt_home.month == m:
                monthly_strength[m] += 1

stats_home = {
    "week_km":        round(home_week_m   / 1000, 2),
    "month_km":       round(home_month_m  / 1000, 2),
    "weekly_strength": home_weekly_strength,
}
stats_travel = {
    "week_km":        round(travel_week_m  / 1000, 2),
    "month_km":       round(travel_month_m / 1000, 2),
    "weekly_strength": travel_weekly_strength,
}

# 近三个月趋势（供 AI 使用）
trend_lines = []
for y, m in trend_months:
    run_km   = round(monthly_run[m] / 1000, 2)
    strength = monthly_strength[m]
    trend_lines.append(f"  {y}-{m:02d}: 跑步 {run_km} km，力量训练 {strength} 次")
trend_summary = "\n".join(trend_lines)

# =========================
# Step 5: 调用 Volcano AI（猫咪点评）
# =========================

prompt = f"""你是一个嘴很欠但很专业的督促人格（像多邻国那种抽象催人风格）。

【最近三个月数据】
{trend_summary}

只输出一句中文（不换行、不加引号），要求：
- 26字以内
- 语气：阴阳怪气/欠揍但专业；不粗口、不人身攻击
- 必须包含"如果X就Y"的触发器句式（X用日常场景，如：刷短视频/回宿舍坐下/晚饭后想躺）
- 必须包含一个量化处方（X分钟 或 X公里，二选一，偏低门槛）
- 必须暗示"断链压力"（用'最近三个月整体偏少/断断续续/有缺口'这类表述即可；不要编造具体天数）
- 只输出那一句话
"""

ai_response = requests.post(
    "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
    headers={
        "Authorization": f"Bearer {VOLCANO_API_KEY}",
        "Content-Type": "application/json",
    },
    json={
        "model": "doubao-seed-2-0-mini-260215",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
        "max_tokens": 60,
    }
)

if ai_response.status_code != 200:
    raise Exception(f"Volcano AI error: {ai_response.text}")

cat_says = ai_response.json()["choices"][0]["message"]["content"].strip()

# =========================
# Step 6: 保存 mileage.json（Widget 使用）
# =========================

last_update = now_travel.strftime("%-m-%-d %H:%M")

output = {
    "mode": "travel",
    "stats_home":   stats_home,
    "stats_travel": stats_travel,
    "cat": cat_says,
    "last_update": last_update,
}

with open("mileage.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

# =========================
# Step 7: 控制台输出（travel 模式）
# =========================

print(last_update)
print(f"week:     {stats_travel['week_km']} km")
print(f"month:    {stats_travel['month_km']} km")
print(f"strength: {stats_travel['weekly_strength']}")
print(f'猫："{cat_says}"')

# =========================
# 暂未启用：Garmin 健康数据
# =========================

# GARMIN_EMAIL = os.environ.get("GARMIN_EMAIL")
# GARMIN_PASSWORD = os.environ.get("GARMIN_PASSWORD")
#
# if GARMIN_EMAIL and GARMIN_PASSWORD:
#     try:
#         from garminconnect import Garmin
#         garmin = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
#         garmin.login()
#         today = datetime.now().strftime("%Y-%m-%d")
#         hr_data = garmin.get_heart_rates(today)
#         resting_hr = hr_data.get("restingHeartRate")
#         ts = garmin.get_training_status(today)
#         atl = ts.get("acuteTrainingLoad") if ts else None
#         ctl = ts.get("chronicTrainingLoad") if ts else None
#         tr = garmin.get_training_readiness(today)
#         training_readiness = tr[0].get("score") if tr else None
#     except Exception as e:
#         print(f"[Garmin] 数据获取失败，跳过: {e}")
