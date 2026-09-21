# Madrid Air Quality & Weather

Integración personalizada de Home Assistant para las estaciones de la Red de Calidad del Aire de la Comunidad de Madrid. Es un proyecto comunitario independiente y no está afiliado ni respaldado por la Comunidad de Madrid.

## Qué hace

- Configuración exclusivamente desde la interfaz de Home Assistant, sin YAML, tokens ni credenciales.
- Una config entry para el servicio y un Device independiente por cada estación seleccionada.
- Selección y modificación de varias estaciones desde el config flow y Options Flow.
- Una entidad por cada magnitud que la estación publica. Las magnitudes nuevas aparecen automáticamente en la siguiente actualización.
- IDs estables basados en el código oficial de estación y el código oficial de magnitud.
- Valores inválidos (`N`, vacío, `***`, `NaN` y equivalentes) se exponen como no disponibles, nunca como cero.

## Fuentes oficiales

La integración usa exclusivamente recursos JSON del [Portal de Datos Abiertos de la Comunidad de Madrid](https://datos.comunidad.madrid/), servido por CKAN:

1. `Red de Calidad del Aire. Estaciones` para catálogo, códigos, nombres y metadatos.
2. `Red de Calidad del Aire. Datos del día en curso` para contaminantes.
3. `Red de calidad del aire. Datos meteorológicos del mes en curso` para meteorología.

El catálogo se descarga al configurar. Cada actualización coordinada realiza dos peticiones, una por recurso de mediciones, y todas las entidades consumen el mismo snapshot; nunca se hace una petición por sensor. Los ficheros son horarios y se consultan cada 20 minutos para reflejar la frecuencia de actualización indicada por la fuente. Las horas se interpretan en `Europe/Madrid`, no como UTC.

La propia Comunidad indica que sus datos meteorológicos son informativos para el contexto de calidad del aire; los datos meteorológicos oficiales son los de [AEMET](https://www.aemet.es/).

## Instalación mediante HACS

1. En HACS, abre **Integraciones** → menú ⋮ → **Repositorios personalizados**.
2. Añade `AcTweeteR/home-assistant-madrid-air-quality` con tipo **Integration**.
3. Instala **Madrid Air Quality & Weather** y reinicia Home Assistant.
4. En **Ajustes → Dispositivos y servicios → Añadir integración**, busca el nombre y selecciona una o más estaciones.

El repositorio está preparado para releases semánticas (`v1.0.0`, `v1.0.1`, `v1.1.0`). HACS detecta releases de GitHub. Para publicar la primera release, el propietario debe crear en GitHub la etiqueta y release `v1.0.0` apuntando al commit validado; el workflow comprueba que coincida con `manifest.json`.

## Entidades

El Device usa el nombre oficial de la estación, por ejemplo `Móstoles`. Las entidades usan nombres propios y `has_entity_name`, por lo que Home Assistant compone nombres como:

- `Móstoles Temperatura (TMP)`
- `Móstoles Humedad relativa (HR)`
- `Móstoles Presión atmosférica (PRE)`
- `Móstoles Dióxido de nitrógeno (NO2)`
- `Móstoles Partículas PM10 (PM10)`

Se incluyen las magnitudes meteorológicas y de contaminación documentadas por la Comunidad, además de códigos desconocidos que aparezcan en el futuro. Para un código desconocido se conserva el código oficial y no se inventan nombre, unidad ni device class.

## Privacidad y limitaciones

La integración es de solo lectura y no almacena credenciales, no acepta URLs arbitrarias, no abre puertos y no ejecuta código remoto. La disponibilidad depende del portal público. Los datos automáticos pueden estar pendientes de validación y no sustituyen información oficial o avisos de calidad del aire.

## Desarrollo y validación

```bash
pip install -r requirements_test.txt
pytest -q
ruff check .
```

GitHub Actions ejecuta tests, Ruff, Hassfest y la validación de HACS. La suite usa fixtures locales sanitizadas y no depende de Internet.

## Licencia y atribución

El software se distribuye bajo [MIT](LICENSE). Los datos de la Comunidad de Madrid se publican bajo [Creative Commons Attribution](https://creativecommons.org/licenses/by/4.0/); consulta sus condiciones en cada dataset oficial.
