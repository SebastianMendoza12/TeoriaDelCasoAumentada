"""
loop_detection.py
LoopDetectionMiddleware

Basado en el Capítulo 8.5 y 17.11 del documento (deep_agents_harness_v3.pdf).

Propósito: detectar si un agente está en loop — llamando la misma
herramienta repetidamente, generando la misma salida, o si el grafo
lleva demasiados pasos sin avanzar.

Describe este patrón así:
  "El LoopDetectionMiddleware interrumpe ejecuciones que se repiten
   sin producir estado nuevo. Compara hashes de salida entre pasos
   consecutivos y corta si supera max_repetitions."
"""

import hashlib
import json
import datetime
from typing import Optional


# Configuración del detector
MAX_REPETICIONES_AGENTE = 3      # veces que un agente puede dar la misma salida
MAX_PASOS_SIN_AVANCE    = 5      # pasos consecutivos sin cambio de estado
MAX_TRAZAS_TOTALES      = 50     # límite absoluto de entradas en trazas


def _hash_salida(datos: object) -> str:
    """Genera hash de la salida de un agente para detectar repetición."""
    try:
        serializado = json.dumps(datos, sort_keys=True, ensure_ascii=False,
                                 default=str)
        return hashlib.md5(serializado.encode()).hexdigest()[:8]
    except Exception:
        return "hash_error"


def detectar_loops(trazas: list[dict]) -> dict:
    """
    Analiza las trazas acumuladas del sistema y detecta patrones de loop.

    Verifica:
    1. Agente que aparece más de MAX_REPETICIONES_AGENTE veces.
    2. Hash de salida idéntico en pasos consecutivos del mismo agente.
    3. Total de trazas excede MAX_TRAZAS_TOTALES.

    Retorna:
        {
            "loop_detectado": bool,
            "tipo": str | None,
            "agente_problema": str | None,
            "descripcion": str,
            "accion_sugerida": str,
            "timestamp": str
        }
    """
    if not trazas:
        return {
            "loop_detectado": False,
            "tipo": None,
            "agente_problema": None,
            "descripcion": "Sin trazas para analizar",
            "accion_sugerida": "Ninguna",
            "timestamp": datetime.datetime.now().isoformat(),
        }

    # ── Verificación 1: total de trazas ──────────────────────────────────────
    if len(trazas) > MAX_TRAZAS_TOTALES:
        return {
            "loop_detectado": True,
            "tipo": "trazas_excesivas",
            "agente_problema": None,
            "descripcion": (
                f"El sistema acumuló {len(trazas)} trazas "
                f"(máximo: {MAX_TRAZAS_TOTALES}). "
                "Posible loop o ejecución repetida sin limpiar estado."
            ),
            "accion_sugerida": "Reiniciar el estado y ejecutar desde cero.",
            "timestamp": datetime.datetime.now().isoformat(),
        }

    # ── Verificación 2: agente repetido ──────────────────────────────────────
    conteo_agentes: dict[str, int] = {}
    for traza in trazas:
        agente = traza.get("agente", "desconocido")
        conteo_agentes[agente] = conteo_agentes.get(agente, 0) + 1

    for agente, conteo in conteo_agentes.items():
        if conteo > MAX_REPETICIONES_AGENTE:
            return {
                "loop_detectado": True,
                "tipo": "agente_repetido",
                "agente_problema": agente,
                "descripcion": (
                    f"El agente '{agente}' apareció {conteo} veces en trazas "
                    f"(máximo permitido: {MAX_REPETICIONES_AGENTE})."
                ),
                "accion_sugerida": (
                    f"Verificar condición de parada del agente '{agente}'. "
                    "Revisar si el grafo tiene un ciclo no intencional."
                ),
                "timestamp": datetime.datetime.now().isoformat(),
            }

    # ── Verificación 3: salidas idénticas consecutivas ────────────────────────
    hashes_por_agente: dict[str, list[str]] = {}
    for traza in trazas:
        agente = traza.get("agente", "desconocido")
        hash_val = _hash_salida({
            k: v for k, v in traza.items()
            if k not in ("timestamp", "errores")
        })
        if agente not in hashes_por_agente:
            hashes_por_agente[agente] = []
        hashes_por_agente[agente].append(hash_val)

    for agente, hashes in hashes_por_agente.items():
        if len(hashes) >= 2:
            # Detectar si los últimos 2 hashes son iguales
            if hashes[-1] == hashes[-2]:
                return {
                    "loop_detectado": True,
                    "tipo": "salida_identica",
                    "agente_problema": agente,
                    "descripcion": (
                        f"El agente '{agente}' produjo salidas idénticas "
                        "en dos ejecuciones consecutivas. "
                        "Posible loop sin progreso de estado."
                    ),
                    "accion_sugerida": (
                        "Verificar si el agente depende de una herramienta "
                        "que no avanza o de datos que no cambian entre pasos."
                    ),
                    "timestamp": datetime.datetime.now().isoformat(),
                }

    # ── Sin loop detectado ────────────────────────────────────────────────────
    return {
        "loop_detectado": False,
        "tipo": None,
        "agente_problema": None,
        "descripcion": (
            f"Sin loops detectados. "
            f"{len(trazas)} trazas analizadas, "
            f"{len(conteo_agentes)} agentes distintos."
        ),
        "accion_sugerida": "Ninguna — el sistema avanzó correctamente.",
        "timestamp": datetime.datetime.now().isoformat(),
    }


def aplicar_loop_detection(trazas: list[dict]) -> dict:
    """
    Punto de entrada principal. Se llama durante la ejecución del grafo.
    Imprime resultado en consola y devuelve el diagnóstico.
    """
    resultado = detectar_loops(trazas)

    if resultado["loop_detectado"]:
        print(f"\n⚠️  [LoopDetection] LOOP DETECTADO")
        print(f"    Tipo:    {resultado['tipo']}")
        print(f"    Agente:  {resultado['agente_problema']}")
        print(f"    Detalle: {resultado['descripcion']}")
        print(f"    Acción:  {resultado['accion_sugerida']}\n")
    else:
        print(f"[LoopDetection] ✓  {resultado['descripcion']}")

    return resultado