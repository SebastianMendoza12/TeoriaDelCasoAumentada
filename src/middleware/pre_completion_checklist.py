"""
pre_completion_checklist.py
PreCompletionChecklistMiddleware

Basado en el Capítulo 8.4 / 17.10 de deep_agents_harness_v3.pdf.

Propósito: interceptar el momento previo a dar por finalizado el flujo y
verificar que existan los artefactos mínimos exigidos por el enunciado
del proyecto (E4-E8) y que las métricas de calidad superen los umbrales
definidos en config.py. No detiene la ejecución del grafo (ya terminó),
pero produce un veredicto auditable que queda en checklist.json y se
muestra en el dashboard (sección "Alertas y Auditoría").
"""

import datetime
from src.state import CaseState
from src.config import UMBRAL_CALIDAD_AUDITOR

# Artefactos que el enunciado exige como entregables mínimos (E4-E7)
REQUIRED_ARTIFACTS = ["matriz_hpn", "grafo", "metricas", "escenarios"]

MIN_SCORES = {
    "score_calidad_auditor": UMBRAL_CALIDAD_AUDITOR,
}

# El enunciado exige al menos 4 escenarios simulados (E7, Cuadro 5)
MIN_ESCENARIOS = 4


def _artefacto_presente(estado: CaseState, nombre: str) -> bool:
    valor = estado.get(nombre)
    if isinstance(valor, dict):
        return bool(valor)
    if isinstance(valor, list):
        return len(valor) > 0
    return bool(valor)


def aplicar_checklist(estado: CaseState) -> dict:
    """
    Punto de entrada principal. Se llama al final de graph.py, después
    de que el grafo de LangGraph terminó de ejecutarse.
    """
    items_aprobados: list[str] = []
    items_fallidos: list[str] = []

    # 1. Artefactos mínimos generados
    for artefacto in REQUIRED_ARTIFACTS:
        if _artefacto_presente(estado, artefacto):
            items_aprobados.append(f"Artefacto '{artefacto}' generado")
        else:
            items_fallidos.append(f"Falta artefacto obligatorio: '{artefacto}'")

    # 2. Cada fila HPN debe tener fuente_expediente (trazabilidad mínima)
    matriz = estado.get("matriz_hpn", [])
    sin_fuente = [f.get("id") for f in matriz if not f.get("fuente_expediente")]
    if matriz and not sin_fuente:
        items_aprobados.append("Todas las filas HPN tienen fuente_expediente")
    elif matriz:
        items_fallidos.append(f"Filas HPN sin fuente verificable: {sin_fuente}")
    else:
        items_fallidos.append("La matriz HPN está vacía")

    # 3. El agente auditor corrió y devolvió un score
    score_auditor = estado.get("reporte_auditoria", {}).get("score_calidad")
    if score_auditor is not None:
        items_aprobados.append(f"Auditor ejecutado (score_calidad={score_auditor})")
        if score_auditor < MIN_SCORES["score_calidad_auditor"]:
            items_fallidos.append(
                f"Score de auditoría {score_auditor} por debajo del umbral "
                f"mínimo ({MIN_SCORES['score_calidad_auditor']})"
            )
    else:
        items_fallidos.append("El agente auditor no produjo 'score_calidad'")

    # 4. Mínimo de escenarios simulados exigido por el enunciado (E7)
    n_escenarios = len(estado.get("escenarios", []))
    if n_escenarios >= MIN_ESCENARIOS:
        items_aprobados.append(
            f"{n_escenarios} escenarios simulados (mínimo {MIN_ESCENARIOS})"
        )
    else:
        items_fallidos.append(
            f"Solo {n_escenarios} escenarios simulados (mínimo {MIN_ESCENARIOS})"
        )

    # 5. No deben quedar errores acumulados sin resolver en las trazas
    errores = estado.get("errores", [])
    if not errores:
        items_aprobados.append("Sin errores acumulados en las trazas de ejecución")
    else:
        items_fallidos.append(
            f"{len(errores)} error(es) registrados durante la ejecución"
        )

    aprobado = len(items_fallidos) == 0
    resultado = {
        "aprobado": aprobado,
        "razon_bloqueo": "; ".join(items_fallidos) if items_fallidos else "",
        "items_aprobados": items_aprobados,
        "items_fallidos": items_fallidos,
        "timestamp": datetime.datetime.now().isoformat(),
    }

    if aprobado:
        print("[PreCompletionChecklist]  ✓  APROBADO — artefactos mínimos generados.")
    else:
        print(f"[PreCompletionChecklist]  ✗  BLOQUEADO — {len(items_fallidos)} falla(s):")
        for item in items_fallidos:
            print(f"    - {item}")

    return resultado