"""Tool registry and individual tool behaviour."""

import json

import httpx
import pytest

from app.services.tools import build_registry
from app.services.tools.base import Tool
from app.services.tools.notes import MAX_NOTE_LENGTH
from app.services.tools.weather import GetWeatherTool

from .conftest import TELEGRAM_ID


def test_schemas_are_valid_openai_tool_definitions(registry):
    schemas = registry.schemas()

    assert {schema["function"]["name"] for schema in schemas} == {
        "get_weather",
        "save_note",
        "search_notes",
    }
    for schema in schemas:
        assert schema["type"] == "function"
        assert schema["function"]["description"]
        assert schema["function"]["parameters"]["type"] == "object"


async def test_save_and_search_round_trip(registry, tool_context, repositories):
    saved = await registry.dispatch(
        "save_note", json.dumps({"text": "Landlord is Ana", "tags": ["Home"]}), tool_context
    )
    found = await registry.dispatch("search_notes", json.dumps({"query": "landlord"}), tool_context)

    assert "Saved" in saved
    assert "home" in saved  # tags are normalised to lowercase
    assert "Landlord is Ana" in found
    assert len(await repositories.notes.search(TELEGRAM_ID, "")) == 1


async def test_search_reports_no_matches(registry, tool_context):
    assert (
        await registry.dispatch("search_notes", json.dumps({"query": "ghost"}), tool_context)
        == "No matching notes."
    )


async def test_save_note_rejects_empty_and_oversized_text(registry, tool_context):
    empty = await registry.dispatch("save_note", json.dumps({"text": "  "}), tool_context)
    huge = await registry.dispatch(
        "save_note", json.dumps({"text": "x" * (MAX_NOTE_LENGTH + 1)}), tool_context
    )

    assert empty.startswith("Error")
    assert huge.startswith("Error")


async def test_unknown_tool_is_reported_not_raised(registry, tool_context):
    result = await registry.dispatch("delete_production_db", "{}", tool_context)

    assert result.startswith("Error: unknown tool")
    assert "save_note" in result  # the model is told what it may call instead


async def test_malformed_arguments_are_reported_not_raised(registry, tool_context):
    result = await registry.dispatch("save_note", "{not json", tool_context)

    assert result.startswith("Error")
    assert "JSON" in result


async def test_hallucinated_extra_argument_is_tolerated(registry, tool_context):
    """Models invent parameters; a **kwargs signature absorbs them."""
    result = await registry.dispatch(
        "save_note", json.dumps({"text": "hi", "priority": 9}), tool_context
    )

    assert result.startswith("Saved")


async def test_bad_signature_is_reported_not_raised(registry, tool_context):
    class StrictTool(Tool):
        name = "strict"
        description = "Accepts exactly one argument."
        parameters = {"type": "object", "properties": {"value": {"type": "string"}}}

        async def run(self, ctx, value: str) -> str:  # no **kwargs on purpose
            return value

    registry._tools["strict"] = StrictTool()

    result = await registry.dispatch("strict", json.dumps({"nope": 1}), tool_context)

    assert result.startswith("Error: wrong arguments")


async def test_non_object_arguments_are_rejected(registry, tool_context):
    result = await registry.dispatch("save_note", json.dumps(["text"]), tool_context)

    assert result.startswith("Error")
    assert "JSON object" in result


async def test_tool_exception_is_swallowed_into_a_message(tool_context):
    class Boom(GetWeatherTool):
        async def _get_json(self, url, params):
            raise RuntimeError("upstream down")

    registry = build_registry()
    registry._tools["get_weather"] = Boom()

    result = await registry.dispatch("get_weather", json.dumps({"city": "Lisbon"}), tool_context)

    assert result.startswith("Error: get_weather failed")
    assert "upstream down" in result


@pytest.fixture
def weather_tool():
    """A weather tool whose HTTP client is a local transport — no network."""

    def handler(request: httpx.Request) -> httpx.Response:
        if "geocoding" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "name": "Lisbon",
                            "country": "Portugal",
                            "latitude": 38.7,
                            "longitude": -9.1,
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "current": {
                    "temperature_2m": 21.4,
                    "apparent_temperature": 20.9,
                    "wind_speed_10m": 12.0,
                    "weather_code": 2,
                }
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return GetWeatherTool(client)


async def test_weather_formats_a_human_answer(weather_tool, tool_context):
    result = await weather_tool.run(tool_context, city="Lisbon")

    assert "Lisbon, Portugal" in result
    assert "21.4°C" in result
    assert "partly cloudy" in result


async def test_weather_handles_unknown_city(tool_context):
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"results": []}))
    )

    result = await GetWeatherTool(client).run(tool_context, city="Atlantis")

    assert "No city named" in result
