# Troubleshooting

## Integration does not appear after HACS installation

1. Confirm it is downloaded under **HACS → Integrations**.
2. Restart Home Assistant if HACS requested a restart.
3. Open **Settings → Devices & services → Add integration** and search for **Madrid Air Quality & Weather**.

## Station list cannot be loaded

The setup flow downloads the public official station catalog. Confirm Home Assistant has Internet access and check whether the Comunidad de Madrid Open Data service is reachable.

## Sensors are unavailable

An unavailable entity does not necessarily indicate an integration failure. The official source can publish missing or invalid readings. These are intentionally not converted to zero.

Check the entity's observation timestamp and Home Assistant logs.

## A sensor disappeared from the latest official response

The integration remembers previously discovered magnitude codes so temporary source gaps do not remove the entity from Home Assistant.

## Data seems old

Home Assistant polls the official hourly meteorological page every 60 minutes, but polling does not force the source to publish a new mean. Check `observation_time` and `data_source`. The page's values are automatic and pending validation. If the online page fails, the entity may legitimately show a much older observation from the official CSV fallback; this is preferable to inventing a value.

If `data_source` is the AZUL_INTERNET page, the timestamp is converted from the page's solar hour to Europe/Madrid. If it is the CSV fallback, its timestamp comes from the monthly open-data file.

## Logs and diagnostics

Search **Settings → System → Logs** for `madrid_air_quality`. When reporting a reproducible problem, include:

- Home Assistant version;
- integration version;
- affected station;
- affected magnitude;
- approximate time;
- sanitized diagnostics;
- relevant log lines.

This integration has no user credentials, but avoid publishing unrelated private information contained in Home Assistant diagnostics.
