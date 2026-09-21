# Installation

## HACS

This project is a Home Assistant custom integration, **not** a Home Assistant App/add-on.

1. Open **HACS → Integrations → ⋮ → Custom repositories**.
2. Add `https://github.com/AcTweeteR/home-assistant-madrid-air-quality`.
3. Choose **Integration**.
4. Open **Madrid Air Quality & Weather** in HACS and select **Download**.
5. Restart Home Assistant if requested.
6. Open **Settings → Devices & services → Add integration**.
7. Search for **Madrid Air Quality & Weather**.
8. Select one or more stations and finish setup.

No YAML or credentials are required.

## Updates

Install published updates from HACS. HACS uses the repository's GitHub releases to determine available versions. Restart Home Assistant when requested after an update.

## Removal

Remove the config entry from **Settings → Devices & services** first if you no longer want its devices/entities. The integration package itself can then be removed from HACS.
