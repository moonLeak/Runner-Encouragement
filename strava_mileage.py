import os
import requests
import json
from datetime import datetime, timezone, timedelta

# =========================
# 环境变量（来自 GitHub Secrets 或本地）
# =========================

CLIENT_ID = os.environ["STRAVA_CLIENT_ID"]
CLIENT_SECRET = os.environ["STRAVA_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["STRAVA_REFRESH_TOKEN"]
VOLCANO_API_KEY = os.environ["VOLCANO_AI_API_KEY"]

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

token_data = token_response.json()

access_token = token_data["access_token"]

# =========================
# Step 2: 获取 activities
# =========================

activities_response = requests.get(
    "https://www.strava.com/api/v3/athlete/activities?per_page=200",
    headers={
        "Authorization": f"Bearer {access_token}"
    }
)

if activities_response.status_code != 200:
    raise Exception(f"Strava activities error: {activities_response.text}")

activities = activities_response.json()

# =========================
# Step 3: 计算跑量
# =========================

now = datetime.now(timezone.utc)

start_of_week = now - timedelta(days=now.weekday())
start_of_month = now.replace(day=1)
start_of_year = now.replace(month=1, day=1)

week_m = 0
month_m = 0
year_m = 0

for act in activities:

    if act.get("type") != "Run":
        continue

    date = datetime.fromisoformat(
        act["start_date"].replace("Z", "+00:00")
    )

    distance = act["distance"]

    if date >= start_of_week:
        week_m += distance

    if date >= start_of_month:
        month_m += distance

    if date >= start_of_year:
        year_m += distance

week_km = round(week_m / 1000, 2)
month_km = round(month_m / 1000, 2)
year_km = round(year_m / 1000, 2)

# =========================
# Step 4: 调用 Volcano AI (Doubao)
# =========================

prompt = f"""
这是跑者当前训练数据：

本周跑量: {week_km} km
本月跑量: {month_km} km
今年跑量: {year_km} km

请给出一句专业跑步建议：
要求：
- 中文
- 鼓励风格
- 20字以内
"""

ai_response = requests.post(
    "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
    headers={
        "Authorization": f"Bearer {VOLCANO_API_KEY}",
        "Content-Type": "application/json",
    },
    json={
        "model": "doubao-lite-4k",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 50,
    }
)

if ai_response.status_code != 200:
    raise Exception(f"Volcano AI error: {ai_response.text}")

ai_data = ai_response.json()

advice = ai_data["choices"][0]["message"]["content"].strip()

# =========================
# Step 5: 保存 JSON 文件（Widget 使用）
# =========================

output = {
    "week_km": week_km,
    "month_km": month_km,
    "year_km": year_km,
    "advice": advice,
    "last_update": datetime.now().strftime("%Y-%m-%d %H:%M")
}

with open("mileage.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

# =========================
# Step 6: 控制台输出（GitHub Actions 日志）
# =========================

print("\n===== Strava Running Stats =====\n")

print(f"Week:  {week_km} km")
print(f"Month: {month_km} km")
print(f"Year:  {year_km} km")

print("\nAI Advice:")
print(advice)

print("\nSaved to mileage.json\n")
