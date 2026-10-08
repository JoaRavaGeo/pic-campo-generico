# Formato del paquete de salida de campo (GeoExplo → PIC Campo)

**Versión del formato: 1** (2026-10-08; campos opcionales agregados en el Tramo 6, ver "Cambios"). Lo genera GeoExplo ("Preparar salida de campo", `src/geoexplo/export/campo.py`) y lo lee PIC Campo Genérico (`JoaRavaGeo/pic-campo-generico`, Tramo 6). Este documento se copia tal cual a ese repositorio (`docs/formato_paquete_campo.md`).

## Resumen

Un único archivo `.zip` que se abre **sin conexión**, en el navegador del celular y sin servidor:

```
salida_campo_<proyecto>_<fecha>.zip
├── manifest.json                 obligatorio
├── raster/<id>.pmtiles           0 o más (teselas WebP en Web Mercator)
├── vector/<id>.geojson           0 o más (WGS84, RFC 7946)
├── paradas.geojson               opcional (puntos a visitar, en orden)
├── guia.md                       opcional (fichas en texto)
└── extras/                       opcional, extensiones de PIC Campo (relieve, pic.json)
```

- Los `.pmtiles` van **sin comprimir** dentro del zip (`STORED`): ya están comprimidos y así se pueden extraer y leer por rangos de bytes.
- Los demás archivos van con `DEFLATE`.
- Rutas con `/`, relativas a la raíz del zip, sin `..`.

## `manifest.json`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `formato` | texto | sí | Siempre `"geoexplo-salida-campo"`. |
| `version` | entero | sí | Versión del formato (este documento: `1`). Un lector rechaza versiones que no conoce. |
| `nombre` | texto | sí | Nombre de la salida (lo elige el usuario). |
| `proyecto` | texto | sí | Proyecto de GeoExplo de origen. |
| `creado` | texto ISO 8601 | sí | Fecha y hora local de armado. |
| `generador` | texto | sí | `"GeoExplo <versión>"`. |
| `crs` | texto | sí | `"EPSG:4326"` (coordenadas de los GeoJSON y de `bbox`). |
| `aoi.bbox` | [O, S, E, N] | sí | Recuadro del AOI en grados. |
| `centro` | [lon, lat] | sí | Centro inicial del mapa. |
| `zoom.min`, `zoom.max` | enteros | sí | Zooms con teselas ráster (0–17). |
| `capas` | lista | sí | Ver abajo, en orden de dibujo (de abajo hacia arriba: primero los rásteres). |
| `paradas` | objeto o `null` | sí | `{"archivo": "paradas.geojson", "n": <cantidad>, "estilo": {"color": "#rrggbb"}}`. |
| `guia` | texto o `null` | sí | Ruta de la guía (`"guia.md"`). |
| `aviso` | texto | no | Recordatorio de que lo interpretativo es hipótesis. |
| `atribuciones` | lista de texto | sí | Atribuciones que hay que mostrar (p. ej. Copernicus). |
| `relieve` | objeto | no | Modelo de elevación para curvas de nivel y cota en PIC Campo (ver "Extensiones de PIC Campo"). |
| `extras` | objeto | no | `{"pic": "extras/pic.json"}`: contenido enriquecido para PIC Campo (ver abajo). |

### Capas (`capas[]`)

Campos comunes: `id` (único, sin espacios), `nombre`, `tipo` (`"raster"` o `"vector"`), `formato`, `archivo`, `visible` (estado inicial).

**Ráster** (`tipo: "raster"`, `formato: "pmtiles"`):

- `tesela`: `"webp"`; `tamano_tesela`: `256`.
- `zoom`: {min, max}; `bounds`: [O, S, E, N] de la capa.
- `opacidad` (0–1).
- `grupo`: origen en GeoExplo (`dem`, `s2`, `alteracion`, `favorabilidad`…).
- `leyenda`: la misma estructura que usa GeoExplo: `{"tipo": "continua", "paleta", "min", "max", "unidad", "nota"}` o `{"tipo": "categorias", "clases": [{"valor", "nombre", "color"}], "nota"}`. `color` es `[r, g, b, a]` (0–255) o `"#rrggbb"`; `paleta` es un nombre (`magma`, `turbo`, `terrain`, `YlOrRd`, `viridis`, `inferno`…) o una lista de colores; `min`/`max` pueden ser número o texto. También vale `{"tipo": "nota", "nota"}` (sólo texto).
- `atribucion`.
- Opcionales: `fondo` (`true` en el fondo satelital: va primera, debajo de todo), `fechas` (fechas de las escenas), `remuestreo` (`"vecino"` para mapas categóricos que se agrandan sin suavizar, `"lineal"` por defecto).

**Vectorial** (`tipo: "vector"`, `formato: "geojson"`):

- `geometria`: `"punto"`, `"linea"`, `"poligono"` o `"mixta"`.
- `elementos`: cantidad de elementos.
- `estilo.color`: color sugerido (`#rrggbb`).

Los atributos son los de la capa en GeoExplo, con valores simples (texto, número o booleano). Se recortan al AOI + 2 km.

## Rásteres: PMTiles v3

Formato evaluado y elegido: **PMTiles v3** ([especificación](https://github.com/protomaps/PMTiles/blob/main/spec/v3/spec.md)).

**Por qué PMTiles:**

- Un archivo por capa en lugar de cientos o miles de teselas sueltas. En el teléfono se guarda tal cual, en OPFS o como `Blob` en IndexedDB.
- Se lee por rangos de bytes con [`pmtiles.js`](https://github.com/protomaps/PMTiles) (BSD-3), con `FileSource` y sin servidor.
- MapLibre lo usa con `addProtocol("pmtiles", …)`.

**Alternativas descartadas:**

- MBTiles: es SQLite y en el navegador necesita sql.js (~1 MB).
- Carpeta `z/x/y.png`: miles de entradas en el zip y en IndexedDB.

**Detalles del archivo:**

- Teselas de 256 px en **Web Mercator** (esquema XYZ, `y` hacia abajo). Imágenes **WebP** con alfa: transparente fuera de los datos. Las teselas vacías no se guardan.
- Encabezado: `tile_type = 4` (WebP), `tile_compression = 1` (ninguna), `internal_compression = 2` (gzip), `clustered = 1`. Los directorios hoja se usan solo si la raíz supera los 16 KB.
- Metadatos JSON: `name`, `attribution`, `generador`.

**Tamaño:** cada zoom más multiplica las teselas por ~4. Referencia: Paramillos (~200 km²), 4 capas, zoom 10–15 → 482 teselas por capa, ~1 MB por capa.

### Fondo satelital Sentinel-2 (opcional)

Capa `fondo_s2` (`grupo: "fondo"`, `fondo: true`, `visible: true`, opacidad 1), primera de `capas[]`:

- **Qué es:** color verdadero de Sentinel-2 L2A (producto `visual`/TCI de 8 bits, 10 m) de la escena de verano con menos nubes (≤ 5 %) de las últimas 3 temporadas que cubre el recuadro; si una sola no alcanza, se completan los huecos con las siguientes. Las fechas van en `fechas` y en la atribución.
- **Recuadro:** AOI + 2 km (el mismo margen que los vectores).
- **Zoom:** de `zoom.min` hasta 14 como máximo (~8 m por píxel a 32° S, el detalle real de Sentinel-2). Más arriba el visor agranda las teselas del 14.
- **Licencia:** datos Copernicus libres; se pueden redistribuir sin conexión con la atribución "Copernicus Sentinel-2 (ESA)". (El satélite de Esri que usa PIC Campo con internet no se puede meter en el paquete.)
- **Tamaño:** Paramillos (AOI + 2 km ≈ 23 × 21 km), zoom 10–14: 197 teselas, **1,6 MB** (~8 kB por tesela). Sin bajar la imagen, GeoExplo estima teselas × 10 kB; ya bajada, la mide como las demás capas.

## `paradas.geojson`

`FeatureCollection` de puntos, ordenada por `orden` (1, 2, …). Una parada todavía sin coordenadas puede ir con `"geometry": null`. Propiedades:

| Propiedad | Descripción |
|---|---|
| `orden` | Orden de visita propuesto. |
| `id`, `numero` | Punto de interés de GeoExplo (`PI-01`, 1). |
| `estado` | `nuevo` o `conocido`. |
| `puntaje` | Puntaje de la zona (0–1). |
| `confianza` | `alta`, `media` o `baja`. |
| `verificar` | Qué verificar en el campo (ítems separados por ` \| `). |
| `avisos` | Avisos (halo de veta, capas rojas, mica metamórfica…), separados por ` \| `. |
| `ficha_json` | La ficha completa del punto (JSON en texto), igual que en GeoExplo. |
| `etiqueta`, `nombre`, `unidad` | Opcionales: texto corto del marcador, nombre y descripción (los usa la salida de Paramillos migrada de PIC Campo). |

## `guia.md`

Markdown simple: una sección por parada, con ubicación, puntaje, confianza, ocurrencia más cercana, avisos y la lista "Qué verificar".

## Lectura (referencia)

El visor de prueba de GeoExplo (`src/geoexplo/web/campo.html` + `js/campo.js`) es la implementación de referencia:

1. Descomprime el zip en el navegador con `fflate`.
2. Valida el manifiesto: `formato`, `version`, que existan todos los archivos y los formatos por tipo.
3. Dibuja los PMTiles (`new pmtiles.PMTiles(new pmtiles.FileSource(file))`) y los GeoJSON con MapLibre.
4. Lista las paradas.

PIC Campo Genérico (Tramo 6) hace lo mismo sin dependencias externas salvo `pmtiles.js` (incluido): descomprime el zip con su lector propio, valida igual, guarda cada salida en IndexedDB (un `Blob` por archivo) y dibuja con Leaflet (una capa de teselas que lee el PMTiles; GeoJSON en canvas). La guía se muestra partida en secciones por los títulos `##`.

## Extensiones de PIC Campo (opcionales)

Las usa la salida de Paramillos (PIC I 2026), que estaba embebida en la app original y se migró a un paquete (`pic-campo-generico/herramientas/armar_paquete_paramillos.py`). Un lector que no las conozca las ignora.

**`relieve`**: `{"archivo": "extras/relieve.bin", "formato": "pic-relieve-1", "min", "max", "atribucion"}`. Binario: `"PICD"`, `uint32` LE con el largo del encabezado, encabezado JSON (`z`, `tile`, `px0`, `py0`, `w`, `h`, `base`, `escala`, `min`, `max`, `fuente`) y después la grilla `w × h` comprimida con zlib (`deflate`): `int16` LE con diferencias acumuladas desde `base`; cota = acumulado × `escala` (m). La grilla está en píxeles globales de Web Mercator del zoom `z` con teselas de `tile` px, empezando en (`px0`, `py0`). PIC Campo saca de ahí las curvas de nivel, el sombreado y la cota de un punto.

**`extras.pic`** (`extras/pic.json`, `{"version": 1, …}`), todo opcional:

| Campo | Qué es |
|---|---|
| `viaje` | `titulo`, `encabezado` (líneas del título), `fechas`, `zona`, `docentes`. |
| `plan` | Plan por día: `[{grupo, nombre, color, dias: [[día, [ids de paradas]]]}]`. |
| `unidades` | Lista de unidades para autocompletar en la libreta. |
| `guia` | `unidades` (`n`, `e`, `d`), `estructuras` (`n`, `d`), `mineral`, `objetivos`, `checklist`. |
| `tele` | `fuente`, `depositos` (`id`, `nombre`, `tipo`, `lat`, `lon`, `val`), `blancos` (`id`, `nombre`, `lat`, `lon`, `cerca`, `dato`, `hip`, `ver`) y `trampas`: marcadores y fichas de teledetección. |
| `mapas` | Mapas georreferenciados que se reconocen por el nombre del archivo al cargarlos: `{clave: {nombre, bounds: [[S, O], [N, E]], opacity, nota, claves: [textos]}}`. |
| `declinacion` | `{valor, nota}` para la zona y la fecha. |
| `textos` | Textos cortos de la interfaz (`plan`, `plan_sin`, `paradas`, `mapas`, `importar`, `tele`). Siempre texto plano. |

## Cambios de versión

- Campos nuevos opcionales: no cambian la versión (un lector ignora lo que no conoce).
- Cambios incompatibles (quitar o renombrar campos, otro formato de ráster): `version` + 1.

Historial:

- **Tramo 6 (2026-10-08), sigue siendo la versión 1** (todo opcional): capa de fondo satelital Sentinel-2 (`fondo`, `fechas`), `remuestreo`, leyendas con paleta como lista y `tipo: "nota"`, colores `#rrggbb`, paradas sin geometría y con `etiqueta`/`nombre`/`unidad`, `relieve` y `extras.pic` para PIC Campo.
