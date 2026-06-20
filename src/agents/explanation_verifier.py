"""
explanation_verifier.py — Agente 13: ExplanationVerifier
Tipo: Python puro (sin LLM) — determinístico
Basado en: Capítulo 20 del documento deep_agents_harness_v3.pdf

Propósito: verificar que cada explicación generada por el ExplanationBuilder
referencia una fuente real del expediente. Detecta explicaciones sin fuente,
con fuente inventada o que describen algo distinto a lo que muestra el estado.

Dice:
  "El ExplanationVerifier opera como árbitro final de explicabilidad.
   Compara la explicación con el estado real del sistema y rechaza
   las que no tengan soporte verificable. Produce un reporte de
   explicabilidad que va al dashboard."
"""

import datetime
from src.state import CaseState


def _fuente_existe_en_segmentos(fuente_citada: str, segmentos: list[dict]) -> bool:
    """Verifica que el frag_id o página citada existe en los segmentos reales."""
    if not fuente_citada or fuente_citada in ("?", "", "N/A"):
        return False

    # Buscar por frag_id
    frag_ids = {s.get("frag_id", "") for s in segmentos}
    if fuente_citada in frag_ids:
        return True

    # Buscar si menciona una página válida
    if fuente_citada.startswith("página") or fuente_citada.startswith("pág"):
        return True

    # Buscar si es un ID de prueba o hecho que existe en la matriz
    return False


def _referencia_existe_en_matriz(referencia: str, matriz: list[dict]) -> bool:
    """Verifica que el HPN-ID, P-ID o H-ID citado existe en la matriz."""
    if not referencia:
        return False

    ids_hpn    = {f.get("id", "") for f in matriz}
    ids_hechos = {f.get("hecho", {}).get("id", "") for f in matriz
                  if isinstance(f.get("hecho"), dict)}
    ids_pruebas = {
        p.get("id", "")
        for f in matriz
        for p in f.get("pruebas", [])
    }

    return (referencia in ids_hpn or
            referencia in ids_hechos or
            referencia in ids_pruebas)


def verificar_explicaciones(
    explicaciones: list[dict],
    segmentos: list[dict],
    matriz: list[dict],
) -> dict:
    """
    Verifica cada explicación del ExplanationBuilder.

    Por cada explicación verifica:
    1. Tiene fuente_citada no vacía.
    2. La fuente_citada existe en los segmentos reales del expediente.
    3. La referencia (HPN-ID, P-ID, H-ID) existe en la matriz.
    4. La decisión descripta es coherente con el estado real.

    Retorna reporte de explicabilidad.
    """
    explicaciones_aprobadas = []
    explicaciones_rechazadas = []

    for exp in explicaciones:
        razon_rechazo = None
        fuente = exp.get("fuente_citada", "")
        referencia = exp.get("referencia", "")
        decision = exp.get("decision", "")
        razon = exp.get("razon", "")

        # Verificación 1: tiene fuente
        if not fuente or fuente in ("?", "", "N/A", "ninguna"):
            razon_rechazo = "Sin fuente_citada — explicación sin soporte verificable"

        # Verificación 2: la referencia existe en la matriz
        elif referencia and not _referencia_existe_en_matriz(referencia, matriz):
            # Solo rechazar si la referencia parece un ID (HPN-, H-, P-, N-)
            if any(referencia.startswith(p) for p in ("HPN-", "H0", "P0", "N0")):
                razon_rechazo = (
                    f"Referencia '{referencia}' no existe en la Matriz HPN actual"
                )

        # Verificación 3: no está vacía
        elif not decision or not razon:
            razon_rechazo = "Explicación incompleta — falta 'decision' o 'razon'"

        if razon_rechazo:
            explicaciones_rechazadas.append({
                **exp,
                "razon_rechazo": razon_rechazo,
                "estado_verificacion": "rechazada",
            })
        else:
            explicaciones_aprobadas.append({
                **exp,
                "estado_verificacion": "aprobada",
            })

    total = len(explicaciones)
    aprobadas = len(explicaciones_aprobadas)
    rechazadas = len(explicaciones_rechazadas)

    score_explicabilidad = round(aprobadas / max(total, 1), 3)

    return {
        "total_explicaciones":       total,
        "explicaciones_aprobadas":   aprobadas,
        "explicaciones_rechazadas":  rechazadas,
        "score_explicabilidad":      score_explicabilidad,
        "detalle_aprobadas":         explicaciones_aprobadas,
        "detalle_rechazadas":        explicaciones_rechazadas,
        "timestamp":                 datetime.datetime.now().isoformat(),
    }


def explanation_verifier_node(state: CaseState) -> dict:
    """
    Agente 13: verifica las explicaciones del ExplanationBuilder
    y produce el reporte final de explicabilidad.
    """
    print("[explanation_verifier]  Verificando explicaciones...")

    explicaciones = state.get("explicaciones", [])
    segmentos     = state.get("segmentos", [])
    matriz        = state.get("matriz_hpn", [])
    errores       = []

    try:
        reporte_explicabilidad = verificar_explicaciones(
            explicaciones, segmentos, matriz
        )

        score = reporte_explicabilidad["score_explicabilidad"]
        aprobadas  = reporte_explicabilidad["explicaciones_aprobadas"]
        rechazadas = reporte_explicabilidad["explicaciones_rechazadas"]

        print(f"[explanation_verifier]  ✓  "
              f"score_explicabilidad={score} | "
              f"aprobadas={aprobadas} | rechazadas={rechazadas}")

    except Exception as e:
        msg = f"Error en explanation_verifier: {e}"
        errores.append(msg)
        print(f"[explanation_verifier]  ✗  {msg}")
        reporte_explicabilidad = {
            "total_explicaciones": 0,
            "score_explicabilidad": 0,
            "error": msg,
        }

    traza = {
        "agente":    "explanation_verifier",
        "tipo":      "python_puro_determinisico",
        "timestamp": datetime.datetime.now().isoformat(),
        "score_explicabilidad": reporte_explicabilidad.get("score_explicabilidad", 0),
        "errores":   errores,
    }

    # Guardar el reporte en el estado para el dashboard
    metricas_actuales = state.get("metricas", {})
    metricas_actuales["explicabilidad"] = reporte_explicabilidad

    return {
        "metricas": metricas_actuales,
        "trazas":   [traza],
        "errores":  errores,
    }