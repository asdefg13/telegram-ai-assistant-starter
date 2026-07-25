"""Weather lookup via Open-Meteo (no API key required)."""

from typing import Any

import httpx

from app.services.tools.base import Tool, ToolContext

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = httpx.Timeout(10.0)

# https://open-meteo.com/en/docs — WMO weather interpretation codes
WEATHER_CODES: dict[int, str] = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "slight snow",
    73: "moderate snow",
    75: "heavy snow",
    80: "rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
}


class GetWeatherTool(Tool):
    """Current conditions for a city, resolved by name."""

    name = "get_weather"
    description = (
        "Get the current weather for a city. Use it whenever the user asks about "
        "weather, temperature or whether they need an umbrella."
    )
    parameters = {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "City name, e.g. 'Lisbon' or 'Buenos Aires'.",
            },
            "units": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "Temperature units. Defaults to celsius.",
            },
        },
        "required": ["city"],
        "additionalProperties": False,
    }

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        # Injectable so tests never touch the network and production reuses one pool.
        self._client = client

    async def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        if self._client is not None:
            response = await self._client.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def run(self, ctx: ToolContext, **kwargs: Any) -> str:
        city = str(kwargs.get("city", "")).strip()
        units = kwargs.get("units", "celsius")
        if not city:
            return "Error: 'city' is required."

        geo = await self._get_json(
            GEOCODING_URL, {"name": city, "count": 1, "language": "en", "format": "json"}
        )
        results = geo.get("results") or []
        if not results:
            return f"No city named {city!r} was found."

        place = results[0]
        forecast = await self._get_json(
            FORECAST_URL,
            {
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,apparent_temperature,wind_speed_10m,weather_code",
                "temperature_unit": units,
            },
        )
        current = forecast.get("current") or {}
        condition = WEATHER_CODES.get(int(current.get("weather_code", -1)), "unknown conditions")
        degrees = "°C" if units == "celsius" else "°F"
        location = ", ".join(filter(None, [place.get("name"), place.get("country")]))

        return (
            f"{location}: {current.get('temperature_2m')}{degrees} ({condition}), "
            f"feels like {current.get('apparent_temperature')}{degrees}, "
            f"wind {current.get('wind_speed_10m')} km/h."
        )
