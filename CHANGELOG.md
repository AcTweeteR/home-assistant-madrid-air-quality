# Changelog

## 1.0.4 - 2026-09-22

- Use the official AZUL_INTERNET latest hourly meteorological page for the same 28 Comunidad de Madrid air-quality stations.
- Keep the current CSV meteorological dataset as a safe fallback when the online page is unavailable or invalid.
- Expose the meteorological source and clarify that online values are automatic, unvalidated hourly means.
- Poll the hourly source every 60 minutes instead of implying 20-minute meteorological freshness.

## 1.0.3 - 2026-09-22

- Keep the latest valid or provisional (`T`) pollutant observation when a newer source row is empty or invalid (`N`).
- Preserve the official observation timestamp and validation marker for the selected value.

## 1.0.2 - 2026-09-22

- Use the current official meteorological CSV resource instead of the stale JSON mirror.
- Ignore future hourly placeholders so temporary (`T`) observations are not hidden by a later invalid hour.

## 1.0.1 - 2026-09-22

- Correctly interpret the official `h24` observation as midnight at the start of the following day.

## 1.0.0 - 2026-09-21

- First complete HACS-ready release.
- Official Comunidad de Madrid CKAN catalog and JSON measurements.
- Multi-station config/options flow and dynamic sensors for known and future magnitudes.
- Coordinated polling, diagnostics, translations, tests and CI.
