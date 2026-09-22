from pathlib import Path
from typing import ClassVar

import pytest

from custom_components.madrid_air_quality.api import MadridAirQualityApi

FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    headers: ClassVar = {"Date": "Tue, 22 Sep 2026 04:33:00 GMT"}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    def raise_for_status(self):
        return None

    async def text(self):
        return (FIXTURES / "online_mostoles.html").read_text()


class FakeSession:
    def __init__(self):
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        return FakeResponse()


@pytest.mark.asyncio
async def test_online_weather_uses_one_shared_request_per_station():
    session = FakeSession()
    api = MadridAirQualityApi(session)

    metrics = await api.online_weather("28092005")

    assert len(session.urls) == 1
    assert session.urls[0].endswith("idEstacion=6")
    assert metrics["83"].value == 19.4
    assert metrics["83"].data_source is not None
