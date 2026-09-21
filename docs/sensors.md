# Entities and sensors

Each selected station becomes a Home Assistant device. Sensor identity is based on the official station code plus official magnitude code.

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

The integration currently recognises official codes for SO₂, CO, NO, NO₂, PM2.5, PM10, PM1, NOx, O₃, toluene, Black Carbon, benzene, total hydrocarbons, non-methane hydrocarbons and MetaParaXylene.

The exact entities depend on what the selected station publishes.

## Unknown future codes

Unknown codes are retained and exposed rather than silently discarded. The integration does not invent a chemical name, abbreviation, unit or Home Assistant device class when these cannot be verified.

## Invalid values

Officially invalid or missing readings are represented as unavailable, not as numeric zero.

Sensor attributes include the official station code, magnitude code, abbreviation when known, observation time and official validation marker.
