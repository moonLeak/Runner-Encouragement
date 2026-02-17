import os
import requests
from datetime import datetime, timezone, timedelta

CLIENT_ID = os.environ["STRAVA_CLIENT_ID"]
CLIENT_SECRET = os.environ["STRAVA_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["STRAVA_REFRESH_TOKEN"]

token_response = requests.post(
    "https://www.strava.com/oauth/token",
    data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    },
)
token_data = token_response.json()
access_token = token_data["access_token"]

activities = requests.get(
    "https://www.strava.com/api/v3/athlete/activities?per_page=200",
    headers={"Authorization": f"Bearer {access_token}"},
).json()

now = datetime.now(timezone.utc)
start_of_week = now - timedelta(days=now.weekday())
start_of_month = now.replace(day=1)

week_m = 0
month_m = 0

for act in activities:
    if act.get("type") != "Run":
        continue
    date = datetime.fromisoformat(act["start_date"].replace("Z", "+00:00"))
    dist = act["distance"]
    if date >= start_of_week:
        week_m += dist
    if date >= start_of_month:
        month_m += dist

print(f"本周跑量: {week_m/1000:.2f} km")
print(f"本月跑量: {month_m/1000:.2f} km")
