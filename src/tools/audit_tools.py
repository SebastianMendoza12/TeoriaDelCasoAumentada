"""
audit_tools.py
Herramientas mínimas de auditoría y trazabilidad.
Sin LLM — determinísticas y reproducibles.
Listadas en Sección 10.6 del enunciado: registrar_traza,
verificar_no_alucinacion.
"""

import hashlib
import datetime
import json
from pathlib import Path
from src.config import OUTPUT_TRAZAS


def registrar_traza(
    agente: str,
    accion: str,
    entrada: dict,
    salida: dict,
    herramienta: str = "",
    errores: list = None,
) -> dict:
    """
    Registra un evento de traza estructurado en trazas.jsonl.
    Incluye hash de entrada y salida para detectar repeticiones.
    """
    hash_entrada = hashlib.md5(
        json.dumps(entrada, sort_keys=True, default=str).encode()
    ).hexdigest()[:8]
    hash_salida = hashlib.md5(
        json.dumps(salida, sort_keys=True, default=str).encode()
    ).hexdigest()[:8]

    traza = {
        "agente":       agente,
        "accion":       accion,
        "herramienta":  herramienta,
        "timestamp":    datetime.datetime.now().isoformat(),
        "hash_entrada": hash_entrada,
        "hash_salida":  hash_salida,
        "errores":      errores or [],
    }

    try:
        with open(OUTPUT_TRAZAS, "a", encoding="utf-8") as f:
            f.write(json.dumps(traza, ensure_ascii=False) + "\n")
    except Exception:
        pass  # No interrumpir el flujo si falla el log

    return traza


def verificar_no_alucinacion(
    afirmacion: str,
    fuentes: list[dict],
    umbral_similitud: float = 0.3,
) -> dict:
    """
    Verifica que una afirmación tenga respaldo en los fragmentos fuente.
    Usa búsqueda de palabras clave (sin LLM — determinístico).
    Si la similitud con alguna fuente supera el umbral, se considera
    respaldada. Si no, se marca como posible alucinación.

    Parámetros:
        afirmacion: texto de la afirmación a verificar.
        fuentes: lista de segmentos {"frag_id", "texto"}.
        umbral_similitud: fracción mínima de palabras de la afirmación
            que deben aparecer en alguna fuente para considerarla válida.

    Retorna:
        {"respaldada": bool, "frag_id_soporte": str|None,
         "score": float, "advertencia": str|None}
    """
    if not afirmacion or not fuentes:
        return {
            "respaldada": False,
            "frag_id_soporte": None,
            "score": 0.0,
            "advertencia": "Afirmación o fuentes vacías",
        }

    palabras = set(afirmacion.lower().split())
    # Filtrar stopwords básicas
    stopwords = {"el", "la", "los", "las", "un", "una", "de", "del", "en",
                 "y", "a", "que", "se", "no", "por", "con", "para", "es",
                 "su", "al", "lo", "le", "más", "o", "pero", "si"}
    palabras_relevantes = palabras - stopwords
    if not palabras_relevantes:
        return {"respaldada": True, "frag_id_soporte": None,
                "score": 1.0, "advertencia": None}

    mejor_score = 0.0
    mejor_frag = None

    for fuente in fuentes:
        texto_fuente = fuente.get("texto", "").lower()
        coincidencias = sum(1 for p in palabras_relevantes if p in texto_fuente)
        score = coincidencias / len(palabras_relevantes)
        if score > mejor_score:
            mejor_score = score
            mejor_frag = fuente.get("frag_id")

    respaldada = mejor_score >= umbral_similitud
    return {
        "respaldada": respaldada,
        "frag_id_soporte": mejor_frag if respaldada else None,
        "score": round(mejor_score, 3),
        "advertencia": None if respaldada else (
            f"Posible alucinación: score={mejor_score:.2f} < umbral={umbral_similitud}"
        ),
    }