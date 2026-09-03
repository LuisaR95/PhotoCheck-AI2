"""
PhotoCheck AI - Modelos de base de datos
--------------------------------------------------------------
properties
    id, name (ej. "A-101"), address

visits
    id, property_id, visit_date, image_path, notes
    risk_score, status              -> resultado del Risk Engine
    method                          -> "pHash" | "ORB" | "ninguno"
    visual_score                    -> similitud visual 0-100
    cross_property_fraud            -> True si la foto venía de OTRO apartamento
    matched_visit_id                -> a qué visita anterior hizo match (auto-referencia)
    exif_date, exif_discrepancy_days -> validación de la fecha real de cámara
    created_at                      -> auditoría
"""

from sqlalchemy import (
    Boolean, Column, Integer, String, Date, Text, ForeignKey, DateTime, func
)
from sqlalchemy.orm import relationship

from db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    role = Column(String(20), nullable=False)  # "operario" | "administrador"

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    address = Column(String(255), nullable=True)

    visits = relationship("Visit", back_populates="property", order_by="Visit.visit_date", foreign_keys="Visit.property_id")

    def __repr__(self):
        return f"<Property {self.name}>"


class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    visit_date = Column(Date, nullable=False)
    image_path = Column(String(500), nullable=False)
    notes = Column(Text, nullable=True)

    risk_score = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="PENDING_REVIEW")

    method = Column(String(20), nullable=True)
    visual_score = Column(Integer, nullable=True)
    cross_property_fraud = Column(Boolean, nullable=False, default=False)
    matched_visit_id = Column(Integer, ForeignKey("visits.id"), nullable=True)

    exif_date = Column(Date, nullable=True)
    exif_discrepancy_days = Column(Integer, nullable=True)

    # Clasificación de la novedad por IA (Fase 6) — siempre una SUGERENCIA,
    # nunca reemplaza la revisión humana.
    ai_category = Column(String(30), nullable=True)
    ai_priority = Column(String(20), nullable=True)
    ai_summary = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    property = relationship("Property", back_populates="visits", foreign_keys=[property_id])
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])

    def __repr__(self):
        return f"<Visit {self.id} property={self.property_id} score={self.risk_score}>"
