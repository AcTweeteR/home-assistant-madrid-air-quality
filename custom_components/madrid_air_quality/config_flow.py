"""Config and options flows."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MadridAirQualityApi, MadridAirQualityApiError
from .const import CONF_KNOWN_METRICS, CONF_STATIONS, DOMAIN
from .parser import parse_catalog


def _station_selector(stations: dict[str, Any]) -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[{"value": code, "label": f"{station.name} ({code})"} for code, station in sorted(stations.items())],
            multiple=True,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


class MadridAirQualityConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _catalog(self) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)
        return parse_catalog(await MadridAirQualityApi(session).catalog())

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        errors: dict[str, str] = {}
        try:
            stations = await self._catalog()
        except (MadridAirQualityApiError, ValueError):
            return self.async_abort(reason="cannot_connect")
        if user_input is not None:
            selected = list(dict.fromkeys(user_input[CONF_STATIONS]))
            if not selected:
                errors[CONF_STATIONS] = "no_station"
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Madrid Air Quality & Weather", data={CONF_STATIONS: selected})
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_STATIONS): _station_selector(stations)}),
            errors=errors,
        )

    @staticmethod
    async def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return MadridAirQualityOptionsFlow(config_entry)


class MadridAirQualityOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        errors: dict[str, str] = {}
        session = async_get_clientsession(self.hass)
        try:
            stations = parse_catalog(await MadridAirQualityApi(session).catalog())
        except (MadridAirQualityApiError, ValueError):
            return self.async_abort(reason="cannot_connect")
        if user_input is not None:
            selected = list(dict.fromkeys(user_input[CONF_STATIONS]))
            if not selected:
                errors[CONF_STATIONS] = "no_station"
            else:
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        CONF_STATIONS: selected,
                        CONF_KNOWN_METRICS: self.config_entry.data.get(CONF_KNOWN_METRICS, {}),
                    },
                )
                return self.async_create_entry(title="", data={})
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Required(CONF_STATIONS, default=self.config_entry.data[CONF_STATIONS]): _station_selector(stations)}),
            errors=errors,
        )
