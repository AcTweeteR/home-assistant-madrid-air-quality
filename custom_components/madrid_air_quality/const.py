"""Constants for the Madrid Air Quality integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "madrid_air_quality"
NAME = "Madrid Air Quality & Weather"
VERSION = "1.0.6"
PLATFORMS = [Platform.SENSOR]
CONF_STATIONS = "stations"
CONF_KNOWN_METRICS = "known_metrics"
UPDATE_INTERVAL_MINUTES = 60
MUNICIPAL_UPDATE_INTERVAL_MINUTES = 20
MODEL_UPDATE_INTERVAL_MINUTES = 15
SOLAR_UPDATE_INTERVAL_MINUTES = 10

MUNICIPAL_AIR_CATALOG_URL = (
    "https://datos.madrid.es/dataset/212629-0-estaciones-control-aire/"
    "resource/212629-0-estaciones-control-aire-csv/download/212629-0-estaciones-control-aire-csv.csv"
)
MUNICIPAL_WEATHER_CATALOG_URL = (
    "https://datos.madrid.es/dataset/300360-0-meteorologicos-estaciones/"
    "resource/300360-1-meteorologicos-estaciones-csv/download/300360-1-meteorologicos-estaciones-csv.csv"
)
MUNICIPAL_AIR_URL = (
    "https://datos.madrid.es/dataset/212531-0-calidad-aire-tiempo-real/"
    "resource/212531-0-calidad-aire-tiempo-real/download/212531-0-calidad-aire-tiempo-real.json"
)
MUNICIPAL_WEATHER_URL = (
    "https://datos.madrid.es/dataset/300392-0-meteorologia-tiempo-real/"
    "resource/300392-5-meteorologia-tiempo-real/download/300392-5-meteorologia-tiempo-real.json"
)
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
SOURCE_MUNICIPAL_AIR = "Ayuntamiento de Madrid: calidad del aire en tiempo real"
SOURCE_MUNICIPAL_WEATHER = "Ayuntamiento de Madrid: meteorología en tiempo real"
SOURCE_OPEN_METEO = "Open-Meteo Forecast API (modelo, no medición de la estación)"
SOURCE_SOLAR = "Cálculo astronómico local (Astral)"

CKAN_API = "https://datos.comunidad.madrid/api/3/action/package_show?id={}"
CATALOG_PACKAGE = "calidad_aire_estaciones"
AIR_PACKAGE = "calidad_aire_datos_dia"
WEATHER_PACKAGE = "calidad_aire_datos_meteo_mes"

# These resource URLs are the official resources exposed by CKAN. The
# package endpoints above remain the canonical source of metadata; the URLs are
# kept here so normal polling does not make an extra CKAN request every cycle.
CATALOG_URL = (
    "https://datos.comunidad.madrid/dataset/4cd076a3-e602-48da-b834-58de39d3125c/"
    "resource/0aa62bb9-9fad-42df-826d-72ae903e3bd6/download/calidad_aire_estaciones.json"
)
AIR_URL = (
    "https://datos.comunidad.madrid/dataset/3dacd589-ecca-485c-81b9-a61606b7199f/"
    "resource/93bed3f0-3ba5-4b00-90bf-1c81951bab24/download/calidad_aire_datos_dia.json"
)
WEATHER_URL = (
    "https://datos.comunidad.madrid/dataset/7e2f01e3-fda0-4693-8f8f-206cf0d74bf4/"
    "resource/d61356c9-9055-4e6f-bffb-16695b01a2da/download/calidad_aire_datos_meteo_mes.csv"
)
ONLINE_WEATHER_BASE_URL = (
    "https://gestiona.comunidad.madrid/azul_internet/html/web/"
    "DatosEstacionAccion.icm?ESTADO_MENU=2&idEstacion="
)
# The public Comunidad de Madrid on-line index currently exposes these 28
# stations with stable numeric links.  The mapping is complete for the
# station catalogue used by this integration and is covered by tests.
ONLINE_STATION_IDS = {
    "28005002": 3,
    "28006004": 4,
    "28148004": 7,
    "28049003": 9,
    "28014002": 15,
    "28123002": 18,
    "28009001": 20,
    "28134002": 114,
    "28065014": 1,
    "28074007": 2,
    "28058004": 5,
    "28092005": 6,
    "28007004": 8,
    "28013002": 13,
    "28161001": 21,
    "28106001": 111,
    "28045002": 11,
    "28080003": 12,
    "28047002": 14,
    "28127004": 112,
    "28115003": 113,
    "28067001": 19,
    "28016001": 22,
    "28120001": 110,
    "28133002": 17,
    "28171001": 23,
    "28102001": 24,
    "28180001": 16,
}
SOURCE_ONLINE_WEATHER = "Comunidad de Madrid AZUL_INTERNET (última media horaria)"
SOURCE_NAME = "Portal de Datos Abiertos de la Comunidad de Madrid (CKAN)"
SOURCE_CATALOG = "Red de Calidad del Aire. Estaciones"
SOURCE_AIR = "Red de Calidad del Aire. Datos del día en curso"
SOURCE_WEATHER = "Red de calidad del aire. Datos meteorológicos del mes en curso"

# Official magnitude codes and names from the data dictionaries supplied by
# the Comunidad de Madrid. Unknown codes are deliberately not rejected.
MAGNITUDES = {
    "1": ("Dióxido de azufre", "SO2", "µg/m³"),
    "6": ("Monóxido de carbono", "CO", "mg/m³"),
    "7": ("Monóxido de nitrógeno", "NO", "µg/m³"),
    "8": ("Dióxido de nitrógeno", "NO2", "µg/m³"),
    "9": ("Partículas PM2.5", "PM2.5", "µg/m³"),
    "10": ("Partículas PM10", "PM10", "µg/m³"),
    "11": ("Partículas PM1", "PM1", "µg/m³"),
    "12": ("Óxidos de nitrógeno", "NOx", "µg/m³"),
    "14": ("Ozono", "O3", "µg/m³"),
    "20": ("Tolueno", "TOL", "µg/m³"),
    "22": ("Black Carbon", "BC", "µg/m³"),
    "30": ("Benceno", "BEN", "µg/m³"),
    "35": ("Etilbenceno", "EBE", "µg/m³"),
    "42": ("Hidrocarburos totales", "HCT", "mg/m³"),
    "44": ("Hidrocarburos no metánicos", "HNM", "mg/m³"),
    "431": ("MetaParaXileno", "XIL", "µg/m³"),
    "81": ("Velocidad del viento", "VV", "m/s"),
    "82": ("Dirección del viento", "DV", "°"),
    "83": ("Temperatura", "TMP", "°C"),
    "86": ("Humedad relativa", "HR", "%"),
    "87": ("Presión atmosférica", "PRE", "mbar"),
    "88": ("Radiación solar", "RS", "W/m²"),
    "89": ("Precipitación", "LL", "l/m²"),
}

INVALID_VALUES = frozenset({"", "***", "N", "NA", "N/A", "NAN", "NULL", "NONE"})
