# DS5220-data-project-3

## Title DS5220 Project 3 Boston Weather Tracker - Full Pipeline

### Overview 

Data Source: Open Mateo Weather API
Data Source Reasoning: As I am working on this project, I am also preparing to move out of my apartment in Charlottesville for potentially the last time. Perhaps the thing I might miss most is the weather, and in particular, how early it warms up in the spring. Although it is rather cold, comparatively speaking, as of the week of April 28th, 2026, it is and is much colder back home up in Boston, MA. For example, it is probably 10 degrees F warmer on average here. Among other reasons, I used Open Mateo's API due to familiarity with the data and the lack of an API key needed to pull data accordingly. 

## Data Ingestion 

The ingestion pipeline is a lambda function, triggered to run once an hour as a schedeuled event in AWS. 

## Storage Schema

Each record is stored as a JSON object with the following structure:

```json
{
  "city": "string",
  "timestamp": "number (unix timestamp)",
  "datetime_utc": "string (ISO 8601 format)",
  "run_id": "string",
  "temperature_c": "number (°C)",
  "humidity": "number (%)",
  "precipitation": "number (mm)",
  "wind_speed_10m": "number (km/h)",
  "source": "string",
  "weather_description": "string",
  "feels_like": "number (°C)"
}
```

## API Resources

The API is built using AWS Chalice and uses the following resources:

### `/`
- **Method:** GET
- **Description:** API landing page and summary of available resources.  
- **Returns:** A short description of the project and a list of available resources/endpoints for exploration: `current`, `trend`, `plot`, `recent`, and `feels`.

### `/current`
- **Method:** GET
- **Description:** Returns the most recent Boston weather conditions.
- **Returns:** A JSON response with the current temperature, weather description, humidity, and wind speed.

### `/trend`
- **Method:** GET
- **Description:** Summarizes trends in temperature across all datapoints.
- **Returns:** A JSON response with the number of samples, average temperature, and total temperature change since April 29, 2026.

### `/plot`
- **Method:** GET
- **Description:** Generates a PNG plot using the collected Boston weather data displaying temperature over time.
- **Returns:** A JSON response containing an updated public S3 URL to the latest generated PNG plot.

### `/recent`
- **Method:** GET
- **Description:** Compares the two most recent weather readings, showing how much the temperature has changed recently.
- **Returns:** A JSON response showing how much the temperature changed since the previous sample.

### `/feels`
- **Method:** GET
- **Description:** Compares the most recent real feel temperature for Boston, relative to the actual temperature recorded.
- **Returns:** A JSON response comparing the feels-like temperature to the actual temperature.

## Stretch Goals 

More Resources Added. Includes additional API resources for `/recent` and `/feels`