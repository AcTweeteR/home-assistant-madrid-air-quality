"""Madrid Air Quality & Weather integration."""

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import UpdateFailed

from .api import MadridAirQualityApi
from .const import CONF_STATIONS, PLATFORMS
from .coordinator import MadridAirQualityCoordinator, MunicipalCoordinator
from .derived import OpenMeteoCoordinator, SolarCoordinator
from .models import Station


@dataclass
class EntryRuntime:
    official: list[MadridAirQualityCoordinator | MunicipalCoordinator]
    model: OpenMeteoCoordinator | None
    solar: SolarCoordinator | None
    stations: dict[str, Station]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = MadridAirQualityApi(async_get_clientsession(hass))
    selected = {str(code) for code in entry.data[CONF_STATIONS]}
    official: list[MadridAirQualityCoordinator | MunicipalCoordinator] = []
    if any(not code.startswith("28079") for code in selected):
        regional = MadridAirQualityCoordinator(hass, entry, api)
        regional.station_codes &= {
            code for code in selected if not code.startswith("28079")
        }
        official.append(regional)
    if any(code.startswith("28079") for code in selected):
        official.append(MunicipalCoordinator(hass, entry, api))
    stations: dict[str, Station] = {}
    for coordinator in official:
        try:
            await coordinator.async_load_catalog()
            stations.update(
                {
                    code: station
                    for code, station in coordinator.catalog.items()
                    if code in selected
                }
            )
        except UpdateFailed:  # A second official network may still be available.
            continue
    if not stations:
        raise ConfigEntryNotReady("No hay catálogos oficiales disponibles")
    for coordinator in official:
        await coordinator.async_refresh()
    station_list = [stations[code] for code in sorted(stations)]
    model = OpenMeteoCoordinator(hass, api, station_list)
    solar = SolarCoordinator(hass, station_list)
    await model.async_refresh()  # A model outage must not block official feeds.
    await solar.async_refresh()
    entry.runtime_data = EntryRuntime(official, model, solar, stations)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
