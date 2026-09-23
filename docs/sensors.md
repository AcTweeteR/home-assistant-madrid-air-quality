# Entities and sensors

Each selected station becomes a Home Assistant device. Physical sensor identity is based on the official station code plus official magnitude code. The 28 Comunidad de Madrid IDs are unchanged; Madrid-city stations use their distinct official `28079...` codes and names such as `Madrid — Casa de Campo`.

## Dynamic discovery

Stations can publish different sets of measurements. The integration discovers the magnitudes present for each selected station instead of assuming every station has the same hardware.

Previously discovered magnitude codes are persisted so a temporarily absent reading does not delete the entity. Newly observed codes can create new entities while Home Assistant is running.

## Known meteorological magnitudes

| Measurement | Code | Display abbreviation | Unit |
| --- | ---: | --- | --- |
| Wind speed | 81 | VV | m/s |
| Wind direction | 82 | DV | ° |
| Temperature | 83 | TMP | °C |
| Relative humidity | 86 | HR | % |
| Atmospheric pressure | 87 | PRE | mbar |
| Solar radiation | 88 | RS | W/m² |
| Precipitation | 89 | LL | l/m² |

## Known air-quality magnitudes

The integration currently recognises official codes for SO₂, CO, NO, NO₂, PM2.5, PM10, PM1, NOx, O₃, toluene, Black Carbon, benzene, ethylbenzene, total hydrocarbons, non-methane hydrocarbons and MetaParaXylene.

The exact entities depend on what the selected station publishes.

Madrid-city air values are published in one network-wide JSON file. Their meteorological network is separate: seven parameters are attached to an air device **only if the official station code and exact catalogue coordinates coincide**. A catalogue entry without current readings does not generate invented physical values.

## Location-based entities

Each selected station with coordinates has four additional entities on the **same device**:

| Name | Class / unit | Source and meaning |
| --- | --- | --- |
| Apparent temperature / Sensación térmica | Temperature, measurement, °C | Open-Meteo modelled `current.apparent_temperature`; not a thermometer reading. |
| Sky condition / Estado del cielo | Enum of Home Assistant weather conditions | Open-Meteo WMO `current.weather_code`; `is_day` distinguishes `sunny` and `clear-night`. Unknown codes remain unknown. |
| Sunrise / Amanecer | Timestamp | Next astronomical sunrise at station coordinates, calculated locally with Astral. |
| Sunset / Atardecer | Timestamp | Next astronomical sunset, calculated locally. |

Open-Meteo estimates for a nearby model grid cell, even when exact station coordinates are sent. The hourly/current timestamp belongs to the model result; the time Home Assistant fetched it is not substituted. The raw WMO code is exposed as `wmo_weather_code`, and `data_source` distinguishes modelled, official and locally calculated values. The WMO subset does not encode every Home Assistant condition: `snowy-rainy` and standalone `hail`, for example, are not invented from a code describing a different phenomenon. Thunderstorm with hail retains its raw WMO code while displaying the closest generic lightning condition.

HomeKit Bridge may export a temperature-class apparent-temperature sensor as another temperature, so keep its clear name. Enum sky conditions and timestamp sensors have no native equivalent in the current Home Assistant HomeKit Bridge sensor mapping; the integration does not change their classes to force export. Apple Home presentation depends on the bridge and iOS version.

## Unknown future codes

Unknown codes are retained and exposed rather than silently discarded. The integration does not invent a chemical name, abbreviation, unit or Home Assistant device class when these cannot be verified.

## Invalid values

Officially invalid or missing readings are represented as unavailable, not as numeric zero.

Sensor attributes include the official station code, magnitude code, abbreviation when known, observation time and official validation marker.

Meteorological attributes also include `data_source`. For regional stations, the primary source is the official AZUL_INTERNET page for the same station and is an automatic, unvalidated hourly mean. If that page fails temporarily, the integration retains a valid value from the official monthly CSV fallback rather than replacing it with zero or an invented value. Municipal hourly values accept only `V`; a newer `N` does not hide the newest usable observation. A previously seen municipal value can survive a short outage or midnight rollover for at most four hours, retaining its original `observation_time`.
