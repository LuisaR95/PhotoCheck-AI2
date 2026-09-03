"""
PhotoCheck AI - Servicio de análisis + guardado de visitas
--------------------------------------------------------------
Punto de entrada ÚNICO para analizar y guardar una visita — lo usan
tanto la API (api/main.py) como el CLI (workflows/analyze_visit.py),
para que ambos se comporten exactamente igual.

Flujo:
  1. Busca (o crea) el apartamento declarado.
  2. Trae TODO el historial de la base de datos (de TODOS los
     apartamentos — necesario para detectar fraude cruzado).
  3. Corre el Risk Engine (pHash + ORB + fecha + EXIF + fraude cruzado).
  4. Guarda una copia permanente de la foto en images/visits/<apto>/.
  5. Inserta el registro de la visita con todos los datos del análisis.
"""

import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from db.models import Property, Visit, User
from detector.risk_engine import (
    DATE_FORMAT, PhotoMeta, HistoricalItem, RiskResult, evaluate_against_history,
)
from ai.notes_processor import process_notes

BASE_DIR = Path(__file__).resolve().parent.parent
VISITS_DIR = BASE_DIR / "images" / "visits"


def get_or_create_property(session: Session, name: str) -> Property:
    prop = session.query(Property).filter_by(name=name).first()
    if prop is None:
        prop = Property(name=name)
        session.add(prop)
        session.commit()
        print(f"🏠 Apartamento '{name}' creado en la base de datos.")
    return prop


def load_full_history(session: Session) -> list[HistoricalItem]:
    """Trae TODAS las visitas de TODOS los apartamentos (para fraude cruzado)."""
    visits = session.query(Visit).join(Property).all()
    history = []
    for v in visits:
        path = Path(v.image_path)
        if not path.exists():
            continue
        history.append(HistoricalItem(
            identifier=str(v.id),
            path=path,
            apartment=v.property.name,
            date=datetime.combine(v.visit_date, datetime.min.time()),
        ))
    return history


def _matched_label(item: HistoricalItem) -> str:
    date_str = item.date.strftime(DATE_FORMAT) if item.date else "fecha desconocida"
    return f"Visita #{item.identifier} ({date_str}, {item.apartment})"


def save_image_copy(source_path: Path, property_name: str, visit_date: datetime, original_name: str) -> Path:
    dest_dir = VISITS_DIR / property_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_name = f"{visit_date.strftime('%Y-%m-%d_%H%M%S')}_{original_name}"
    dest_path = dest_dir / dest_name
    shutil.copy2(source_path, dest_path)
    return dest_path


def status_from_risk(risk_label: str) -> str:
    # 🟢 BAJO -> aprobación automática. 🟡/🔴 -> requiere revisión humana.
    return "APPROVED" if risk_label == "LOW" else "PENDING_REVIEW"


def analyze_and_save_visit(
    session: Session,
    property_name: str,
    image_path: Path,
    date_str: str,
    notes: str | None = None,
    uploaded_by_username: str | None = None,
) -> tuple[RiskResult, Visit]:
    """
    'image_path' es la ruta al archivo recién subido/temporal: se usa
    para el análisis y luego se copia a almacenamiento permanente.

    'uploaded_by_username' identifica qué usuario subió la evidencia
    (para que el administrador sepa a quién revisar). Es opcional para
    no romper el CLI cuando se corre sin un usuario autenticado.
    """
    visit_date = datetime.strptime(date_str, DATE_FORMAT)

    prop = get_or_create_property(session, property_name)
    history = load_full_history(session)

    uploaded_by_id = None
    if uploaded_by_username:
        uploader = session.query(User).filter_by(username=uploaded_by_username).first()
        if uploader:
            uploaded_by_id = uploader.id

    new_meta = PhotoMeta(filename=image_path.name, apartment=property_name, date=visit_date)
    result = evaluate_against_history(image_path, new_meta, history, label_fn=_matched_label)

    stored_path = save_image_copy(image_path, property_name, visit_date, image_path.name)
    status = status_from_risk(result.risk_label)

    # Clasificación de la novedad con IA (opcional — nunca bloquea el análisis)
    ai_result = process_notes(notes)

    new_visit = Visit(
        property_id=prop.id,
        uploaded_by_id=uploaded_by_id,
        visit_date=visit_date.date(),
        image_path=str(stored_path),
        notes=notes,
        risk_score=result.risk_score,
        status=status,
        method=result.method,
        visual_score=round(result.visual_score),
        cross_property_fraud=result.cross_property_fraud,
        matched_visit_id=int(result.matched_id) if result.matched_id else None,
        exif_date=result.exif_date.date() if result.exif_date else None,
        exif_discrepancy_days=result.exif_discrepancy_days,
        ai_category=ai_result["categoria"] if ai_result else None,
        ai_priority=ai_result["prioridad"] if ai_result else None,
        ai_summary=ai_result["resumen"] if ai_result else None,
    )
    session.add(new_visit)
    session.commit()

    return result, new_visit
