from chalice import Chalice
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

# import boto3
#import matplotlib
#matplotlib.use("Agg")
#import matplotlib.pyplot as plt
import json
import requests

from datetime import datetime
from boto3.dynamodb.conditions import Key

app = Chalice(app_name = "boston-weather-api")

TABLE_NAME = "dp3-table"
BUCKET_NAME = "bkf4cy-dp3-bucket"
CITY = "Boston"

dynamodb = boto3.resource("dynamodb", region_name = "us-east-1")
table = dynamodb.Table(TABLE_NAME)


def to_float(x):
    if isinstance(x, Decimal):
        return float(x)
    return x


def get_items():
    response = table.query(
        KeyConditionExpression=Key("city").eq(CITY),
        ScanIndexForward=True
    )
    return response.get("Items", [])


@app.route("/")
def index():
    return {
        "about": "Tracks Boston weather information via Open-Meteo. Includes information about current conditions, trends, and plots.",
        "resources": ["current", "trend", "plot", "recent", "feels"]}


@app.route("/current")
def current():
    items = get_items()

    if not items:
        return {"response": "No Boston weather data collected yet."}

    latest = items[-1]

    temp = to_float(latest.get("temperature_c"))
    humidity = to_float(latest.get("humidity"))
    wind = to_float(latest.get("wind_speed_10m"))
    weather = latest.get("weather_description", "Unknown")

    return {"response": f"Current Boston weather: {temp}°C, {weather}, a humidity of {humidity}%, and a wind speed of {wind} km/h."}


@app.route("/trend")
def trend():
    items = get_items()

    if len(items) < 2:
        return {"response": "Not enough data yet to calculate a trend."}

    temps = [float(item["temperature_c"]) for item in items]
    first = temps[0]
    latest = temps[-1]
    avg = sum(temps) / len(temps)
    change = latest - first

    return {
        "response": f"Across {len(items)} samples, since April 29, 2026, the average temperature has been {avg:.2f}°C and changed by {change:.2f}°C."
    }

# use quickstart instead of matplotlib because it hangs 
@app.route("/plot")
def plot():
    items = get_items()

    if len(items) < 2:
        return {"response": "Not enough data to generate a plot yet."}

    labels = [
        datetime.fromtimestamp(int(item["timestamp"])).strftime("%H:%M")
        for item in items
    ]

    temps = [float(item["temperature_c"]) for item in items]

    chart_config = {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Boston Temperature (C)",
                "data": temps,
                "fill": False
            }]
        },
        "options": {
            "title": {
                "display": True,
                "text": "Boston Temperature Over Time"
            }
        }
    }

    response = requests.get(
        "https://quickchart.io/chart",
        params={
            "c": json.dumps(chart_config),
            "format": "png",
            "width": 900,
            "height": 450,
            "backgroundColor": "white"
        }, timeout = 15
    )

    response.raise_for_status()

    s3_key = "weather/plots/latest.png"
    s3 = boto3.client("s3", region_name="us-east-1")

    s3.put_object(
        Bucket = BUCKET_NAME,
        Key = s3_key,
        Body = response.content,
        ContentType = "image/png"
    )

    return {"response": f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"}

@app.route("/recent")
def latest_delta():
    items = get_items()

    if len(items) < 2:
        return {"response": "Not enough data to compute change."}

    # last two readings
    prev = items[-2]
    curr = items[-1]

    prev_temp = float(prev["temperature_c"])
    curr_temp = float(curr["temperature_c"])

    change = curr_temp - prev_temp

    return {"response": f"Temperature has changed by {change:.2f}°C since the last sample."}

@app.route("/feels")
def feels():
    items = get_items()

    if not items:
        return {"response": "No Boston weather data collected yet."}

    latest = items[-1]

    temp = to_float(latest.get("temperature_c"))
    feels_like = latest.get("feels_like", None)

    if feels_like is None:
        return {"response": "Feels-like temperature not available yet."}

    feels_like = to_float(feels_like)

    return {"response": f"It currently feels like {feels_like}°C in Boston, even though it is actually {temp}°C."}