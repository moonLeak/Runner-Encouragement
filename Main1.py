#!/usr/bin/env python3

import requests
from datetime import datetime, timezone, timedelta

# 你的 Strava API 信息
CLIENT_ID = "203245"
CLIENT_SECRET = "447b010e5c69c1031418e6ae7733fc1c45a80a12"
REFRESH_TOKEN = "bddb42b13afa3b75c0ed7193203c61d7df159e74"

# Step 1: 获取 access_token
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
new_refresh_token = token_data["refresh_token"]

# Step 2: 获取 activities
activities_response = requests.get(
	"https://www.strava.com/api/v3/athlete/activities?per_page=200",
	headers={
		"Authorization": f"Bearer {access_token}"
	}
)

activities = activities_response.json()

# Step 3: 计算时间范围
now = datetime.now(timezone.utc)

start_of_week = now - timedelta(days=now.weekday())
start_of_month = now.replace(day=1)
start_of_year = now.replace(month=1, day=1)

week_m = 0
month_m = 0
year_m = 0

# Step 4: 统计跑量
for act in activities:
	if act.get("type") != "Run":
		continue
	
	date = datetime.fromisoformat(
		act["start_date"].replace("Z", "+00:00")
	)
	
	dist = act["distance"]
	
	if date >= start_of_week:
		week_m += dist
		
	if date >= start_of_month:
		month_m += dist
		
	if date >= start_of_year:
		year_m += dist
		
# Step 5: 输出
print("\nStrava 跑量统计\n")

print(f"本周跑量: {week_m/1000:.2f} km")
print(f"本月跑量: {month_m/1000:.2f} km")
print(f"今年跑量: {year_m/1000:.2f} km")

print("\n完成\n")