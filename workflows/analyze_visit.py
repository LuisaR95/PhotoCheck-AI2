"""
PhotoCheck AI - Analizar y guardar una nueva visita (CLI)
--------------------------------------------------------------
Usa db/analyze_service.py — la misma lógica que usa la API.

Uso:
    python -m workflows.analyze_visit --property A-101 --image ruta/a/foto.jpg
    python -m workflows.analyze_visit --property A-101 --image foto.jpg --date 24/08/2026 --notes "Se encontró una fuga de agua"

Si no pasas --date, se usa la fecha de hoy.
"""

import argparse
from datetime import datetime
from pathlib import Path

from db.database import get_session
from db.analyze_service import analyze_and_save_visit
from detector.risk_engine import DATE_FORMAT


def print_risk_box(property_name: str, visit_date: str, result, visit) -> None:
    icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[result.risk_label]

    print(f"\n{property_name} — {visit_date}")
    print("┌─────────────────────────────┐")
    print("│     EVIDENCE RISK SCORE     │")
    print("│                             │")
    print(f"│          {result.risk_score:>3} / 100           │")
    print("│                             │")
    print(f"│      {icon} {result.risk_label + ' RISK':<20}│")
    print("└─────────────────────────────┘")

    if result.matched_image:
        print(f"   Coincide con: {result.matched_image} (método: {result.method})")
        print(f"   Señal visual: {result.visual_score}%")
        if result.cross_property_fraud:
            print(f"   🚨 FRAUDE CRUZADO: coincide con una foto de {result.matched_apartment}, no de {property_name}")
        if result.gap_days is not None:
            print(f"   Diferencia de fechas: {result.gap_days} día(s)")
        if result.exif_discrepancy_days is not None and result.exif_discrepancy_days > 1:
            print(f"   ⚠️  Discrepancia EXIF: {result.exif_discrepancy_days} día(s)")
    else:
        print("   Primera visita registrada para este apartamento (sin historial que comparar).")

    print(f"   Estado guardado: {visit.status}")
    if result.risk_label != "LOW":
        print("   ⚠️  Requiere revisión humana")
    if visit.ai_category:
        print(f"   🧠 Novedad clasificada: {visit.ai_category} · Prioridad {visit.ai_priority} — \"{visit.ai_summary}\"")
    print(f"   ✅ Visita #{visit.id} guardada en la base de datos.")


def main():
    parser = argparse.ArgumentParser(description="Analiza una nueva foto y la guarda como visita en la base de datos.")
    parser.add_argument("--property", required=True, help="Nombre del apartamento, ej. A-101")
    parser.add_argument("--image", required=True, help="Ruta a la foto nueva")
    parser.add_argument("--date", default=None, help="Fecha de la visita DD/MM/AAAA (default: hoy)")
    parser.add_argument("--notes", default=None, help="Novedad reportada por el operario")
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"❌ No se encontró la imagen: {image_path}")
        return

    date_str = args.date or datetime.today().strftime(DATE_FORMAT)

    session = get_session()
    try:
        result, visit = analyze_and_save_visit(
            session=session,
            property_name=args.property,
            image_path=image_path,
            date_str=date_str,
            notes=args.notes,
        )
        print_risk_box(args.property, date_str, result, visit)
    finally:
        session.close()


if __name__ == "__main__":
    main()
