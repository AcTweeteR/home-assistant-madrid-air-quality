# Configuration

Madrid Air Quality & Weather is configured entirely from the Home Assistant UI.

## Initial setup

During setup the integration downloads the two official station catalogues and presents regional and Madrid-city stations in one multi-select field. City labels start with `Madrid —`. Select at least one station; Open-Meteo requires no account, API key or additional field.

A single config entry holds the selected stations from both official networks. Each selected station is represented by a separate Home Assistant device using its official national code as stable identity. Updating an existing installation does not rename or replace the 28 original devices or their entities.

## Change stations

Open **Settings → Devices & services → Madrid Air Quality & Weather → Configure** and change the selection.

No `configuration.yaml` changes are required.

## Polling

Regional resources are polled every 60 minutes; the online station weather page requires at most one request per selected station and the official CSV remains fallback. Municipal air and meteorology use one network-wide JSON request each every 20 minutes. Open-Meteo uses one multicoordinate request every 15 minutes for the selected stations. Sunrise and sunset use one shared local timer and no HTTP. These domains update independently: model downtime does not stop official measurements or solar events.

The observation timestamp supplied by the source is kept separate from the time at which Home Assistant downloads the resource.

## Credentials

None. The integration reads public official datasets and Open-Meteo, storing no account password, API key or token.
