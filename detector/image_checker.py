"""
PhotoCheck AI - Modo de pruebas por carpetas
--------------------------------------------------------------
Usa detector/risk_engine.py, pero leyendo las fotos desde carpetas
locales (images/historical y images/new) en vez de la base de datos.
Útil para probar rápido sin depender de PostgreSQL.

Para el flujo real conectado a la base de datos, usa:
    python -m workflows.analyze_visit --property A-101 --image foto.jpg

Uso:
    python -m detector.image_checker
"""

import json
from datetime import datetime
from pathlib import Path

from detector.risk_engine import (
    VALID_EXTENSIONS, DATE_FORMAT, PhotoMeta, HistoricalItem, evaluate_against_history,
)


def load_history_from_folder(folder: Path) -> list[HistoricalItem]:
    metadata_path = folder / "metadata.json"
    raw = {}
    if metadata_path.exists():
        try:
            raw = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"⚠️  No se pudo leer {metadata_path.name} en {folder.name}: {e}")

    items = []
    for path in sorted(folder.glob("*")):
        if path.suffix.lower() not in VALID_EXTENSIONS:
            continue
        entry = raw.get(path.name, {})
        apartment = entry.get("apartment")
        date_obj = None
        date_str = entry.get("date")
        if date_str:
            try:
                date_obj = datetime.strptime(date_str, DATE_FORMAT)
            except ValueError:
                print(f"⚠️  Fecha inválida para {path.name}: '{date_str}' (formato esperado DD/MM/AAAA)")
        if apartment is None:
            print(f"⚠️  {path.name} no tiene 'apartment' en metadata.json.")
        items.append(HistoricalItem(identifier=path.name, path=path, apartment=apartment, date=date_obj))
    return items


def print_risk_box(new_image: str, apartment, result) -> None:
    icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[result.risk_label]
    label = f"{result.risk_label} RISK"

    print(f"\n{new_image}" + (f"  (Apto {apartment})" if apartment else ""))
    print("┌─────────────────────────────┐")
    print("│     EVIDENCE RISK SCORE     │")
    print("│                             │")
    print(f"│          {result.risk_score:>3} / 100           │")
    print("│                             │")
    print(f"│      {icon} {label:<20}│")
    print("└─────────────────────────────┘")

    if result.matched_image:
        print(f"   Coincide con: {result.matched_image} (método: {result.method})")
        print(f"   Señal visual: {result.visual_score}%")
        if result.cross_property_fraud:
            print(f"   🚨 FRAUDE CRUZADO: la foto pertenece a {result.matched_apartment}, no a {apartment}")
        if result.gap_days is not None:
            print(f"   Diferencia de fechas: {result.gap_days} día(s) -> señal fecha: {result.date_score}%")
        if result.exif_discrepancy_days is not None and result.exif_discrepancy_days > 1:
            print(f"   ⚠️  Discrepancia EXIF: {result.exif_discrepancy_days} día(s) entre fecha declarada y fecha real de cámara")
    else:
        print("   No se encontraron fotos históricas para comparar.")

    if result.risk_label != "LOW":
        print("   ⚠️  Requiere revisión humana")


def main():
    base_dir = Path(__file__).resolve().parent.parent
    historical_dir = base_dir / "images" / "historical"
    new_dir = base_dir / "images" / "new"

    if not historical_dir.exists() or not new_dir.exists():
        print("❌ No se encontraron las carpetas images/historical o images/new")
        return

    print("📚 Cargando historial (todas las fotos, todos los apartamentos)...")
    history = load_history_from_folder(historical_dir)
    print(f"   {len(history)} fotos históricas cargadas.")

    new_items = load_history_from_folder(new_dir)
    if not new_items:
        print("\nℹ️  No hay fotos nuevas en images/new para analizar.")
        return

    print(f"\n🔍 Analizando {len(new_items)} foto(s) nueva(s)...")
    for item in new_items:
        new_meta = PhotoMeta(filename=item.identifier, apartment=item.apartment, date=item.date)
        result = evaluate_against_history(item.path, new_meta, history)
        print_risk_box(item.identifier, item.apartment, result)


if __name__ == "__main__":
    main()
