"""
simulator.py — Agente 9: Simulador de Escenarios Procesales
Tipo: LLM (Groq) + perturbación y cálculo determinísticos
Función: Perturba REALMENTE la matriz y la red (no solo describe el
efecto en texto) para los 4 escenarios mínimos S1-S4, y recalcula
métricas HPN y de red antes/después de cada perturbación, según el
flujo mínimo de la Sección 7.1 del enunciado.
Entrada: matriz_hpn, metricas, actores, normas, cronologia
Salida:  escenarios
"""

import json
import datetime
import copy
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from src.state import CaseState
from src.tools.hpn_tools import calcular_metricas_hpn
from src.tools.graph_tools import construir_grafo, calcular_metricas_red
from src.config import GROQ_API_KEY, LLM_MODEL, LLM_TEMP

# Los 4 escenarios mínimos exigidos por el enunciado (Tabla 5)
ESCENARIOS_BASE = [
    {
        "id":     "S1",
        "nombre": "Exclusión de prueba crítica",
        "descripcion": "Se elimina la prueba con mayor fuerza de soporte de la matriz. "
                       "Simula que esa prueba es inadmitida o excluida por el juez.",
    },
    {
        "id":     "S2",
        "nombre": "Excepción probada",
        "descripcion": "Se activa una excepción de fuerza mayor, prescripción o caducidad "
                       "que bloquea las filas de mayor riesgo/controversia de la teoría del caso.",
    },
    {
        "id":     "S3",
        "nombre": "Testigo contradictorio",
        "descripcion": "Se incorpora una nueva prueba testimonial que contradice "
                       "el hecho mejor soportado de la teoría del caso.",
    },
    {
        "id":     "S4",
        "nombre": "Precedente distinguido",
        "descripcion": "El soporte jurisprudencial principal es distinguido por el juez "
                       "por diferencias fácticas con el caso en análisis.",
    },
]

PROMPT_ESCENARIO = ChatPromptTemplate.from_messages([
    ("system", """Eres el Agente Simulador de un sistema de análisis jurídico.

Tu tarea es analizar el impacto estratégico de un escenario de perturbación
sobre la teoría del caso, dado que la perturbación YA fue ejecutada de forma
determinística sobre la matriz y la red (no la ejecutas tú).

IMPORTANTE:
- NO predices el resultado del fallo judicial.
- Te basas en las métricas ANTES y DESPUÉS que se te entregan, que son reales.
- Declaras siempre incertidumbre. Todo escenario requiere revisión humana.

Devuelve ÚNICAMENTE JSON válido, sin texto adicional:
{{
  "hechos_afectados": ["H001", "H003"],
  "filas_hpn_impactadas": ["HPN-001", "HPN-003"],
  "rutas_debilitadas": ["descripción de la ruta que pierde soporte"],
  "nivel_impacto": "bajo | medio | alto | critico",
  "accion_sugerida": "acción concreta que debe tomar el abogado",
  "incertidumbre": "nota de cautela sobre las limitaciones del análisis"
}}"""),
    ("human", """Escenario simulado:
{escenario}

Elemento perturbado: {elemento_perturbado}

Métricas HPN antes:
{metricas_hpn_antes}

Métricas HPN después:
{metricas_hpn_despues}

Métricas de red antes:
{metricas_red_antes}

Métricas de red después:
{metricas_red_despues}"""),
])


# ── Perturbaciones deterministas (una por escenario) ──────────────────────

def _eliminar_prueba_mas_fuerte(matriz: list[dict]) -> tuple[list[dict], str | None]:
    """S1: elimina la prueba con mayor fuerza de soporte de toda la matriz."""
    prueba_max_fuerza, fuerza_max = None, -1
    for fila in matriz:
        for prueba in fila.get("pruebas", []):
            if prueba.get("relacion") == "soporta" and prueba.get("fuerza", 0) > fuerza_max:
                fuerza_max = prueba.get("fuerza", 0)
                prueba_max_fuerza = prueba.get("id")

    nueva_matriz = copy.deepcopy(matriz)
    if not prueba_max_fuerza:
        return nueva_matriz, None

    for fila in nueva_matriz:
        fila["pruebas"] = [p for p in fila.get("pruebas", []) if p.get("id") != prueba_max_fuerza]
        if not fila["pruebas"] and fila.get("estado") == "completo":
            fila["estado"] = "vacio_critico"
            fila["riesgo"] = "critico"
    return nueva_matriz, prueba_max_fuerza


def _activar_excepcion(matriz: list[dict]) -> tuple[list[dict], str | None]:
    """S2: activa una excepción que bloquea las filas más débiles/riesgosas."""
    nueva_matriz = copy.deepcopy(matriz)
    afectadas = []
    for fila in nueva_matriz:
        if fila.get("riesgo") in {"alto", "critico"} or fila.get("estado") in {"controvertido", "debil"}:
            fila["estado"] = "bloqueado"
            fila["riesgo"] = "critico"
            afectadas.append(fila.get("id"))
    return nueva_matriz, (", ".join(afectadas) if afectadas else None)


def _agregar_testigo_contradictorio(matriz: list[dict]) -> tuple[list[dict], str | None]:
    """S3: agrega una prueba testimonial que contradice el hecho mejor soportado."""
    nueva_matriz = copy.deepcopy(matriz)
    candidata, mejor_fuerza = None, -1
    for fila in nueva_matriz:
        if fila.get("estado") == "completo":
            fuerza_total = sum(
                p.get("fuerza", 0) for p in fila.get("pruebas", []) if p.get("relacion") == "soporta"
            )
            if fuerza_total > mejor_fuerza:
                mejor_fuerza, candidata = fuerza_total, fila

    if candidata is None:
        return nueva_matriz, None

    candidata.setdefault("pruebas", []).append({
        "id": "P-SIM-S3", "tipo": "testimonio",
        "descripcion": "Testigo contradictorio simulado",
        "relacion": "contradice", "fuerza": 0.6,
    })
    candidata["estado"] = "controvertido"
    if candidata.get("riesgo") in {"bajo", "medio"}:
        candidata["riesgo"] = "alto"
    return nueva_matriz, candidata.get("id")


def _distinguir_precedente(matriz: list[dict]) -> tuple[list[dict], str | None]:
    """S4: distingue el precedente de la fila que más normas/precedentes usa."""
    nueva_matriz = copy.deepcopy(matriz)
    candidata, mas_normas = None, -1
    for fila in nueva_matriz:
        n_normas = len(fila.get("normas", []))
        if n_normas > mas_normas:
            mas_normas, candidata = n_normas, fila

    if candidata is None or mas_normas <= 0:
        return nueva_matriz, None

    for norma in candidata.get("normas", []):
        norma["fuente"] = "precedente_distinguido"
    if candidata.get("estado") == "completo":
        candidata["estado"] = "debil"
    candidata["riesgo"] = "critico" if candidata.get("riesgo") in {"alto", "critico"} else "alto"
    return nueva_matriz, candidata.get("id")


PERTURBACIONES = {
    "S1": _eliminar_prueba_mas_fuerte,
    "S2": _activar_excepcion,
    "S3": _agregar_testigo_contradictorio,
    "S4": _distinguir_precedente,
}


def simulator_node(state: CaseState) -> dict:
    print("[simulator]  Ejecutando escenarios de perturbación...")

    matriz     = state.get("matriz_hpn", [])
    actores    = state.get("actores", [])
    normas     = state.get("normas", [])
    cronologia = state.get("cronologia", [])
    metricas   = state.get("metricas", {})
    errores    = []

    llm   = ChatGroq(api_key=GROQ_API_KEY, model=LLM_MODEL, temperature=0.1)
    chain = PROMPT_ESCENARIO | llm

    metricas_hpn_antes = metricas.get("hpn", {})
    metricas_red_antes = metricas.get("red", {})
    escenarios_resultado = []

    for escenario in ESCENARIOS_BASE:
        esc_id = escenario["id"]
        print(f"[simulator]    → Simulando {esc_id}: {escenario['nombre']}")

        perturbar = PERTURBACIONES.get(esc_id)
        matriz_perturbada, elemento_perturbado = (
            perturbar(matriz) if perturbar else (copy.deepcopy(matriz), None)
        )

        # ── Recalcular métricas HPN después de la perturbación ────────────
        metricas_hpn_despues = {}
        try:
            metricas_hpn_despues = calcular_metricas_hpn(matriz_perturbada)
        except Exception as e:
            errores.append(f"Error calculando métricas HPN de {esc_id}: {e}")

        # ── Recalcular métricas de RED después de la perturbación ─────────
        metricas_red_despues = {}
        try:
            G_despues = construir_grafo(matriz_perturbada, actores, normas, cronologia)
            metricas_red_despues = calcular_metricas_red(G_despues)
        except Exception as e:
            errores.append(f"Error calculando métricas de red de {esc_id}: {e}")

        # ── Análisis cualitativo del LLM, anclado a métricas reales ────────
        try:
            respuesta = chain.invoke({
                "escenario":            json.dumps(escenario, ensure_ascii=False),
                "elemento_perturbado":  elemento_perturbado or "ninguno identificado",
                "metricas_hpn_antes":   json.dumps(metricas_hpn_antes, ensure_ascii=False, indent=2),
                "metricas_hpn_despues": json.dumps(metricas_hpn_despues, ensure_ascii=False, indent=2),
                "metricas_red_antes":   json.dumps(metricas_red_antes, ensure_ascii=False, indent=2, default=str),
                "metricas_red_despues": json.dumps(metricas_red_despues, ensure_ascii=False, indent=2, default=str),
            })
            contenido = respuesta.content.strip()
            if contenido.startswith("```"):
                contenido = contenido.split("```")[1]
                if contenido.startswith("json"):
                    contenido = contenido[4:]
            analisis = json.loads(contenido)
        except Exception as e:
            errores.append(f"Error en análisis LLM de {esc_id}: {e}")
            analisis = {
                "hechos_afectados": [],
                "nivel_impacto": "desconocido",
                "accion_sugerida": "Revisar manualmente",
                "incertidumbre": "Error en análisis automático",
            }

        escenarios_resultado.append({
            "id":                   esc_id,
            "nombre":               escenario["nombre"],
            "supuesto_explicito":   escenario["descripcion"],
            "elemento_perturbado":  elemento_perturbado,
            # se conserva el nombre original para no romper el dashboard actual
            "prueba_eliminada_s1":  elemento_perturbado if esc_id == "S1" else None,
            "metricas_antes":       metricas_hpn_antes,
            "metricas_despues":     metricas_hpn_despues,
            "metricas_red_antes":   metricas_red_antes,
            "metricas_red_despues": metricas_red_despues,
            "analisis":             analisis,
            "revision_humana_requerida": True,
            "timestamp":            datetime.datetime.now().isoformat(),
        })

    print(f"[simulator]  ✓  {len(escenarios_resultado)} escenarios simulados "
          f"(perturbación real + métricas antes/después en los 4)")

    traza = {
        "agente":    "simulator",
        "tipo":      "perturbacion_deterministica + llm_groq",
        "modelo":    LLM_MODEL,
        "timestamp": datetime.datetime.now().isoformat(),
        "escenarios_simulados": len(escenarios_resultado),
        "errores":   errores,
    }

    return {
        "escenarios": escenarios_resultado,
        "trazas":     [traza],
        "errores":    errores,
    }