"""Arma el paquete de salida de Paramillos (PIC I 2026) a partir de la versión original de PIC Campo.

La app original traía el viaje embebido (paradas, guía, teledetección y relieve). En PIC Campo
genérico ese contenido pasa a ser un paquete con el formato de GeoExplo
(``docs/formato_paquete_campo.md``, versión 1) más las extensiones opcionales de PIC Campo
(``extras/pic.json`` y ``relieve``).

Uso (desde la raíz del repo, con GeoExplo instalado para el escritor de PMTiles):

    python herramientas/armar_paquete_paramillos.py            # toma los datos del commit original
    python herramientas/armar_paquete_paramillos.py --origen carpeta_con_index_y_bins

Salida: ``paquetes/paramillos-pic-2026.zip``.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import re
import struct
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from PIL import Image

from geoexplo.export.campo import ORIGEN, TESELA, Fuente, codificar, escribir_pmtiles, rango_teselas

RAIZ = Path(__file__).resolve().parents[1]
COMMIT_ORIGINAL = "2cccd36"  # última versión de JoaRavaGeo/pic-campo con el viaje embebido
ARCHIVOS = ("index.html", "relieve.bin", "teledeteccion.bin")
ZOOM_MIN = 10

# Orden de dibujo de la app original (de abajo hacia arriba) y opacidades por defecto
ORDEN = ["s2_color", "s2_swir", "s2_cocientes", "aster_cuarzo", "emit_fe", "emit_swir", "emit_aloh", "s2_fe", "s2_oh", "sintesis"]
OPACIDAD = {"s2_color": 1, "s2_swir": 0.9, "s2_cocientes": 0.85, "s2_oh": 0.9, "s2_fe": 0.9, "sintesis": 0.9,
            "emit_swir": 0.85, "emit_fe": 0.8, "emit_aloh": 0.9, "aster_cuarzo": 0.85}


def atribucion(cid: str) -> str:
    if cid.startswith("s2"):
        return "Sentinel-2: ESA Copernicus"
    if cid.startswith("emit"):
        return "EMIT: NASA JPL / LP DAAC"
    if cid.startswith("aster"):
        return "ASTER: NASA/METI"
    return "EMIT + ASTER: NASA"


def origen(dir_: Path | None) -> Path:
    if dir_:
        return dir_
    tmp = Path(tempfile.mkdtemp(prefix="pic_original_"))
    for a in ARCHIVOS:
        (tmp / a).write_bytes(subprocess.run(["git", "show", f"{COMMIT_ORIGINAL}:{a}"], cwd=RAIZ, check=True,
                                             capture_output=True).stdout)
    return tmp


def datos_embebidos(index: Path) -> dict:
    out = subprocess.run(["node", str(RAIZ / "herramientas" / "extraer_datos_pic.js"), str(index)], check=True,
                         capture_output=True, text=True).stdout
    return json.loads(out)


def leer_bin(path: Path) -> tuple[dict, bytes]:
    b = path.read_bytes()
    hl = struct.unpack("<I", b[4:8])[0]
    return json.loads(b[8:8 + hl]), b[8 + hl:]


def _color(c: str) -> list[int]:
    c = c.strip()
    if c.startswith("#"):
        return [int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16), 255]
    v = [float(x) for x in re.findall(r"[\d.]+", c)]
    return [int(v[0]), int(v[1]), int(v[2]), round(255 * (v[3] if len(v) > 3 else 1))]


def _texto(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()


def leyenda(html: str) -> dict:
    """Pasa la leyenda HTML de la app original a la estructura de GeoExplo."""
    notas = [_texto(n) for n in re.findall(r'<div class="ley-nota">(.*?)</div>', html)]
    clases = [{"valor": i + 1, "nombre": _texto(t), "color": _color(c)}
              for i, (c, t) in enumerate(re.findall(r'<i style="background:([^"]+)"></i>(.*?)</span>', html))]
    g = re.search(r'<div class="ley-grad"><span>(.*?)</span><b style="background:linear-gradient\(90deg,([^)]*)\)"></b><span>(.*?)</span>', html)
    if g:
        return {"tipo": "continua", "paleta": g.group(2).split(","), "min": _texto(g.group(1)), "max": _texto(g.group(3)),
                "unidad": "", "nota": " ".join(notas)}
    if clases:
        return {"tipo": "categorias", "clases": clases, "nota": " ".join(notas)}
    return {"tipo": "nota", "nota": _texto(html)}


def zoom_nativo(fuente: Fuente, ancho_px: int) -> int:
    """Zoom a partir del cual la tesela ya no gana detalle (píxel de tesela ≤ 1,5 píxeles de la imagen)."""
    res = (fuente.x1 - fuente.x0) / ancho_px
    return max(ZOOM_MIN, min(16, math.ceil(math.log2(2 * ORIGEN / TESELA / (1.5 * res)))))


def teselas(fuente: Fuente, zmin: int, zmax: int, sin_perdida: bool) -> dict:
    """Como ``campo.teselas_de``, pero los mapas categóricos van en WebP sin pérdida (colores exactos)."""
    out = {}
    for z in range(zmin, zmax + 1):
        x0, y0, x1, y1 = rango_teselas(fuente.bounds, z)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                t = fuente.tesela(z, x, y)
                if t is None:
                    continue
                if sin_perdida:
                    b = io.BytesIO()
                    Image.fromarray(t, "RGBA").save(b, "WEBP", lossless=True, method=6)
                    out[(z, x, y)] = b.getvalue()
                else:
                    out[(z, x, y)] = codificar(t)
    return out


def guia_md(d: dict) -> str:
    """Texto de la guía que no tiene estructura propia en pic.json: método de teledetección, tablas y fuentes."""
    dep = [["Cerro Canario", 99, 98, "mica 59 % · caol+mica 24 %"], ["Paramillos Sur", 98, 97, "caol+mica 53 % · mica 30 %"],
           ["Paramillos Centro", 83, 93, "mica 38 % · carbonatos"], ["Oro del Sur", 78, 75, "mica 70 %"],
           ["Paramillos Norte", 64, 89, "carbonatos · esmectita"], ["Vetas Paramillos", 38, 36, "carbonatos 91 % · Fe²⁺"]]
    par = [["2026.1", "caol+mica 46 % · esmectita 19 %", "hematita 95 %"], ["2026.2", "caolinita 21 % · dickita/nacrita 20 %", "hematita 49 % · goethita 45 %"],
           ["2026.3", "caol+mica 33 %", "hematita 94 %"], ["2026.4", "calcita+mica 31 % · mica 18 %", "goethita 72 %"],
           ["2026.5", "caolinita 63 % · dickita/nacrita 16 %", "goethita 56 % · hematita 39 %"], ["2026.6", "carbonatos 64 % · mica 23 %", "Fe²⁺ 100 %"],
           ["2026.7", "esmectita 37 % · calcita+mica 21 %", "hematita 70 %"]]
    v = d["VIAJE"]
    lin = [f"# {v['titulo']} · Cerro Redondo – Paramillos de Uspallata", "", v["fechas"], "", v["docentes"], "",
           "## Teledetección: cómo se hizo", "", d["TELE"]["fuente"], "",
           "- **EMIT**: reflectancia corregida por atmósfera y mineral identificado por Tetracorder (USGS) en dos fechas independientes. Sólo se aceptó un mineral con banda ≥ 0,02; donde las fechas coinciden (68 % de los píxeles en 2 µm, 82 % en 1 µm) el mapa es opaco.",
           "- **Química de la mica blanca**: posición del mínimo Al-OH (≈2200 nm) con remoción del continuo y ajuste cuadrático, en las dos fechas. Diferencia media entre fechas: 1,1 nm (r = 0,76).",
           "- **ASTER**: índices SWIR (Al-OH, caolinita, Mg-OH) de 2000 y 2007, y cuarzo, sílice, carbonato y máficos de la emisividad térmica AG100.",
           "- **Síntesis**: zonas por mineral dominante; la “fílica probable” es mica con banda en el cuartil más profundo (≥ 0,087) y Al-OH en el cuartil más corto (≤ 2204 nm).",
           "", "### ¿Funciona acá? Control con depósitos conocidos", "",
           "| Depósito | S2 OH | S2 Fe³⁺ | EMIT (300 m) |", "|---|---|---|---|"]
    lin += [f"| {r[0]} | p{r[1]} | p{r[2]} | {r[3]} |" for r in dep]
    lin += ["", "S2: percentil del valor alto (p90 local, 250 m) respecto de toda el área. EMIT: proporción de píxeles en 300 m. Los pórfiros y el epitermal con alteración expuesta dan mica blanca ± caolinita; las vetas dan su ganga carbonática y los basaltos de caja.",
            "", "### Qué ve EMIT en cada parada", "", "| Parada | 2 µm (arcillas, micas) | 1 µm (Fe) |", "|---|---|---|"]
    lin += [f"| {r[0]} | {r[1]} | {r[2]} |" for r in par]
    lin += ["", "2026.1 y 2026.3: capas rojas. 2026.2 y 2026.5: bordes de los dos sistemas argílicos (B1 y B2–B3); ASTER da cuarzo p95 en 2026.5. 2026.6: basaltos triásicos. Radio de 300 m.",
            "", "## Fuentes", "",
            "- Cátedra PIC I (2026): guía de campo, programa y presentación metodológica.",
            "- Orellano Ricchetti, Winocur y Rubinstein (2017), RAGA 74(2): geología y estructura de las vetas de Paramillos de Uspallata.",
            "- Orellano Ricchetti, tesis doctoral (UBA): estratigrafía y estructura del depocentro Paramillos.",
            "- Carrasquero (2015), tesis doctoral: magmatismo mioceno (Fm. Cerro Redondo).",
            "- Brea, Artabe y Spalletti (2009), RAGA 64(1): bosque de Darwin en Agua de la Zorra.",
            "- SEGEMAR (1999): Carta Geológica de la República Argentina 1:100.000, Hoja 3369-09 Uspallata.",
            "- Datos satelitales: ESA Copernicus (Sentinel-2 L2A); NASA LP DAAC: EMIT L2A RFL, L2A MASK y L2B MIN V001; ASTER AST_07XT y AST_05 V004; ASTER GED AG100 V003. Tetracorder: Clark et al. (2003), USGS.",
            "- Relieve: Copernicus DEM GLO-30 (ESA) vía Mapterhorn.", ""]
    return "\n".join(lin)


def paradas_geojson(d: dict) -> dict:
    feats = []
    for k, p in enumerate(d["PARADAS_BASE"], 1):
        geom = {"type": "Point", "coordinates": [p["lon"], p["lat"]]} if p["lat"] is not None else None
        feats.append({"type": "Feature", "geometry": geom, "properties": {
            "orden": k, "id": p["id"], "etiqueta": p["id"].split(".")[-1], "nombre": f"Parada {p['id']}",
            "unidad": p["unidad"], "confianza": p.get("conf") or None, "verificar": "", "avisos": ""}})
    return {"type": "FeatureCollection", "features": feats}


def pic_json(d: dict) -> dict:
    v = d["VIAJE"]
    return {
        "version": 1,
        "viaje": {"titulo": v["titulo"], "encabezado": ["Cerro Redondo", "· Paramillos de Uspallata"], "fechas": v["fechas"],
                  "zona": v["zona"], "docentes": v["docentes"]},
        "plan": d["PLAN"],
        "unidades": d["UNIDADES"],
        "guia": {k: d["GUIA"][k] for k in ("unidades", "estructuras", "mineral", "objetivos", "checklist")},
        "tele": d["TELE"],
        # claves: textos del nombre del archivo que reconocen cada mapa al cargarlo (como en la app original)
        "mapas": {k: {**v, "claves": {"brea": ["brea"], "orellano": ["orellano"], "hoja": ["3369", "segemar", "hoja"]}.get(k, [k])}
                  for k, v in d["PRESETS"].items()},
        "declinacion": {"valor": -1.9, "nota": "La declinación para la zona en octubre de 2026 es ≈ −1,9° (oeste), según el modelo WMM2025."},
        "textos": {
            "plan": "Puntos sugeridos en la presentación de la cátedra. Elegí tu recuadro para resaltarlo en el mapa.",
            "plan_sin": "Los números grises (.0, .8, .9) no tienen coordenadas en el KMZ que se cargó. Cargalas acá abajo o importando el KMZ desde Mapa → Capas.",
            "paradas": "La unidad esperable sale de la Hoja Geológica 3369-09 Uspallata (SEGEMAR 1999), contrastada con Orellano Ricchetti y con EMIT. Es un mapa 1:100.000 de 1999: confirmala en el afloramiento.",
            "mapas": "Pasá al celu las imágenes brea2009_fig3.webp y orellano2017_fig1a.webp (o la Hoja 3369-09) y cargalas acá: se ubican solas.",
            "importar": "KML/KMZ de Google Earth (por ejemplo el de la cátedra), GPX de un GPS.",
            "tele": "Minerales de alteración identificados con EMIT (hiperespectral, 2 fechas), cuarzo de ASTER térmico e índices de Sentinel-2, validados contra los depósitos conocidos. Empezá por la Síntesis. La interpretación y qué mirar en cada blanco están en Guía → Teledetección.",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--origen", type=Path, help="Carpeta con index.html, relieve.bin y teledeteccion.bin originales")
    ap.add_argument("--salida", type=Path, default=RAIZ / "paquetes" / "paramillos-pic-2026.zip")
    a = ap.parse_args()
    src = origen(a.origen)
    d = datos_embebidos(src / "index.html")
    meta, datos = leer_bin(src / "teledeteccion.bin")
    rel_meta, _ = leer_bin(src / "relieve.bin")
    grupos = {cid: g for g, ids in d["TELE_GRUPOS"] for cid in ids}

    archivos: dict[str, bytes] = {}
    capas = []
    w_all, s_all, e_all, n_all = 180, 90, -180, -90
    por_id = {c["id"]: c for c in meta["capas"]}
    with tempfile.TemporaryDirectory() as tmp:
        for cid in ORDEN:
            c = por_id[cid]
            (s, w), (n, e) = c["bounds"]
            w_all, s_all, e_all, n_all = min(w_all, w), min(s_all, s), max(e_all, e), max(n_all, n)
            img = datos[c["off"]:c["off"] + c["len"]]
            f = Fuente(io.BytesIO(img), [[w, n], [e, n], [e, s], [w, s]])
            zmax = zoom_nativo(f, f.img.shape[1])
            vecino = bool(re.match(r"^(emit|sintesis)", cid))
            tes = teselas(f, ZOOM_MIN, zmax, vecino)
            p = Path(tmp) / f"{cid}.pmtiles"
            escribir_pmtiles(p, tes, f.bounds, {"name": c["nombre"], "attribution": atribucion(cid), "generador": "PIC Campo"})
            archivos[f"raster/{cid}.pmtiles"] = p.read_bytes()
            capas.append({"id": cid, "nombre": c["nombre"], "tipo": "raster", "formato": "pmtiles", "archivo": f"raster/{cid}.pmtiles",
                          "tesela": "webp", "tamano_tesela": TESELA, "zoom": {"min": ZOOM_MIN, "max": zmax}, "bounds": list(f.bounds),
                          "opacidad": OPACIDAD[cid], "visible": False, "grupo": grupos.get(cid, "Teledetección"),
                          "leyenda": leyenda(d["TELE_LEY"].get(cid, "")), "atribucion": atribucion(cid),
                          "remuestreo": "vecino" if vecino else "lineal"})
            print(f"{cid} ({f.img.shape[1]} px): {len(tes)} teselas, zoom {ZOOM_MIN}–{zmax}, {len(archivos[f'raster/{cid}.pmtiles']) / 1e3:.0f} kB")
    archivos["extras/relieve.bin"] = (src / "relieve.bin").read_bytes()
    archivos["extras/pic.json"] = json.dumps(pic_json(d), ensure_ascii=False, indent=1).encode()
    par = paradas_geojson(d)
    archivos["paradas.geojson"] = json.dumps(par, ensure_ascii=False).encode()
    archivos["guia.md"] = guia_md(d).encode()
    manifest = {
        "formato": "geoexplo-salida-campo", "version": 1, "nombre": "PIC I 2026 · Paramillos de Uspallata",
        "proyecto": "Paramillos de Uspallata (PIC Campo original)", "creado": datetime.now().isoformat(timespec="seconds"),
        "generador": "PIC Campo · herramientas/armar_paquete_paramillos.py", "crs": "EPSG:4326",
        "aoi": {"bbox": [w_all, s_all, e_all, n_all]}, "centro": [-69.208, -32.462],
        "zoom": {"min": ZOOM_MIN, "max": max(c["zoom"]["max"] for c in capas)}, "capas": capas,
        "paradas": {"archivo": "paradas.geojson", "n": len(par["features"]), "estilo": {"color": "#b0452a"}},
        "guia": "guia.md",
        "aviso": "La unidad esperable de cada parada y los blancos de teledetección son hipótesis: confirmalos en el afloramiento.",
        "atribuciones": sorted({c["atribucion"] for c in capas} | {"Relieve: Copernicus DEM GLO-30 (ESA) vía Mapterhorn"}),
        "relieve": {"archivo": "extras/relieve.bin", "formato": "pic-relieve-1", "min": rel_meta["min"], "max": rel_meta["max"],
                    "atribucion": "Relieve: Copernicus DEM GLO-30 (ESA) vía Mapterhorn"},
        "extras": {"pic": "extras/pic.json"},
    }
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(a.salida, "w") as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False), zipfile.ZIP_DEFLATED)
        for arch, cont in archivos.items():
            z.writestr(arch, cont, zipfile.ZIP_STORED if arch.endswith((".pmtiles", ".bin")) else zipfile.ZIP_DEFLATED)
    print(f"Listo: {a.salida} ({a.salida.stat().st_size / 1e6:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
