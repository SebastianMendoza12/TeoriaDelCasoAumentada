"""
simulator.py — Agente 9: Simulador de Escenarios Procesales
Tipo: LLM (Groq) + cálculo determinístico antes/después
Función: Perturba la matriz y la red para simular escenarios S1–S4.
Entrada: matriz_hpn, metricas, pruebas
Salida:  escenarios
"""

import json
import datetime
import copy
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from src.state import CaseState
from src.tools.hpn_tools import calcular_metricas_hpn
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
                       "que podría enervar las pretensiones principales.",
    },
    {
        "id":     "S3",
        "nombre": "Testigo contradictorio",
        "descripcion": "Se incorpora una nueva prueba testimonial que contradice "
                       "el hecho principal de la teoría del caso.",
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
sobre la teoría del caso.

IMPORTANTE:
- NO predices el resultado del fallo judicial.
- Analizas efectos ESTRUCTURALES sobre la teoría: qué hechos pierden soporte,
  qué rutas argumentativas se debilitan, qué requiere refuerzo.
- Declara siempre incertidumbre. Todo escenario requiere revisión humana.

Devuelve ÚNICAMENTE JSON válido, sin texto adicional:
{{
  "hechos_afectados": ["H001", "H003"],
  "filas_hpn_impactadas": ["HPN-001", "HPN-003"],
  "rutas_debilitadas": ["descripción de la ruta que pierde soporte"],
  "nivel_impacto": "bajo | medio | alto | critico",
  "accion_sugerida": "acción concreta que debe tomar el abogado",
  "incertidumbre": "nota de cautela sobre las limitaciones del análisis"
}}"""),
    ("human", """Escenario a simular:
{escenario}

Matriz HPN (resumen):
{matriz_resumen}

Métricas actuales:
{metricas}"""),
])


def _eliminar_prueba_mas_fuerte(matriz: list[dict]) -> list[dict]:
    """S1: Elimina la prueba con mayor fuerza de soporte."""
    prueba_max_fuerza = None
    fuerza_max = -1

    for fila in matriz:
        for prueba in fila.get("pruebas", []):
            if prueba.get("relacion") == "soporta":
                f = prueba.get("fuerza", 0)
                if f > fuerza_max:
                    fuerza_max = f
                    prueba_max_fuerza = prueba.get("id")

    if not prueba_max_fuerza:
        return matriz

    # Copia profunda para no modificar el estado original
    nueva_matriz = copy.deepcopy(matriz)
    for fila in nueva_matriz:
        fila["pruebas"] = [
            p for p in fila.get("pruebas", [])
            if p.get("id") != prueba_max_fuerza
        ]
        # Degradar estado si queda sin pruebas
        if not fila["pruebas"] and fila.get("estado") == "completo":
            fila["estado"] = "vacio_critico"
            fila["riesgo"] = "critico"

    return nueva_matriz, prueba_max_fuerza


def simulator_node(state: CaseState) -> dict:
    print("[simulator]  Ejecutando escenarios de perturbación...")

    matriz   = state.get("matriz_hpn", [])
    metricas = state.get("metricas", {})
    errores  = []

    llm   = ChatGroq(api_key=GROQ_API_KEY, model=LLM_MODEL, temperature=0.1)
    chain = PROMPT_ESCENARIO | llm

    metricas_originales = metricas.get("hpn", {})
    escenarios_resultado = []

    matriz_resumen = [
        {
            "id":               f.get("id"),
            "elemento_juridico": f.get("elemento_juridico"),
            "estado":           f.get("estado"),
            "riesgo":           f.get("riesgo"),
        }
        for f in matriz
    ]

    for escenario in ESCENARIOS_BASE:
        print(f"[simulator]    → Simulando {escenario['id']}: {escenario['nombre']}")

        # Calcular métricas DESPUÉS de la perturbación (S1 tiene lógica especial)
        metricas_despues = {}
        prueba_eliminada = None

        if escenario["id"] == "S1" and matriz:
            try:
                resultado_s1 = _eliminar_prueba_mas_fuerte(matriz)
                if isinstance(resultado_s1, tuple):
                    matriz_perturbada, prueba_eliminada = resultado_s1
                else:
                    matriz_perturbada = resultado_s1
                metricas_despues = calcular_metricas_hpn(matriz_perturbada)
            except Exception as e:
                errores.append(f"Error calculando S1: {e}")

        # Análisis cualitativo del LLM
        try:
            respuesta = chain.invoke({
                "escenario":     json.dumps(escenario, ensure_ascii=False),
                "matriz_resumen": json.dumps(matriz_resumen, ensure_ascii=False, indent=2),
                "metricas":      json.dumps(metricas_originales, ensure_ascii=False, indent=2),
            })
            contenido = respuesta.content.strip()
            if contenido.startswith("```"):
                contenido = contenido.split("```")[1]
                if contenido.startswith("json"):
                    contenido = contenido[4:]
            analisis = json.loads(contenido)
        except Exception as e:
            errores.append(f"Error en análisis LLM de {escenario['id']}: {e}")
            analisis = {
                "hechos_afectados": [],
                "nivel_impacto": "desconocido",
                "accion_sugerida": "Revisar manualmente",
                "incertidumbre": "Error en análisis automático",
            }

        escenarios_resultado.append({
            "id":                  escenario["id"],
            "nombre":              escenario["nombre"],
            "supuesto_explicito":  escenario["descripcion"],
            "prueba_eliminada_s1": prueba_eliminada,
            "metricas_antes":      metricas_originales,
            "metricas_despues":    metricas_despues,
            "analisis":            analisis,
            "revision_humana_requerida": True,
            "timestamp":           datetime.datetime.now().isoformat(),
        })

    print(f"[simulator]  ✓  {len(escenarios_resultado)} escenarios simulados")

    traza = {
        "agente":    "simulator",
        "tipo":      "llm_groq + calculos_deterministas",
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
