import sys
from pathlib import Path
import shutil
import tempfile

# Garantizar que la raíz del proyecto esté en sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
import jwt

from db.database import get_session
from db.models import Property, Visit, User
from db.analyze_service import analyze_and_save_visit
from auth.security import verify_password, create_access_token, decode_access_token, hash_password
from auth.dependencies import require_role

app = FastAPI(
    title="PhotoCheck AI Enterprise",
    description="API para la detección automatizada de fotografías reutilizadas y fraude operativo.",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EMBEDDED_HTML_PATH = PROJECT_ROOT / "frontend" / "index.html"


def render_frontend():
    """Sirve frontend/index.html si existe, o un mensaje de respaldo si no."""
    if EMBEDDED_HTML_PATH.is_file():
        content = EMBEDDED_HTML_PATH.read_text(encoding="utf-8")
        if content.strip():
            return HTMLResponse(
                content=content,
                status_code=200,
                headers={"Cache-Control": "no-cache, no-store, must-revalidate, max-age=0"},
            )
    return HTMLResponse(
        content="<h1>PhotoCheck AI</h1><p>No se encontró frontend/index.html</p>",
        status_code=200,
    )


@app.get("/", response_class=HTMLResponse)
def serve_root():
    return render_frontend()


@app.get("/app", response_class=HTMLResponse)
def serve_app():
    return render_frontend()


@app.get("/visits/{visit_id}/photo")
def get_visit_photo(visit_id: int, token: str | None = None):
    """
    Sirve el archivo de imagen de una visita.

    Las etiquetas <img> del navegador no pueden mandar el header
    'Authorization', así que aquí aceptamos el token como parámetro
    de la URL (?token=...) en vez de exigirlo como header.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Falta el token de sesión.")

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Tu sesión expiró.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido.")

    if payload.get("role") != "administrador":
        raise HTTPException(status_code=403, detail="No tienes acceso a este recurso.")

    session = get_session()
    try:
        visit = session.query(Visit).filter_by(id=visit_id).first()
        if not visit:
            raise HTTPException(status_code=404, detail="Visita no encontrada.")

        image_path = Path(visit.image_path)
        if not image_path.exists():
            raise HTTPException(status_code=404, detail="La imagen ya no existe en el servidor.")

        return FileResponse(image_path)
    finally:
        session.close()


@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Recibe usuario/contraseña (form-urlencoded, estándar OAuth2) y
    devuelve un token JWT si son correctos.
    """
    session = get_session()
    try:
        user = session.query(User).filter_by(username=form_data.username).first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")
        token = create_access_token(username=user.username, role=user.role)
        return {
            "access_token": token,
            "token_type": "bearer",
            "role": user.role,
            "full_name": user.full_name,
        }
    finally:
        session.close()


class CreateUserPayload(BaseModel):
    username: str
    password: str
    full_name: str | None = None
    role: str  # "operario" | "administrador"


@app.get("/users")
def list_users(current_user: dict = Depends(require_role("administrador"))):
    session = get_session()
    try:
        users = session.query(User).order_by(User.role, User.username).all()
        return [
            {"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role}
            for u in users
        ]
    finally:
        session.close()


@app.post("/users")
def create_user(payload: CreateUserPayload, current_user: dict = Depends(require_role("administrador"))):
    if payload.role not in ("operario", "administrador"):
        raise HTTPException(status_code=400, detail="El rol debe ser 'operario' o 'administrador'.")

    session = get_session()
    try:
        existing = session.query(User).filter_by(username=payload.username).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Ya existe un usuario con el username '{payload.username}'.")

        user = User(
            username=payload.username,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            role=payload.role,
        )
        session.add(user)
        session.commit()
        return {"id": user.id, "username": user.username, "full_name": user.full_name, "role": user.role}
    finally:
        session.close()


@app.get("/stats")
def get_stats(current_user: dict = Depends(require_role("administrador"))):
    """Resumen para las tarjetas del dashboard del supervisor."""
    session = get_session()
    try:
        total = session.query(Visit).count()
        approved = session.query(Visit).filter(Visit.status == "APPROVED").count()
        pending = session.query(Visit).filter(Visit.status == "PENDING_REVIEW").count()
        high_risk = session.query(Visit).filter(Visit.risk_score >= 70).count()
        return {
            "total": total,
            "validas": approved,
            "requieren_revision": pending,
            "posibles_duplicadas": high_risk,
        }
    finally:
        session.close()


@app.get("/visits")
def list_visits(current_user: dict = Depends(require_role("administrador"))):
    """Lista de todas las visitas para la tabla del dashboard."""
    session = get_session()
    try:
        visits = (
            session.query(Visit)
            .join(Property)
            .order_by(Visit.visit_date.desc(), Visit.id.desc())
            .all()
        )
        return [
            {
                "id": v.id,
                "apartamento": v.property.name,
                "fecha": v.visit_date.strftime("%d/%m/%Y"),
                "similitud": v.visual_score,
                "riesgo": v.risk_score,
                "estado": v.status,
                "metodo": v.method,
                "fraude_cruzado": v.cross_property_fraud,
                "notas": v.notes,
                "novedad_categoria": v.ai_category,
                "novedad_prioridad": v.ai_priority,
                "novedad_resumen": v.ai_summary,
                "coincide_con_id": v.matched_visit_id,
                "operario": v.uploaded_by.full_name or v.uploaded_by.username if v.uploaded_by else None,
            }
            for v in visits
        ]
    finally:
        session.close()


@app.post("/analyze")
def analyze_photo(
        file: UploadFile = File(...),
        apartment: str = Form(...),
        date: str = Form(...),
        notes: str | None = Form(None),
        current_user: dict = Depends(require_role("operario", "administrador")),
):
    with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=Path(file.filename).suffix or ".jpg"
    ) as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_path = Path(temp_file.name)

    session = get_session()
    try:
        result, visit = analyze_and_save_visit(
            session=session,
            property_name=apartment.strip(),
            image_path=temp_path,
            date_str=date.strip(),
            notes=notes,
            uploaded_by_username=current_user["username"],
        )

        niveles_riesgo = {"LOW": "BAJO", "MEDIUM": "MEDIO", "HIGH": "ALTO"}
        motivos = []

        if result.cross_property_fraud:
            motivos.append(
                f"🚨 ¡ALERTA DE FRAUDE CRUZADO!: La fotografía coincide con una evidencia "
                f"registrada originalmente en el apartamento {result.matched_apartment}."
            )
        elif result.matched_image is not None:
            motivos.append("Se encontró una fotografía histórica para comparar.")

        if result.visual_score >= 90:
            motivos.append("La fotografía coincide visualmente con una fotografía histórica.")

        if result.matched_image is not None and not result.cross_property_fraud:
            motivos.append("La comparación se realizó con fotografías históricas del mismo apartamento.")

        if result.gap_days is not None and result.gap_days > 0 and result.visual_score >= 50:
            motivos.append(f"Han transcurrido {result.gap_days} días desde la fotografía histórica comparada.")

        if result.exif_discrepancy_days is not None and result.exif_discrepancy_days > 1:
            exif_str = result.exif_date.strftime('%d/%m/%Y') if result.exif_date else 'Desconocida'
            motivos.append(
                f"⚠️ INCONSISTENCIA EXIF: La fecha reportada ({date.strip()}) difiere de la fecha real "
                f"grabada por la cámara ({exif_str})."
            )
        elif result.exif_date is not None:
            motivos.append("✅ Metadatos EXIF validados: La fecha de la cámara coincide con la fecha declarada.")

        if result.matched_image is None:
            motivos.append("No existen fotografías históricas disponibles para comparar (primera visita).")

        if visit.ai_category:
            motivos.append(
                f"🧠 IA clasificó la novedad como '{visit.ai_category}' con prioridad '{visit.ai_priority}'."
            )

        if result.cross_property_fraud:
            recomendacion = "RECHAZAR SERVICIO: Evidencia reutilizada de otro apartamento."
        elif result.risk_label == "HIGH":
            recomendacion = "Revisar la evidencia fotográfica antes de aprobar el servicio."
        elif result.risk_label == "MEDIUM":
            recomendacion = "Se recomienda realizar una revisión adicional de la fotografía."
        else:
            recomendacion = "No se encontraron indicios importantes de reutilización."

        return {
            "visita_id": visit.id,
            "archivo": file.filename,
            "apartamento": result.apartment,
            "nivel_riesgo": niveles_riesgo.get(result.risk_label, result.risk_label),
            "puntaje_riesgo": result.risk_score,
            "foto_coincidente": result.matched_image,
            "apartamento_coincidente": result.matched_apartment,
            "fraude_cruzado": result.cross_property_fraud,
            "metodo_comparacion": result.method,
            "similitud_visual": result.visual_score,
            "dias_desde_foto_anterior": result.gap_days,
            "fecha_exif": result.exif_date.strftime("%d/%m/%Y") if result.exif_date else None,
            "discrepancia_exif_dias": result.exif_discrepancy_days,
            "requiere_revision": result.risk_label != "LOW",
            "estado_guardado": visit.status,
            "novedad_categoria": visit.ai_category,
            "novedad_prioridad": visit.ai_priority,
            "novedad_resumen": visit.ai_summary,
            "motivos": motivos,
            "recomendacion": recomendacion,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante el análisis: {str(e)}")
    finally:
        session.close()
        temp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
