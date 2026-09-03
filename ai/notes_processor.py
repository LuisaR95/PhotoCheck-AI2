"""
PhotoCheck AI - Clasificador de novedades (Fase 6)
--------------------------------------------------------------
Usa Claude para estructurar la novedad que escribe el operario en
texto libre (ej. "Se encontró una fuga de agua debajo del lavamanos")
en: categoría, prioridad sugerida y un resumen corto.

IMPORTANTE: la IA NUNCA decide nada por sí sola. Solo propone una
clasificación para que el supervisor la revise — igual que el
Risk Engine, esto es una sugerencia, no una decisión automática.

Si no hay ANTHROPIC_API_KEY configurada, o la llamada falla por
cualquier motivo, esta función devuelve None silenciosamente (con
una advertencia en consola) en vez de romper el resto del análisis.
La clasificación de novedades es un complemento, no algo crítico.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

CATEGORIAS_VALIDAS = ["Mantenimiento", "Limpieza", "Seguridad", "Otro"]
PRIORIDADES_VALIDAS = ["Baja", "Media", "Alta"]

MODEL = "claude-haiku-4-5-20251001"  # rápido y barato, ideal para clasificación simple

SYSTEM_PROMPT = f"""Eres un asistente que clasifica novedades reportadas por operarios \
de servicios de limpieza/mantenimiento en apartamentos.

Dado el texto de la novedad, responde ÚNICAMENTE con un objeto JSON válido, \
sin texto adicional, sin explicaciones, sin backticks de markdown, con esta forma exacta:

{{"categoria": "<una de estas: {", ".join(CATEGORIAS_VALIDAS)}>", \
"prioridad": "<una de estas: {", ".join(PRIORIDADES_VALIDAS)}>", \
"resumen": "<resumen de máximo 12 palabras>"}}
"""

_client = None


def _get_client():
    """Crea el cliente de Anthropic una sola vez (perezosamente)."""
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        from anthropic import Anthropic
        _client = Anthropic(api_key=api_key)
        return _client
    except Exception as e:
        print(f"⚠️  No se pudo inicializar el cliente de Anthropic: {e}")
        return None


def process_notes(notes: str | None) -> dict | None:
    """
    Clasifica la novedad escrita por el operario.

    Devuelve None si:
      - no hay texto de novedad,
      - no hay ANTHROPIC_API_KEY configurada,
      - la llamada a la API falla por cualquier razón.

    En caso de éxito, devuelve:
        {"categoria": "...", "prioridad": "...", "resumen": "..."}
    """
    if not notes or not notes.strip():
        return None

    client = _get_client()
    if client is None:
        print("⚠️  ANTHROPIC_API_KEY no configurada — se omite la clasificación de la novedad con IA.")
        return None

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": notes.strip()}],
        )
        raw_text = response.content[0].text.strip()

        # Por si el modelo agrega backticks de markdown a pesar de la instrucción
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        data = json.loads(raw_text)

        categoria = data.get("categoria")
        if categoria not in CATEGORIAS_VALIDAS:
            categoria = "Otro"

        prioridad = data.get("prioridad")
        if prioridad not in PRIORIDADES_VALIDAS:
            prioridad = "Media"

        resumen = str(data.get("resumen", "")).strip()[:200]

        return {"categoria": categoria, "prioridad": prioridad, "resumen": resumen}

    except Exception as e:
        print(f"⚠️  No se pudo clasificar la novedad con IA: {e}")
        return None
