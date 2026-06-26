import pytest
from unittest.mock import MagicMock

from pydantic_ai import RunContext

from app.agent.agent import search_accommodations
from app.agent.dependency import AgentDependencies
from app.adapters.mcp_accommodation_service import MCPAccommodationServiceAdapter
from app.domain import AccommodationOption, UserPreferences
from app.ports.accommodation_service import AccommodationServicePort
from app.ports.prompt_service import PromptServicePort
from app.mcp_servers import accommodations_server


# --- No API key → degrade to search_web (no fabricated data) -------------------

def test_search_accommodations_unavailable_without_api_key(monkeypatch):
    monkeypatch.setattr(accommodations_server, "_api_key", lambda: None)
    result = accommodations_server.search_accommodations(
        "Santorini", "2026-09-10", "2026-09-14", currency="EUR"
    )
    assert result["options"] == []
    assert result["estimated"] is False
    assert result["available"] is False
    assert result["currency"] == "EUR"


def test_search_accommodations_rejects_bad_dates(monkeypatch):
    monkeypatch.setattr(accommodations_server, "_api_key", lambda: "test-key")
    # check-out before check-in → unavailable, no SerpApi call attempted.
    result = accommodations_server.search_accommodations(
        "Santorini", "2026-09-14", "2026-09-10", currency="GBP"
    )
    assert result["available"] is False
    assert result["currency"] == "GBP"


# --- SerpApi parsing (mocked HTTP) --------------------------------------------

_SERPAPI_HOTELS_FIXTURE = {
    "properties": [
        {
            "type": "hotel",
            "name": "Katikies Santorini",
            "gps_coordinates": {"latitude": 36.46, "longitude": 25.37},
            "rate_per_night": {"lowest": "$900", "extracted_lowest": 900},
            "total_rate": {"lowest": "$3,600", "extracted_lowest": 3600},
            "overall_rating": 4.8,
            "reviews": 1200,
            "extracted_hotel_class": 5,
            "amenities": ["Pool", "Free Wi-Fi", "Spa", "Breakfast", "Bar", "Gym", "Beach access"],
            "link": "https://example.com/katikies",
        },
        {
            "type": "vacation rental",
            "name": "Oia Sunset Studio",
            # Only nightly present → total must be derived from nights.
            "rate_per_night": {"lowest": "$150", "extracted_lowest": 150},
            "overall_rating": 4.4,
            "reviews": 80,
        },
        {
            # No price at all → dropped.
            "type": "hotel",
            "name": "No Price Inn",
            "overall_rating": 4.0,
        },
    ]
}


def test_search_accommodations_parses_serpapi(monkeypatch):
    monkeypatch.setattr(accommodations_server, "_api_key", lambda: "test-key")
    captured = {}

    def fake_search(params):
        captured["params"] = params
        return _SERPAPI_HOTELS_FIXTURE

    monkeypatch.setattr(accommodations_server, "_serpapi_search", fake_search)
    result = accommodations_server.search_accommodations(
        "Santorini", "2026-09-10", "2026-09-14", guests=2, min_rating=4.5, currency="EUR"
    )

    assert result["available"] is True
    assert result["estimated"] is False
    # Request mapping: q, dates, adults, currency, lowest-price sort, rating enum.
    assert captured["params"]["q"] == "Santorini"
    assert captured["params"]["adults"] == 2
    assert captured["params"]["currency"] == "EUR"
    assert captured["params"]["sort_by"] == 3
    assert captured["params"]["rating"] == 9  # min_rating 4.5 -> enum 9

    opts = result["options"]
    # Priced properties only (No Price Inn dropped), cheapest nightly first.
    assert [o["name"] for o in opts] == ["Oia Sunset Studio", "Katikies Santorini"]
    cheap = AccommodationOption(**opts[0])
    # 4 nights * 150 = 600 derived total.
    assert cheap.rate_per_night == 150.0
    assert cheap.total_rate == 600.0
    lux = AccommodationOption(**opts[1])
    assert lux.hotel_class == 5
    assert lux.rating == 4.8
    assert len(lux.amenities) == 6  # capped
    assert lux.latitude == 36.46


def test_map_rating_buckets():
    assert accommodations_server._map_rating(None) is None
    assert accommodations_server._map_rating(3.0) is None
    assert accommodations_server._map_rating(3.5) == 7
    assert accommodations_server._map_rating(4.0) == 8
    assert accommodations_server._map_rating(4.7) == 9


# --- Mock mode (MCP_MODE=mock → no network, flagged estimated) -----------------

def test_search_accommodations_mock_mode_no_network(monkeypatch):
    monkeypatch.setenv("MCP_MODE", "mock")

    def boom(_params):
        raise AssertionError("SerpApi must not be called in mock mode")

    monkeypatch.setattr(accommodations_server, "_serpapi_search", boom)
    # No API key needed in mock mode.
    monkeypatch.setattr(accommodations_server, "_api_key", lambda: None)

    result = accommodations_server.search_accommodations(
        "Santorini", "2026-09-10", "2026-09-14", guests=2, max_price=200, currency="EUR"
    )
    assert result["available"] is True
    assert result["estimated"] is True  # mock data is flagged as approximate
    assert len(result["options"]) >= 1
    # max_price cap is honored against the mock catalog.
    assert all(o["rate_per_night"] <= 200 for o in result["options"])
    opt = AccommodationOption(**result["options"][0])
    assert opt.estimated is True
    # 4 nights → total is nightly * nights.
    assert opt.total_rate == round(opt.rate_per_night * 4, 2)


# --- Adapter parsing (no subprocess) ------------------------------------------

class _FakeResult:
    isError = False

    def __init__(self, structured):
        self.structuredContent = structured
        self.content = []


@pytest.mark.asyncio
async def test_adapter_parses_accommodations_into_domain():
    adapter = MCPAccommodationServiceAdapter()
    captured = {}

    async def fake_call_tool(name, arguments):
        captured["name"] = name
        captured["arguments"] = arguments
        return _FakeResult(
            {
                "currency": "EUR",
                "estimated": False,
                "options": [
                    {
                        "name": "Katikies Santorini",
                        "property_type": "hotel",
                        "rate_per_night": 900.0,
                        "total_rate": 3600.0,
                        "currency": "EUR",
                        "rating": 4.8,
                        "reviews": 1200,
                        "hotel_class": 5,
                        "amenities": ["Pool", "Spa"],
                        "link": "https://example.com/katikies",
                        "latitude": 36.46,
                        "longitude": 25.37,
                        "estimated": False,
                    }
                ],
            }
        )

    adapter.session = MagicMock()
    adapter.session.call_tool = fake_call_tool

    options = await adapter.search_accommodations(
        "Santorini",
        check_in_date="2026-09-10",
        check_out_date="2026-09-14",
        guests=2,
        min_rating=4.5,
        currency="EUR",
    )
    assert captured["name"] == "search_accommodations"
    assert captured["arguments"]["min_rating"] == 4.5
    assert captured["arguments"]["currency"] == "EUR"
    assert len(options) == 1
    assert isinstance(options[0], AccommodationOption)
    assert options[0].name == "Katikies Santorini"
    assert options[0].total_rate == 3600.0


# --- Agent tool ---------------------------------------------------------------

class _StubAccommodationService(AccommodationServicePort):
    def __init__(self):
        self.calls = []

    async def search_accommodations(self, destination, **kwargs):
        self.calls.append(("search_accommodations", destination, kwargs))
        return [
            AccommodationOption(
                name="TestStay",
                property_type="hotel",
                rate_per_night=120.0,
                total_rate=480.0,
                currency=kwargs.get("currency", "EUR"),
                rating=4.5,
            )
        ]


def _ctx(deps):
    return RunContext(deps=deps, model=MagicMock(), usage=MagicMock(), prompt="test")


@pytest.mark.asyncio
async def test_search_accommodations_tool_uses_pref_currency():
    stub = _StubAccommodationService()
    deps = AgentDependencies(
        prompt_service=MagicMock(spec=PromptServicePort),
        user_preferences=UserPreferences(currency="USD"),
        accommodation_service=stub,
    )
    out = await search_accommodations(
        _ctx(deps), "Santorini", "2026-09-10", "2026-09-14", guests=2, min_rating=4.0
    )
    assert out["currency"] == "USD"
    assert len(out["options"]) == 1
    assert out["options"][0]["total_rate"] == 480.0
    _, _, kwargs = stub.calls[0]
    assert kwargs["check_in_date"] == "2026-09-10"
    assert kwargs["check_out_date"] == "2026-09-14"
    assert kwargs["currency"] == "USD"
    assert kwargs["min_rating"] == 4.0


@pytest.mark.asyncio
async def test_search_accommodations_tool_handles_missing_service():
    deps = AgentDependencies(
        prompt_service=MagicMock(spec=PromptServicePort), accommodation_service=None
    )
    out = await search_accommodations(_ctx(deps), "Santorini", "2026-09-10", "2026-09-14")
    assert out["options"] == []
    assert "error" in out
