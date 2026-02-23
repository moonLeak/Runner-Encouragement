import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ["STRAVA_CLIENT_ID"]
CLIENT_SECRET = os.environ["STRAVA_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["STRAVA_REFRESH_TOKEN"]

# 获取 access_token
token_res = requests.post(
    "https://www.strava.com/oauth/token",
    data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    },
)
access_token = token_res.json()["access_token"]

# 获取最近 10 条记录
res = requests.get(
    "https://www.strava.com/api/v3/athlete/activities?per_page=10",
    headers={"Authorization": f"Bearer {access_token}"}
)
activities = res.json()

# 类型映射
TYPE_LABEL = {
    "Run": "🏃 跑步",
    "WeightTraining": "🏋️ 力量",
    "Ride": "🚴 骑行",
    "Swim": "🏊 游泳",
    "Walk": "🚶 步行",
    "Hike": "🥾 徒步",
    "Workout": "💪 训练",
}

HOME_TZ   = ZoneInfo(os.environ.get("HOME_TZ", "America/New_York"))
TRAVEL_TZ = ZoneInfo(os.environ.get("USER_TZ", str(HOME_TZ)))

print("\n─── 最近 10 次运动 ───────────────────────")
for i, act in enumerate(activities, 1):
    name = act.get("name", "未命名")
    act_type = act.get("type", "")
    label = TYPE_LABEL.get(act_type, f"• {act_type}")
    date = datetime.fromisoformat(act["start_date"].replace("Z", "+00:00")).astimezone(TRAVEL_TZ)
    date_str = date.strftime("%-m/%-d %H:%M")
    distance_m = act.get("distance", 0)
    duration_s = act.get("moving_time", 0)

    parts = [f"{label}", f"{date_str}"]

    if distance_m > 0:
        parts.append(f"{distance_m/1000:.2f} km")

    if duration_s > 0:
        h, rem = divmod(duration_s, 3600)
        m, s = divmod(rem, 60)
        if h > 0:
            parts.append(f"{h}h{m:02d}m")
        else:
            parts.append(f"{m}m{s:02d}s")

    print(f"  {i:2}.  {'  │  '.join(parts)}")
    print(f"        {name}")
    print()

print("──────────────────────────────────────────\n")
