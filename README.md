# PIC Campo Genérico

App web para el celular (PWA) que funciona **sin conexión** en el campo: mapa con GPS, libreta de estaciones con fotos, notas de voz y croquis, mediciones con la brújula del celular, columnas estratigráficas, estereograma, guía y exportación (KML, CSV, texto, respaldo `.zip`).

Es la versión genérica de [PIC Campo](https://github.com/JoaRavaGeo/pic-campo): el contenido de cada viaje ya no viene dentro de la app. Ahora se **carga una salida de campo**, que es un paquete `.zip` armado por [GeoExplo](https://github.com/JoaRavaGeo/GeoExplo) con «Preparar salida de campo». Una salida trae capas (rásteres en PMTiles, por ejemplo un fondo satelital Sentinel-2, sombreado o favorabilidad, y vectores en GeoJSON), paradas y guía. El formato está en [`docs/formato_paquete_campo.md`](docs/formato_paquete_campo.md).

Se pueden guardar varias salidas en el celular y elegir cuál usar. La de **Paramillos de Uspallata (PIC I 2026)**, que antes venía dentro de la app, ahora es un paquete más ([`paquetes/paramillos-pic-2026.zip`](paquetes/paramillos-pic-2026.zip)) y se carga con un botón.

## Instalarla en Android

1. **Publicar la app** (una sola vez): en GitHub, este repo → **Settings → Pages** → «Deploy from a branch» → rama `main`, carpeta `/ (root)` → Save. A los pocos minutos queda en `https://joaravageo.github.io/pic-campo-generico/`.
2. En el celular, con wifi, abrí esa dirección en **Chrome**.
3. Menú **⋮ → Agregar a la pantalla principal** (o «Instalar app»). Aparece el ícono **PIC Genérico**, con el logo de GeoExplo.
4. Abrila una vez desde el ícono con internet, para que quede guardada para usar sin conexión. En Ajustes (⚙) dice «lista para usar sin conexión ✔».

**Convive con la PIC Campo original.** Las dos apps se pueden tener instaladas a la vez y no comparten nada: esta tiene otro nombre, otra base de datos (`pic-campo-generico`), otros ajustes (`picg.*`) y otros cachés (`picg-…`), y nunca borra los de la original. Las estaciones de una no aparecen en la otra. Si querés pasar tus datos, exportá un respaldo `.zip` en la original (Ajustes → Exportar todo) y restauralo en esta (Ajustes → Restaurar desde un .zip).

## Cargar una salida de campo

**Desde GeoExplo (en la compu):**

1. Proyecto → **Preparar salida de campo**. Elegí capas, paradas y zoom. Si querés un mapa satelital sin señal, marcá **Fondo satelital Sentinel-2**. Revisá el tamaño estimado y tocá «Armar .zip».
2. Pasá el `.zip` al celular (cable, Drive, WhatsApp a vos mismo, etc.) y dejalo en Descargas.

**En el celular** (no hace falta internet):

1. Tocá el nombre de la salida, arriba a la izquierda del mapa. Si todavía no hay ninguna, aparece la tarjeta «Elegí una salida de campo».
2. **Cargar salida (.zip)** → elegí el archivo. La app lo revisa: si le falta algo, dice qué. Después queda guardado en el celular y se abre solo.
3. **Mapa → Capas (botón de capas)**: «Capas de la salida», con casillas, opacidad y leyenda. **Guía**: paradas con «Qué verificar» y avisos, y la guía del paquete. **Ir** marca una parada como destino, con flecha y distancia.
4. Para cambiar de salida o borrar una, tocá otra vez el nombre de arriba (o Ajustes → Salidas guardadas). Tus estaciones, fotos y columnas son las mismas para todas las salidas.

**Paramillos (PIC I 2026):** en la misma tarjeta, **Paramillos · PIC I 2026 (ejemplo incluido)**. Para bajarla hace falta conexión la primera vez.

**El satélite de Esri** (Capas → «Satélite sin señal») sigue como antes: con internet se bajan las teselas de la zona. Si la salida trae el fondo Sentinel-2, ya hay un satélite sin señal sin bajar nada más.

## Qué hay en el repo

| Archivo | Qué es |
|---|---|
| `index.html` | Toda la app (Leaflet 1.9.4 y pmtiles.js 4.5.0 incluidos). |
| `sw.js` | Service worker: guarda la app para usarla sin conexión (cachés `picg-…`, con una copia de respaldo en IndexedDB). |
| `manifest.webmanifest`, `icon-*.png` | Datos para instalarla (nombre, ícono). |
| `paquetes/paramillos-pic-2026.zip` | Salida de Paramillos (PIC I 2026): teledetección en PMTiles, paradas, plan por día, guía, blancos, relieve. |
| `herramientas/` | `armar_paquete_paramillos.py` vuelve a armar ese paquete desde la versión original de la app (commit `2cccd36`). Necesita Node y GeoExplo instalado (usa su escritor de PMTiles): `python herramientas/armar_paquete_paramillos.py`. |
| `docs/formato_paquete_campo.md` | Formato del paquete (copia del de GeoExplo), con las extensiones opcionales de PIC Campo. |

## Licencias de lo incluido

Leaflet (BSD-2-Clause), pmtiles.js (BSD-3-Clause, Protomaps). Datos de las salidas: según su atribución (Copernicus Sentinel-2 y DEM GLO-30 de ESA, EMIT y ASTER de NASA, SEGEMAR/SIGAM, IGN).
