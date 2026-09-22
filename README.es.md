# Madrid Air Quality & Weather

Integración personalizada para Home Assistant que incorpora las estaciones oficiales de la Red de Calidad del Aire de la Comunidad de Madrid y expone sus mediciones como sensores.

> Proyecto comunitario independiente. No está afiliado ni respaldado por la Comunidad de Madrid.

## Características

- Configuración completamente gráfica, sin YAML.
- No necesita usuario, contraseña ni API key.
- Permite seleccionar una o varias estaciones.
- Cada estación aparece como un dispositivo independiente.
- Crea automáticamente los sensores que publique cada estación.
- Conserva IDs estables y recuerda magnitudes aunque falten temporalmente.
- Admite nuevos códigos oficiales sin tener que actualizar una lista cerrada de sensores.
- Datos meteorológicos horarios de las mismas estaciones y datos de calidad del aire.
- Instalación y actualizaciones mediante HACS.

## Instalación con HACS

Mientras no esté incluida en el catálogo general de HACS:

1. Abre **HACS → Integraciones**.
2. Pulsa el menú **⋮ → Repositorios personalizados**.
3. Introduce:

```text
https://github.com/AcTweeteR/home-assistant-madrid-air-quality
```

4. Selecciona la categoría **Integración**.
5. Añade el repositorio.
6. Busca **Madrid Air Quality & Weather** y pulsa **Descargar**.
7. Reinicia Home Assistant si HACS lo solicita.

Después hay que añadir la integración:

1. Ve a **Ajustes → Dispositivos y servicios**.
2. Pulsa **Añadir integración**.
3. Busca **Madrid Air Quality & Weather**.
4. Selecciona una o varias estaciones.
5. Finaliza la configuración.

**Importante:** descargarla desde HACS e incorporarla desde Dispositivos y servicios son dos pasos distintos.

## Cambiar las estaciones

Ve a **Ajustes → Dispositivos y servicios → Madrid Air Quality & Weather → Configurar**.

Desde ahí puedes modificar la selección sin editar YAML ni reinstalar la integración.

## Sensores

Cada estación expone únicamente las magnitudes que realmente publica.

Entre las meteorológicas pueden aparecer:

| Medición | Sigla | Unidad habitual |
| --- | --- | --- |
| Temperatura | TMP | °C |
| Humedad relativa | HR | % |
| Presión atmosférica | PRE | mbar |
| Velocidad del viento | VV | m/s |
| Dirección del viento | DV | ° |
| Radiación solar | RS | W/m² |
| Precipitación | LL | l/m² |

En calidad del aire puede exponer, según la estación, SO₂, CO, NO, NO₂, NOx, O₃, PM10, PM2.5, PM1, benceno, tolueno, Black Carbon e hidrocarburos, entre otros.

Los nombres completos quedan asociados a la estación, por ejemplo:

- `Móstoles Temperatura (TMP)`
- `Móstoles Humedad relativa (HR)`
- `Móstoles Dióxido de nitrógeno (NO2)`
- `Móstoles Partículas PM10 (PM10)`

Si la Comunidad de Madrid empieza a publicar una magnitud desconocida, la integración no la descarta: crea la entidad conservando el código oficial y evita inventar su significado o unidad.

## Fuente y frecuencia

La integración utiliza exclusivamente recursos públicos oficiales de la Comunidad de Madrid:

- **Red de Calidad del Aire. Estaciones**
- **Red de Calidad del Aire. Datos del día en curso**
- [**Páginas de estación AZUL_INTERNET**](https://gestiona.comunidad.madrid/azul_internet/html/web/DatosEstacionAccion.icm?ESTADO_MENU=2&idEstacion=6): última media horaria de VV, DV, TMP, HR, PRE, RS y LL para la misma estación. El ID web está cruzado con el código oficial de las 28 estaciones del catálogo.
- **Red de calidad del aire. Datos meteorológicos del mes en curso** como respaldo si la página online no responde o no contiene datos válidos.

La integración consulta la fuente meteorológica horaria cada 60 minutos. Todos los sensores de una estación reutilizan la misma respuesta; no se realiza una petición por entidad.

La web oficial expresa la hora en formato solar. La integración la convierte a Europe/Madrid aplicando +2 en verano y +1 en invierno. Son medias horarias automáticas pendientes de revisión, no datos instantáneos. Cada entidad conserva `observation_time` y muestra `data_source`.

La fuente online no proporciona un marcador V/T/N para meteorología; por eso `official_validation` queda vacío y la semántica de “pendiente de validación” procede de la advertencia explícita de la propia página. Los valores vacíos o `***` nunca se convierten en cero.

Los datos meteorológicos de esta red tienen carácter informativo en el contexto de calidad del aire. Para previsiones o información distinta de la observación de estas estaciones debe consultarse el servicio meteorológico oficial correspondiente.

## Datos inválidos

Un dato ausente o marcado como inválido por la fuente **no se transforma en cero**. Se muestra como no disponible.

Una ausencia temporal tampoco elimina la entidad. Las magnitudes ya descubiertas se conservan para mantener estable el Entity Registry.

## Actualizaciones

Las versiones se publican mediante GitHub Releases. HACS detecta las nuevas releases y las muestra mediante el mecanismo habitual de actualizaciones de Home Assistant.

Antes de actualizar puedes consultar [CHANGELOG.md](CHANGELOG.md).

## Privacidad y seguridad

Es una integración de solo lectura. No almacena credenciales, no abre puertos, no ejecuta comandos en las estaciones y no permite configurar servidores arbitrarios.

## Problemas

Si deja de funcionar:

1. Comprueba que Home Assistant tiene Internet.
2. Comprueba que el portal de datos de la Comunidad de Madrid está disponible.
3. Verifica que la integración continúa instalada en HACS.
4. Revisa **Ajustes → Sistema → Registros** buscando `madrid_air_quality`.
5. Descarga los diagnósticos de la integración antes de abrir una incidencia, si están disponibles.

Consulta [la guía de solución de problemas](docs/troubleshooting.md).

## Documentación

- [Instalación](docs/installation.md)
- [Configuración](docs/configuration.md)
- [Sensores](docs/sensors.md)
- [Solución de problemas](docs/troubleshooting.md)
- [Historial de cambios](CHANGELOG.md)

## Licencia

El software se distribuye bajo licencia MIT. Los datos proceden del Portal de Datos Abiertos de la Comunidad de Madrid y están sujetos a las condiciones publicadas por la fuente oficial.
