"""Round-trip del snapshot: load-snapshot -> export-snapshot conserva los SHA-256.

Usa SQLite en memoria y un snapshot de prueba en un directorio temporal:
ninguna prueba toca la DB real, data/raw/* ni ai_cache.json.
"""
from __future__ import annotations

import json
import os

import pytest

from pipeline import db
from pipeline import snapshot_io as sio


def _fixture(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    base = tmp_path

    noticias = [
        {"id_noticia": "a1", "titulo": "Titular, uno", "url": "http://x/a", "medio": "TVN",
         "idioma": "es", "fecha_publicacion": "2026-09-29T01:23:06Z", "fecha_deteccion": "",
         "fecha_extraccion": "2026-10-08T18:51:31Z", "tema": "turismo", "origen": "RSS",
         "alcance_texto": "titular+metadatos", "descripcion": "texto con \"comillas\" y, coma"},
        {"id_noticia": "b2", "titulo": "Titular dos", "url": "http://x/b", "medio": "GDELT",
         "idioma": "es", "fecha_publicacion": "", "fecha_deteccion": "2026-09-29T01:23:06Z",
         "fecha_extraccion": "2026-10-08T18:51:31Z", "tema": "economia", "origen": "GDELT",
         "alcance_texto": "titular+metadatos", "descripcion": ""},
    ]
    sio._write_csv(str(raw / "noticias.csv"), noticias, sio.CAMPOS_NOTICIAS)

    indicadores = [
        {"pais_iso3": "PAN", "indicador_id": "NY.GDP.MKTP.KD.ZG", "anio": "2024",
         "valor": "1.49330728771066", "unidad": "% anual", "fuente_url": "http://wb",
         "fecha_extraccion": "2026-10-08T18:51:31Z", "licencia": "CC BY 4.0"},
        {"pais_iso3": "PAN", "indicador_id": "X", "anio": "2020", "valor": "", "unidad": "%",
         "fuente_url": "", "fecha_extraccion": "", "licencia": ""},
    ]
    sio._write_csv(str(raw / "indicadores.csv"), indicadores, sio.CAMPOS_INDICADORES)

    eventos = {
        "type": "FeatureCollection", "metadata": {"count": 2},
        "features": [
            {"type": "Feature", "id": "e1",
             "properties": {"mag": 4.2, "place": "near X", "time": 1735513210566,
                            "url": "http://usgs/e1"},
             "geometry": {"type": "Point", "coordinates": [-82.0, 8.0, 10.0]}},
            {"type": "Feature", "id": "e2",
             "properties": {"mag": 3.1, "place": "near Y", "time": 1735513210000,
                            "url": "http://usgs/e2"},
             "geometry": {"type": "Point", "coordinates": [-80.5, 7.5, 5.0]}},
        ],
    }
    with open(raw / "eventos.geojson", "w", encoding="utf-8", newline="") as fh:
        json.dump(eventos, fh, ensure_ascii=False, indent=2)

    fuentes = [{"nombre": "TVN", "url": "http://x", "tipo": "RSS", "confiabilidad": 5,
                "licencia": "CC"}]
    with open(base / "fuentes.json", "w", encoding="utf-8", newline="") as fh:
        json.dump(fuentes, fh, ensure_ascii=False, indent=2)

    manifest = {
        "version": "v1", "rules_version": "p-3.0",
        "fecha_corte_UTC": "2026-10-08T00:00:00+00:00",
        "sha256": {f: sio._sha256(str(raw / f)) for f in sio.FILES},
        "cantidad_por_archivo": {"noticias.csv": 2, "indicadores.csv": 2, "eventos.geojson": 2},
        "transformaciones": ["x"],
    }
    manifest_path = base / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8", newline="") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    return raw, manifest_path, base


def test_roundtrip_mismos_sha256(tmp_path):
    raw, manifest_path, base = _fixture(tmp_path)
    out = base / "out"
    out.mkdir()

    conn = db.connect(":memory:")  # SQLite en memoria; no toca la DB real
    sio.load_snapshot(conn=conn, raw_dir=str(raw), manifest_path=str(manifest_path),
                      fuentes_path=str(base / "fuentes.json"))
    sio.export_snapshot(conn=conn, out_dir=str(out), manifest_path=str(base / "out_manifest.json"))

    for f in sio.FILES:
        assert sio._sha256(str(out / f)) == sio._sha256(str(raw / f)), f


def test_load_aborta_si_sha256_no_coincide(tmp_path):
    raw, manifest_path, base = _fixture(tmp_path)
    # corrompe el manifest: cambia un hash
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    m["sha256"]["noticias.csv"] = "0" * 64
    manifest_path.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")

    conn = db.connect(":memory:")
    with pytest.raises(SystemExit):
        sio.load_snapshot(conn=conn, raw_dir=str(raw), manifest_path=str(manifest_path),
                          fuentes_path=str(base / "fuentes.json"))
