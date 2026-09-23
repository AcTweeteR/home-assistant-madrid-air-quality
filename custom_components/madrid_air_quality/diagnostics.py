"""Diagnostics for support requests, without credentials or raw payloads."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    SOURCE_AIR,
    SOURCE_CATALOG,
    SOURCE_MUNICIPAL_AIR,
    SOURCE_MUNICIPAL_WEATHER,
    SOURCE_NAME,
    SOURCE_ONLINE_WEATHER,
    SOURCE_OPEN_METEO,
    SOURCE_WEATHER,
    VERSION,
)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    runtime = entry.runtime_data
    return {
        "integration_version": VERSION,
        "source": SOURCE_NAME,
        "catalog": SOURCE_CATALOG,
        "measurements": [
            SOURCE_AIR,
            SOURCE_ONLINE_WEATHER,
            SOURCE_WEATHER,
            SOURCE_MUNICIPAL_AIR,
            SOURCE_MUNICIPAL_WEATHER,
            SOURCE_OPEN_METEO,
        ],
        "selected_stations": list(entry.data.get("stations", [])),
        "official": {
            coordinator.name: {
                "snapshot": coordinator.data.as_diagnostic()
                if coordinator.data
                else None,
                "last_update_success": coordinator.last_update_success,
                "last_exception": str(coordinator.last_exception)
                if coordinator.last_exception
                else None,
            }
            for coordinator in runtime.official
        },
        "open_meteo": {
            "last_update_success": runtime.model.last_update_success
            if runtime.model
            else None,
            "last_exception": str(runtime.model.last_exception)
            if runtime.model and runtime.model.last_exception
            else None,
        },
        "domain": DOMAIN,
    }
