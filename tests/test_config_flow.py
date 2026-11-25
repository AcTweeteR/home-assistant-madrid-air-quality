from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.madrid_air_quality import config_flow
from custom_components.madrid_air_quality.const import CONF_KNOWN_METRICS, CONF_STATIONS


@pytest.mark.asyncio
async def test_options_form_opens_and_saves_selected_stations(monkeypatch):
    entry = SimpleNamespace(
        entry_id="madrid",
        data={CONF_STATIONS: ["28092005"], CONF_KNOWN_METRICS: {"28092005": ["8"]}},
    )
    entries = Mock()
    entries.async_get_known_entry.return_value = entry
    monkeypatch.setattr(config_flow, "async_get_clientsession", Mock())
    monkeypatch.setattr(
        config_flow,
        "_all_stations",
        AsyncMock(return_value={
            "28092005": SimpleNamespace(name="Móstoles"),
            "28007004": SimpleNamespace(name="Alcorcón"),
        }),
    )

    flow = config_flow.MadridAirQualityConfigFlow.async_get_options_flow(entry)
    flow.hass = SimpleNamespace(config_entries=entries)
    flow.handler = entry.entry_id
    flow.flow_id = "test"
    flow.context = {}

    form = await flow.async_step_init()
    assert form["type"] == FlowResultType.FORM
    assert form["data_schema"]({}) == {CONF_STATIONS: ["28092005"]}

    result = await flow.async_step_init({CONF_STATIONS: ["28092005", "28007004"]})
    assert result["type"] == FlowResultType.CREATE_ENTRY
    entries.async_update_entry.assert_called_once_with(
        entry,
        data={
            CONF_STATIONS: ["28092005", "28007004"],
            CONF_KNOWN_METRICS: {"28092005": ["8"]},
        },
    )
