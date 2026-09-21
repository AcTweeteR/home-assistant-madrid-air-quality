"""Constants for the Madrid Air Quality integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "madrid_air_quality"
NAME = "Madrid Air Quality & Weather"
VERSION = "1.0.0"
PLATFORMS = [Platform.SENSOR]
CONF_STATIONS = "stations"
CONF_KNOWN_METRICS = "known_metrics"
UPDATE_INTERVAL_MINUTES = 20

CKAN_API = "https://datos.comunidad.madrid/api/3/action/package_show?id={}"
CATALOG_PACKAGE = "calidad_aire_estaciones"
AIR_PACKAGE = "calidad_aire_datos_dia"
WEATHER_PACKAGE = "calidad_aire_datos_meteo_mes"

# These resource URLs are the official JSON resources exposed by CKAN. The
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
    "resource/dd692c0c-5698-4af1-9f6c-61b6b9a63782/download/calidad_aire_datos_meteo_mes.json"
)
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
