"""
PhotoCheck AI - Risk Engine (Enterprise)
--------------------------------------------------------------
Motor de detección genérico: no le importa si el historial viene de
carpetas locales (detector/image_checker.py) o de la base de datos
(db/analyze_service.py) — solo recibe una lista de "items históricos"
con su ruta de archivo, apartamento y fecha, y calcula el riesgo.

Incluye:
  - pHash + ORB para similitud visual (con calibración de ruido/escala).
  - EXIF: compara la fecha real de la cámara contra la fecha declarada.
  - Fraude cruzado: si no hay match en el mismo apartamento, busca en
    TODOS los demás inmuebles.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import cv2
import imagehash
from PIL import Image, ExifTags

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".jfif"}
DATE_FORMAT = "%d/%m/%Y"

HASH_SIZE = 16
PHASH_STRONG_MATCH_DISTANCE = 5
PHASH_NOISE_FLOOR = 45.0

ORB_N_FEATURES = 800
ORB_HIGH_RISK_RATIO = 0.15

VISUAL_WEIGHT = 0.70
DATE_WEIGHT = 0.15
EXIF_WEIGHT = 0.15
DATE_MAX_SUSPICION_DAYS = 60

HIGH_RISK_THRESHOLD = 70
MEDIUM_RISK_THRESHOLD = 40

# Umbral para aceptar un match "cruzado" (de otro apartamento) como fraude real
CROSS_PROPERTY_REUSE_THRESHOLD = 60
CROSS_PROPERTY_SIMILARITY_THRESHOLD = 70


# =============================================================================
# DATOS
# =============================================================================

@dataclass
class PhotoMeta:
    """Datos declarados de la foto NUEVA que se está evaluando."""
    filename: str
    apartment: str | None
    date: datetime | None


@dataclass
class HistoricalItem:
    """Una foto histórica genérica (de carpeta o de la BD)."""
    identifier: str          # nombre de archivo, o id de visita en la BD
    path: Path
    apartment: str | None
    date: datetime | None


@dataclass
class VisualMatch:
    matched_id: str | None
    method: str
    phash_distance: int | None
    orb_ratio: float | None
    visual_similarity: float
    reuse_score: float
    reuse_evidence: str


@dataclass
class RiskResult:
    apartment: str | None
    matched_id: str | None
    matched_image: str | None      # etiqueta legible para mostrar en UI/API
    matched_apartment: str | None
    cross_property_fraud: bool
    method: str
    visual_score: float
    reuse_evidence: str
    date_score: float | None
    gap_days: int | None
    exif_date: datetime | None
    exif_discrepancy_days: int | None
    risk_score: int
    risk_label: str  # "LOW" | "MEDIUM" | "HIGH"


# =============================================================================
# EXIF
# =============================================================================

def extract_exif_metadata(image_path: Path) -> datetime | None:
    """Extrae la fecha real de captura (DateTimeOriginal) de los metadatos EXIF."""
    try:
        with Image.open(image_path) as img:
            exif_raw = img._getexif() if hasattr(img, "_getexif") else None
            if not exif_raw:
                return None
            exif = {ExifTags.TAGS.get(k, k): v for k, v in exif_raw.items() if k in ExifTags.TAGS}
            date_str = exif.get("DateTimeOriginal") or exif.get("DateTime")
            if date_str:
                try:
                    return datetime.strptime(str(date_str)[:10], "%Y:%m:%d")
                except ValueError:
                    return None
    except Exception as e:
        print(f"⚠️  No se pudieron leer metadatos EXIF de {image_path.name}: {e}")
    return None


# =============================================================================
# pHash + ORB
# =============================================================================

def compute_phash(image_path: Path) -> imagehash.ImageHash:
    with Image.open(image_path) as img:
        return imagehash.phash(img, hash_size=HASH_SIZE)


def phash_distance_to_similarity(distance: int) -> float:
    max_bits = HASH_SIZE * HASH_SIZE
    return round((1 - distance / max_bits) * 100, 2)


_orb = cv2.ORB_create(nfeatures=ORB_N_FEATURES)
_bf_matcher = cv2.BFMatcher(cv2.NORM_HAMMING)


def compute_orb_match_ratio(img_path_a: Path, img_path_b: Path) -> float:
    img_a = cv2.imread(str(img_path_a), cv2.IMREAD_GRAYSCALE)
    img_b = cv2.imread(str(img_path_b), cv2.IMREAD_GRAYSCALE)
    if img_a is None or img_b is None:
        return 0.0
    kp_a, des_a = _orb.detectAndCompute(img_a, None)
    kp_b, des_b = _orb.detectAndCompute(img_b, None)
    if des_a is None or des_b is None or len(kp_a) == 0 or len(kp_b) == 0:
        return 0.0
    matches = _bf_matcher.knnMatch(des_a, des_b, k=2)
    good = [m for m, n in (p for p in matches if len(p) == 2) if m.distance < 0.75 * n.distance]
    smaller = min(len(kp_a), len(kp_b))
    return len(good) / smaller if smaller else 0.0


def calculate_orb_reuse_score(orb_ratio: float) -> float:
    if orb_ratio <= 0:
        return 0.0
    return round(min(100.0, (orb_ratio / ORB_HIGH_RISK_RATIO) * 90), 2)


def classify_reuse_evidence(reuse_score: float) -> str:
    if reuse_score >= 70:
        return "ALTA"
    if reuse_score >= 40:
        return "MEDIA"
    return "BAJA"


def compute_visual_score(new_path: Path, candidates: dict[str, Path]) -> VisualMatch:
    if not candidates:
        return VisualMatch(None, "ninguno", None, None, 0.0, 0.0, "BAJA")

    new_hash = compute_phash(new_path)
    best_phash_id, best_phash_distance = None, None
    for identifier, path in candidates.items():
        try:
            distance = new_hash - compute_phash(path)
        except Exception as e:
            print(f"⚠️  Error procesando {identifier} (pHash): {e}")
            continue
        if best_phash_distance is None or distance < best_phash_distance:
            best_phash_distance, best_phash_id = distance, identifier

    if best_phash_distance is not None and best_phash_distance <= PHASH_STRONG_MATCH_DISTANCE:
        return VisualMatch(
            matched_id=best_phash_id, method="pHash",
            phash_distance=best_phash_distance, orb_ratio=None,
            visual_similarity=phash_distance_to_similarity(best_phash_distance),
            reuse_score=100.0, reuse_evidence="ALTA",
        )

    best_orb_id, best_orb_ratio = None, 0.0
    for identifier, path in candidates.items():
        try:
            ratio = compute_orb_match_ratio(new_path, path)
        except Exception as e:
            print(f"⚠️  Error procesando {identifier} (ORB): {e}")
            continue
        if ratio > best_orb_ratio:
            best_orb_ratio, best_orb_id = ratio, identifier

    raw_phash_similarity = phash_distance_to_similarity(best_phash_distance) if best_phash_distance is not None else 0.0
    phash_score = max(0.0, (raw_phash_similarity - PHASH_NOISE_FLOOR) / (100 - PHASH_NOISE_FLOOR) * 100)
    orb_reuse_score = calculate_orb_reuse_score(best_orb_ratio)

    if orb_reuse_score > phash_score:
        return VisualMatch(
            matched_id=best_orb_id, method="ORB",
            phash_distance=best_phash_distance, orb_ratio=best_orb_ratio,
            visual_similarity=round(min(100.0, best_orb_ratio * 100), 2),
            reuse_score=orb_reuse_score, reuse_evidence=classify_reuse_evidence(orb_reuse_score),
        )

    return VisualMatch(
        matched_id=best_phash_id, method="pHash",
        phash_distance=best_phash_distance, orb_ratio=best_orb_ratio,
        visual_similarity=round(raw_phash_similarity, 2),
        reuse_score=round(phash_score, 2), reuse_evidence=classify_reuse_evidence(phash_score),
    )


# =============================================================================
# EVALUACIÓN INTEGRAL (visual + fecha + EXIF + fraude cruzado)
# =============================================================================

def evaluate_against_history(
    new_path: Path,
    new_meta: PhotoMeta,
    history: list[HistoricalItem],
    label_fn: Callable[[HistoricalItem], str] | None = None,
) -> RiskResult:
    """
    'history' debe incluir TODO el historial disponible (de todos los
    apartamentos) para que la detección de fraude cruzado funcione.

    label_fn: cómo mostrar el item que hizo match (por defecto, su identifier).
    """
    label_fn = label_fn or (lambda item: item.identifier)
    exif_date = extract_exif_metadata(new_path)

    same_apartment_candidates = {
        item.identifier: item.path
        for item in history
        if new_meta.apartment and item.apartment == new_meta.apartment
    }

    visual = compute_visual_score(new_path, same_apartment_candidates)
    cross_property_fraud = False

    # Si no hubo match fuerte en el mismo apartamento, buscamos en los demás
    if visual.reuse_score < 70 and len(same_apartment_candidates) < len(history):
        other_candidates = {
            item.identifier: item.path
            for item in history
            if not new_meta.apartment or item.apartment != new_meta.apartment
        }
        global_visual = compute_visual_score(new_path, other_candidates)
        if (global_visual.reuse_score >= CROSS_PROPERTY_REUSE_THRESHOLD
                or global_visual.visual_similarity >= CROSS_PROPERTY_SIMILARITY_THRESHOLD):
            visual = global_visual
            cross_property_fraud = True

    matched_item = next((h for h in history if h.identifier == visual.matched_id), None)
    matched_apartment = matched_item.apartment if matched_item else new_meta.apartment

    date_score, gap_days = None, None
    if new_meta.date and matched_item and matched_item.date:
        gap_days = abs((new_meta.date - matched_item.date).days)
        date_score = min(100.0, (gap_days / DATE_MAX_SUSPICION_DAYS) * 100)

    exif_discrepancy_days, exif_score = None, 0.0
    if exif_date and new_meta.date:
        exif_discrepancy_days = abs((new_meta.date - exif_date).days)
        if exif_discrepancy_days > 1:
            exif_score = min(100.0, exif_discrepancy_days * 20.0)

    if date_score is None:
        base_risk = visual.reuse_score
    else:
        base_risk = visual.reuse_score * VISUAL_WEIGHT + date_score * DATE_WEIGHT + exif_score * EXIF_WEIGHT

    if cross_property_fraud:
        base_risk = max(base_risk, 95.0)

    risk_score = max(0, min(100, round(base_risk)))
    if risk_score >= HIGH_RISK_THRESHOLD:
        risk_label = "HIGH"
    elif risk_score >= MEDIUM_RISK_THRESHOLD:
        risk_label = "MEDIUM"
    else:
        risk_label = "LOW"

    return RiskResult(
        apartment=new_meta.apartment,
        matched_id=matched_item.identifier if matched_item else None,
        matched_image=label_fn(matched_item) if matched_item else None,
        matched_apartment=matched_apartment,
        cross_property_fraud=cross_property_fraud,
        method=visual.method,
        visual_score=visual.visual_similarity,
        reuse_evidence=visual.reuse_evidence,
        date_score=date_score,
        gap_days=gap_days,
        exif_date=exif_date,
        exif_discrepancy_days=exif_discrepancy_days,
        risk_score=risk_score,
        risk_label=risk_label,
    )
