"""Carga/exporta el snapshot congelado hacia/desde la base SQLite operativa.

- `load-snapshot`  : construye la DB desde data/raw/* + data/manifest.json y
                     **verifica el SHA-256 de cada archivo contra el manifest**
                     (aborta si no coincide).
- `export-snapshot`: regenera data/raw/* + data/manifest.json desde la DB.

El snapshot (CSV/JSONL/GeoJSON + manifest) sigue siendo el contrato de datos del
reto; la DB es estado operativo reconstruible. El round-trip es sin pérdida:
los archivos exportados tienen el mismo SHA-256 que los originales.

Uso:
    python -m pipeline.snapshot_io --load
    python -m pipeline.snapshot_io --export
    make load-snapshot | make export-snapshot
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys

from pipeline import db

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RAW = os.path.join(DATA, "raw")
MANIFEST_PATH = os.path.join(DATA, "manifest.json")
FUENTES_PATH = os.path.join(DATA, "fuentes.json")

FILES = ("noticias.csv", "indicadores.csv", "eventos.geojson")

CAMPOS_NOTICIAS = ["id_noticia", "titulo", "url", "medio", "idioma",
                   "fecha_publicacion", "fecha_deteccion", "fecha_extraccion",
                   "tema", "origen", "alcance_texto", "descripcion"]
CAMPOS_INDICADORES = ["pais_iso3", "indicador_id", "anio", "valor", "unidad",
                      "fuente_url", "fecha_extraccion", "licencia"]


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_csv(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def _read_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _write_csv(path: str, rows: list[dict], fields: list[str]) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def _verify_manifest(manifest: dict, raw_dir: str) -> None:
    sha = manifest.get("sha256") or {}
    for f in FILES:
        path = os.path.join(raw_dir, f)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Falta {f} en el snapshot ({path})")
        if f not in sha:
            raise ValueError(f"manifest.json no declara sha256 para {f}")
        actual = _sha256(path)
        if actual != sha[f]:
            raise SystemExit(
                f"SHA-256 de {f} NO coincide con manifest.json:\n"
                f"  esperado {sha[f]}\n  obtenido {actual}\n"
                f"Abortando; no se construye la DB desde un snapshot corrupto."
            )


def load_snapshot(db_path: str | None = None, conn=None, raw_dir: str = RAW,
                  manifest_path: str = MANIFEST_PATH, fuentes_path: str = FUENTES_PATH) -> dict:
    manifest = _read_json(manifest_path)
    _verify_manifest(manifest, raw_dir)

    noticias = _read_csv(os.path.join(raw_dir, "noticias.csv"))
    indicadores = _read_csv(os.path.join(raw_dir, "indicadores.csv"))
    with open(os.path.join(raw_dir, "eventos.geojson"), encoding="utf-8", newline="") as fh:
        eventos_text = fh.read()
    eventos = json.loads(eventos_text)
    fuentes = _read_json(fuentes_path) if os.path.exists(fuentes_path) else []

    if conn is None:
        conn = db.connect(db_path)
    db.init(conn)
    with db.transaction(conn):
        db.insert_fuentes(conn, fuentes)
        db.insert_noticias(conn, noticias)
        for r in noticias:
            db.upsert_clasificacion(conn, r.get("url", ""),
                                    r.get("tema") or "general", None, None,
                                    "csv", False, False)
        db.upsert_indicadores(conn, indicadores)
        db.replace_eventos(conn, eventos.get("features", []))
        db.record_snapshot(conn, manifest, eventos_text)

    return {
        "noticias": len(noticias),
        "indicadores": len(indicadores),
        "eventos": len(eventos.get("features", [])),
        "fuentes": len(fuentes),
        "sha256_ok": manifest.get("sha256"),
    }


def export_snapshot(db_path: str | None = None, conn=None, out_dir: str = RAW,
                    manifest_path: str = MANIFEST_PATH) -> dict:
    if conn is None:
        conn = db.connect(db_path)
    snap = db.get_snapshot(conn)
    if snap is None:
        raise RuntimeError("No hay snapshot en la DB; corre `load-snapshot` primero.")

    noticias = db.get_noticias(conn)
    indicadores = db.get_indicadores(conn)
    eventos_text = snap.get("eventos_json")

    os.makedirs(out_dir, exist_ok=True)
    _write_csv(os.path.join(out_dir, "noticias.csv"), noticias, CAMPOS_NOTICIAS)
    _write_csv(os.path.join(out_dir, "indicadores.csv"), indicadores, CAMPOS_INDICADORES)
    with open(os.path.join(out_dir, "eventos.geojson"), "w", encoding="utf-8", newline="") as fh:
        fh.write(eventos_text or "")

    sha = {f: _sha256(os.path.join(out_dir, f)) for f in FILES}
    manifest = snap["manifest"]
    manifest["sha256"] = sha
    n_ev = len(db.get_eventos_features(conn))
    manifest["cantidad_por_archivo"] = {
        "noticias.csv": len(noticias), "indicadores.csv": len(indicadores),
        "eventos.geojson": n_ev,
    }
    with open(manifest_path, "w", encoding="utf-8", newline="") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    return {"noticias": len(noticias), "indicadores": len(indicadores),
            "eventos": n_ev, "sha256": sha}


def main() -> int:
    if "--load" in sys.argv:
        conn = db.connect()
        try:
            res = load_snapshot(conn=conn)
        finally:
            conn.close()
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    if "--export" in sys.argv:
        conn = db.connect()
        try:
            res = export_snapshot(conn=conn)
        finally:
            conn.close()
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    print("Uso: python -m pipeline.snapshot_io --load | --export", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
