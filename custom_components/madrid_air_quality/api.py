"""HTTP client for the official CKAN JSON resources."""

from __future__ import annotations

import asyncio
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import AIR_URL, CATALOG_URL, WEATHER_URL


class MadridAirQualityApiError(Exception):
    """Raised when an official resource cannot be read or decoded."""


class MadridAirQualityApi:
    def __init__(self, session: ClientSession) -> None:
        self._session = session
        self._timeout = ClientTimeout(total=45)

    async def _get_json(self, url: str) -> Any:
        try:
            async with self._session.get(
                url,
                timeout=self._timeout,
                headers={"User-Agent": "home-assistant-madrid-air-quality/1.0.1"},
            ) as response:
                response.raise_for_status()
                return await response.json(content_type=None)
        except (ClientError, asyncio.TimeoutError, ValueError) as err:
            raise MadridAirQualityApiError(f"No se pudo leer {url}: {err}") from err

    async def catalog(self) -> Any:
        return await self._get_json(CATALOG_URL)

    async def measurements(self) -> list[Any]:
        # Two requests per coordinated refresh, never one request per entity.
        return await asyncio.gather(self._get_json(AIR_URL), self._get_json(WEATHER_URL))
