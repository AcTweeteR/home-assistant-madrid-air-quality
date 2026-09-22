# Configuration

Madrid Air Quality & Weather is configured entirely from the Home Assistant UI.

## Initial setup

During setup the integration downloads the official station catalog and presents the available stations in a multi-select field. Select at least one station.

A single config entry represents the Comunidad de Madrid service. Each selected station is represented by a separate Home Assistant device using its official station code as stable identity.

## Change stations

Open **Settings → Devices & services → Madrid Air Quality & Weather → Configure** and change the selection.

No `configuration.yaml` changes are required.

## Polling

Measurement resources are polled every 60 minutes, matching the hourly publication cadence of the official meteorological pages. A coordinated snapshot is shared by all entities. The integration makes at most one online page request per selected station, not one request per sensor, and keeps the official CSV as fallback.

The observation timestamp supplied by the source is kept separate from the time at which Home Assistant downloads the resource.

## Credentials

None. The integration reads public official datasets and stores no account password, API key or token.
