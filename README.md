# Madrid Air Quality & Weather

[![HACS validation](https://github.com/AcTweeteR/home-assistant-madrid-air-quality/actions/workflows/hacs.yml/badge.svg)](https://github.com/AcTweeteR/home-assistant-madrid-air-quality/actions)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-custom%20integration-18BCF2.svg)](https://www.home-assistant.io/)
[![License](https://img.shields.io/github/license/AcTweeteR/home-assistant-madrid-air-quality)](LICENSE)

Home Assistant custom integration for the official air-quality and meteorological monitoring stations operated by the Comunidad de Madrid, Spain.

**Español:** [documentación en español](README.es.md)

> Independent community project. It is not affiliated with or endorsed by the Comunidad de Madrid.

## Features

- UI-only setup: no YAML, account, token or credentials.
- Select one or several monitoring stations.
- One Home Assistant device per selected station.
- Dynamic entities for every magnitude published by each station.
- New official magnitude codes can appear automatically without reinstalling the integration.
- Stable entity IDs/unique IDs based on official station and magnitude codes.
- Shared polling: the integration downloads the official measurement resources once per update, not once per sensor or entity.
- Invalid official values are exposed as unavailable and are never silently converted to zero.
- Spanish and English translations.
- HACS installation and updates.

## Install with HACS

### 1. Add this repository

Until the integration is included in the default HACS catalog:

1. Open **HACS → Integrations**.
2. Open the **⋮** menu and choose **Custom repositories**.
3. Enter:

```text
https://github.com/AcTweeteR/home-assistant-madrid-air-quality
```

4. Select **Integration** as the category.
5. Add the repository.
6. Find **Madrid Air Quality & Weather** in HACS and select **Download**.
7. Restart Home Assistant if HACS requests it.

### 2. Add the integration to Home Assistant

After HACS has downloaded it:

1. Open **Settings → Devices & services**.
2. Select **Add integration**.
3. Search for **Madrid Air Quality & Weather**.
4. Select one or more stations from the official catalog.
5. Finish setup.

No API key, username or password is required.

> Installing the files in HACS and adding the integration in Home Assistant are two separate steps.

## Updating

HACS monitors published GitHub releases. When a newer compatible release is available, HACS exposes the update through Home Assistant's normal update mechanism.

Review the release notes, install the update in HACS and restart Home Assistant if requested.

## Stations and devices

The station catalog is obtained from the official Comunidad de Madrid dataset. Each selected station becomes a separate Home Assistant device, identified internally by its official station code.

You can change the selected stations later from:

**Settings → Devices & services → Madrid Air Quality & Weather → Configure**

Adding or removing a station does not require editing YAML.

## Sensors

Every selected station exposes the measurements that the official source actually publishes for it. Stations do not need to have the same set of sensors.

Typical meteorological entities include:

| Measurement | Abbreviation | Typical unit |
| --- | --- | --- |
| Temperature | TMP | °C |
| Relative humidity | HR | % |
| Atmospheric pressure | PRE | mbar |
| Wind speed | VV | m/s |
| Wind direction | DV | ° |
| Solar radiation | RS | W/m² |
| Precipitation | LL | l/m² |

Typical air-quality entities include SO₂, CO, NO, NO₂, NOx, O₃, PM10, PM2.5, PM1, benzene, toluene, Black Carbon and hydrocarbons when the station publishes them.

Home Assistant combines the device and entity names, producing names such as:

- `Móstoles Temperatura (TMP)`
- `Móstoles Humedad relativa (HR)`
- `Móstoles Dióxido de nitrógeno (NO2)`
- `Móstoles Partículas PM10 (PM10)`

Unknown future magnitude codes are not discarded. The integration preserves their official code rather than inventing a meaning, unit or device class.

See [Entities and sensors](docs/sensors.md) for details.

## Data sources and update frequency

The integration uses only official resources from the [Comunidad de Madrid Open Data Portal](https://datos.comunidad.madrid/):

- **Red de Calidad del Aire. Estaciones** — station catalog and metadata.
- **Red de Calidad del Aire. Datos del día en curso** — current-day air-quality measurements.
- [**AZUL_INTERNET station pages**](https://gestiona.comunidad.madrid/azul_internet/html/web/DatosEstacionAccion.icm?ESTADO_MENU=2&idEstacion=6) — the latest hourly meteorological mean for the same station, including VV, DV, TMP, HR, PRE, RS and LL. The station ID is mapped to the official station code for all 28 stations in the catalogue.
- **Red de calidad del aire. Datos meteorológicos del mes en curso** — fallback meteorological observations when the online station page cannot be read.

Home Assistant polls the hourly meteorological source every 60 minutes. Air-quality and fallback CSV data are included in the same coordinated snapshot. The value timestamp is the observation timestamp supplied by the source, interpreted in the Madrid time zone; the download time is not presented as the measurement time.

The AZUL_INTERNET page identifies the hour in solar time. The integration converts it to Europe/Madrid local time using the official summer/winter offset note. These are automatic, unvalidated readings pending review, not instantaneous measurements. Freshness ultimately depends on the Comunidad de Madrid source.

Each sensor exposes `observation_time`, `official_validation` when the source provides one, and `data_source`. For online meteorology, `official_validation` is empty because the page does not publish a V/T/N flag; the page itself states that the values are pending validation.

These are observations from the air-quality network itself, not a forecast or a substitute for a general meteorological service.

## Availability and invalid values

Official validation flags and missing values are respected. Empty, invalid or non-numeric measurements are not converted to `0`.

A temporarily missing reading does not cause Home Assistant to forget the sensor. Previously discovered magnitude codes are retained so entities remain stable across restarts and temporary source gaps.

## Privacy and security

The integration is read-only. It:

- requires no credentials;
- opens no inbound ports;
- accepts no arbitrary server URL;
- executes no downloaded code;
- sends no commands to monitoring stations.

Home Assistant only makes HTTPS requests to the public Comunidad de Madrid data services. One online request is made per selected station and the response is shared by all seven meteorological entities for that station.

## Troubleshooting

If the integration cannot be added or data becomes unavailable:

1. Verify that Home Assistant has Internet access.
2. Check the official Comunidad de Madrid Open Data portal.
3. Confirm that the integration is still present under **HACS → Integrations**.
4. Restart Home Assistant after a new installation if it was requested.
5. Check **Settings → System → Logs** for `madrid_air_quality`.
6. Download integration diagnostics before opening an issue when possible.

See [Troubleshooting](docs/troubleshooting.md) for detailed guidance.

## Documentation

- [Installation](docs/installation.md)
- [Configuration](docs/configuration.md)
- [Entities and sensors](docs/sensors.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Changelog](CHANGELOG.md)

## Development

```bash
pip install -r requirements_test.txt
pytest -q
ruff check .
```

GitHub Actions validates tests, Ruff, Hassfest, HACS metadata and release/version consistency.

## License and attribution

The integration software is distributed under the [MIT License](LICENSE).

The measurements belong to their respective official source. Review the licensing and reuse terms published with each Comunidad de Madrid dataset before redistributing the underlying data.
