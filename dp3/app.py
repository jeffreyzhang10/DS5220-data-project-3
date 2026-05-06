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

import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

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
    try:
        response = table.query(
            KeyConditionExpression=Key("city").eq(CITY),
            ScanIndexForward=True
        )
        return response.get("Items", [])
    except Exception as e:
        logger.error(f"DynamoDB query failed: {e}")
        return []


@app.route("/")
def index():

    logger.info("GET / called")

    try:
        response = {
            "about": (
                "Tracks Boston weather information via Open-Meteo. "
                "Includes information about current conditions, trends, and plots."
            ),
            "resources": ["current", "trend", "plot", "recent", "feels"]
        }

        logger.info(f"Returning API response: {response}")

        return response

    except Exception as e:
        logger.exception(f"Unexpected error in / route: {e}")

        return {
            "about": "Boston weather API temporarily unavailable.",
            "resources": []
        }


@app.route("/current")
def current():

    logger.info("GET /current called")

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

    logger.info("GET /trend called")

    items = get_items()

    if len(items) < 2:
        return {"response": "Not enough data yet to calculate a trend."}

    temps = [float(item["temperature_c"]) for item in items]
    first = temps[0]
    latest = temps[-1]
    avg = sum(temps) / len(temps)
    change = latest - first

    return {"response": f"Across {len(items)} samples, since April 29, 2026, the average temperature has been {avg:.2f}°C and changed by {change:.2f}°C."
    }

# use quickstart instead of matplotlib because it hangs 
@app.route("/plot")
def plot():

    logger.info("GET /plot called")

    items = get_items()

    logger.info(f"Retrieved {len(items)} weather records for plotting")

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

    logger.info("Sending chart request to QuickChart!")

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

    logger.info(f"Uploading plot to s3://{BUCKET_NAME}/{s3_key}")

    s3.put_object(
        Bucket = BUCKET_NAME,
        Key = s3_key,
        Body = response.content,
        ContentType = "image/png"
    )

    return {"response": f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"}

@app.route("/recent")
def latest_delta():

    logger.info("GET /recent called")

    try:
        items = get_items()

        logger.info(f"Retrieved {len(items)} weather records")

        if len(items) < 2:
            logger.warning("Not enough data to compute recent temperature change")
            return {"response": "Not enough data to compute change."}

        # last two readings
        prev = items[-2]
        curr = items[-1]

        prev_temp = float(prev["temperature_c"])
        curr_temp = float(curr["temperature_c"])

        change = curr_temp - prev_temp

        #logger.info(
         #   f"Previous temp: {prev_temp}°C | "
        #    f"Current temp: {curr_temp}°C | "
        #    f"Change: {change:.2f}°C"
        #)

        return {"response": f"Temperature has changed by {change:.2f}°C since the last sample."}

    except KeyError as e:
        logger.error(f"Missing expected field in DynamoDB item: {e}")
        return {"response": "Weather data is missing required fields."}

    except ValueError as e:
        logger.error(f"Temperature conversion failed: {e}")
        return {"response": "Failed to process temperature values."}

    except Exception as e:
        logger.exception(f"Unexpected error in /recent route: {e}")
        return {"response": "An unexpected error occurred while computing recent weather changes."}

@app.route("/feels")
def feels():

    logger.info("GET /feels called")

    try:
        items = get_items()

        logger.info(f"Retrieved {len(items)} weather records")

        if not items:
            logger.warning("No Boston weather data available yet")
            return {"response": "No Boston weather data collected yet."}

        latest = items[-1]

        temp = to_float(latest.get("temperature_c"))
        feels_like = latest.get("feels_like", None)

        logger.info(f"Raw temperature: {temp}")
        logger.info(f"Raw feels-like temperature: {feels_like}")

        if feels_like is None:
            logger.warning("Feels-like temperature missing from latest record")
            return {"response": "Feels-like temperature not available yet."}

        feels_like = to_float(feels_like)

        logger.info(
            f"Processed temperatures | "
            f"Actual: {temp}°C | Feels-like: {feels_like}°C"
        )

        return {
            "response": (
                f"It currently feels like {feels_like}°C in Boston, "
                f"even though it is actually {temp}°C."
            )
        }

    except KeyError as e:
        logger.error(f"Missing expected field in DynamoDB item: {e}")
        return {"response": "Weather data is missing required fields."}

    except ValueError as e:
        logger.error(f"Temperature conversion failed: {e}")
        return {"response": "Failed to process feels like temperature values."}

    except Exception as e:
        logger.exception(f"Unexpected error in /feels route: {e}")
        return {"response": "An unexpected error occurred while retrieving feelslike information."}