import json
import os
import time
import logging
from decimal import Decimal
from datetime import datetime, timezone

import boto3
import requests


logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

def weather_code(code):
    mapping = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Rain showers",
        95: "Thunderstorm"
    }
    return mapping.get(code, "Unknown")


def lambda_handler(event, context):
    table_name = os.environ.get("DYNAMO_TABLE", "dp3-table")
    bucket_name = os.environ.get("S3_BUCKET", "bkf4cy-dp3-bucket")

    city = os.environ.get("CITY", "Boston")
    lat = os.environ.get("LAT", "42.3601")
    lon = os.environ.get("LON", "-71.0589")

    table = dynamodb.Table(table_name)

    timestamp = int(time.time())
    run_id = str(int(time.time()))

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weathercode,apparent_temperature"
    )

    logger.info(f"Starting weather ingest for {city}")
    logger.info(f"Fetching Open-Meteo URL: {url}")

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.error(f"Failed to fetch Open-Meteo data: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"status": "failed", "error": str(e)})
        }

    current = data.get("current", {})
    weather_text = weather_code(current.get("weathercode", -1))

    if not current:
        logger.warning("No current weather data returned")
        return {
            "statusCode": 200,
            "body": json.dumps({"status": "skipped", "reason": "no current data"})
        }

    item = {
        "city": city,
        "timestamp": timestamp,
        "datetime_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "temperature_c": Decimal(str(current.get("temperature_2m", 0))),
        "humidity": Decimal(str(current.get("relative_humidity_2m", 0))),
        "precipitation": Decimal(str(current.get("precipitation", 0))),
        "wind_speed_10m": Decimal(str(current.get("wind_speed_10m", 0))),
        "source": "open-meteo", 
        "weather_description": weather_text,
        "feels_like": Decimal(str(current.get("apparent_temperature", 0)))
        }

    logger.info(f"Writing item to DynamoDB table {table_name}")
    table.put_item(Item=item)

    s3_key = f"weather/raw/{city.lower()}-{run_id}.json"

    s3_body = json.dumps(
        {
            "city": city,
            "timestamp": timestamp,
            "source": "open-meteo",
            "raw_response": data
        },
        default=str,
        indent=2
    )

    logger.info(f"Writing raw data to s3://{bucket_name}/{s3_key}")
    s3.put_object(
        Bucket=bucket_name,
        Key=s3_key,
        Body=s3_body,
        ContentType="application/json"
    )

    logger.info("Weather ingest completed successfully")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "success",
            "city": city,
            "timestamp": timestamp,
            "s3_key": s3_key
        })
    }