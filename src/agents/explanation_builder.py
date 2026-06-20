"""
explanation_builder.py — Agente 12: ExplanationBuilder
Tipo: LLM (Groq)
Basado en: Capítulo 19 del documento deep_agents_harness_v3.pdf

Propósito: generar explicaciones legibles para el abogado de POR QUÉ
el sistema tomó cada decisión relevante. No es un resumen — es trazabilidad
narrativa: "el sistema marcó esta fila como vacio_critico PORQUE no
encontró prueba en los fragmentos frag-003 a frag-007."

Dice:
  "El ExplanationBuilder transforma el rastro de decisiones del agente
   en lenguaje natural accesible para el usuario final. Cada explicación
   debe referenciar la fuente que motivó la decisión, no solo describirla."
"""

import json
import datetime
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from src.state import CaseState
from src.config import GROQ_API_KEY, LLM_MODEL, LLM_TEMP

PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Eres el Agente ExplanationBuilder de un sistema de análisis jurídico.

Tu tarea es generar explicaciones en lenguaje natural que justifiquen
las decisiones más importantes tomadas por el sistema.

PROPÓSITO: El abogado debe entender POR QUÉ el sistema asignó cada estado,
riesgo o acción — no solo QUÉ decidió. Cada explicación debe referenciar
la fuente (frag_id, página o prueba específica) que motivó la decisión.

TIPOS DE EXPLICACIÓN a generar:
1. Por qué una fila HPN tiene el estado que tiene.
2. Por qué una prueba tiene la fuerza que tiene.
3. Por qué el sistema marcó ciertos vacíos como críticos.
4. Por qué el auditor asignó ese score de calidad.
5. Por qué el semáforo del caso es el que es.

REGLAS:
- Usa lenguaje claro, sin tecnicismos de programación.
- Siempre cita la fuente (frag_id, página, ID de prueba o ID de hecho).
- No inventes justificaciones. Si no hay fuente clara, dilo.
- Máximo 2 oraciones por explicación.

Devuelve ÚNICAMENTE JSON válido, sin texto adicional:
{{
  "explicaciones": [
    {{
      "tipo": "estado_fila | fuerza_prueba | vacio_critico | score_auditor | semaforo",
      "referencia": "HPN-001 | P002 | H003",
      "decision": "lo que el sistema decidió",
      "razon": "por qué lo decidió, con referencia a fuente específica",
      "fuente_citada": "frag-003 | página 4 | P002"
    }}
  ]
}}"""),
    ("human", """Matriz HPN:
{matriz_resumen}

Reporte del auditor:
{reporte_auditor}

Semáforo del caso: {semaforo}
Score de calidad: {score}

Genera explicaciones para las decisiones más importantes del sistema."""),
])


def explanation_builder_node(state: CaseState) -> dict:
    print("[explanation_builder]  Generando explicaciones de decisiones...")

    matriz   = state.get("matriz_hpn", [])
    reporte  = state.get("reporte_auditoria", {})
    errores  = []

    # Semáforo viene del dashboard_data si existe, o se calcula
    metricas_hpn = state.get("metricas", {}).get("hpn", {})
    cob_prob = metricas_hpn.get("cobertura_probatoria", 0)
    cob_norm = metricas_hpn.get("cobertura_normativa", 0)
    vacios   = metricas_hpn.get("vacios_criticos", 0)
    total    = metricas_hpn.get("total_filas", 1)
    score    = reporte.get("score_calidad", 0)

    pct_vacios = vacios / max(total, 1)
    score_cob  = (cob_prob + cob_norm) / 2
    if score_cob >= 0.70 and pct_vacios <= 0.20:
        semaforo = "verde"
    elif score_cob >= 0.50 and pct_vacios <= 0.40:
        semaforo = "amarillo"
    else:
        semaforo = "rojo"

    # Resumen de la matriz para el prompt
    matriz_resumen = [
        {
            "id":               f.get("id"),
            "elemento_juridico": f.get("elemento_juridico"),
            "estado":           f.get("estado"),
            "riesgo":           f.get("riesgo"),
            "n_pruebas":        len(f.get("pruebas", [])),
            "n_normas":         len(f.get("normas", [])),
            "contradicciones":  len(f.get("contradicciones", [])),
            "fuente":           f.get("fuente_expediente", {}).get("frag_id", "?"),
        }
        for f in matriz
    ]

    try:
        llm = ChatGroq(api_key=GROQ_API_KEY, model=LLM_MODEL, temperature=LLM_TEMP)
        chain = PROMPT | llm

        respuesta = chain.invoke({
            "matriz_resumen":  json.dumps(matriz_resumen, ensure_ascii=False, indent=2),
            "reporte_auditor": json.dumps(reporte, ensure_ascii=False, indent=2),
            "semaforo":        semaforo,
            "score":           score,
        })
        contenido = respuesta.content.strip()
        if contenido.startswith("```"):
            contenido = contenido.split("```")[1]
            if contenido.startswith("json"):
                contenido = contenido[4:]

        datos = json.loads(contenido)

    except json.JSONDecodeError as e:
        errores.append(f"Error parseando JSON del explanation_builder: {e}")
        datos = {"explicaciones": []}
    except Exception as e:
        errores.append(f"Error en explanation_builder: {e}")
        datos = {"explicaciones": []}

    explicaciones = datos.get("explicaciones", [])
    print(f"[explanation_builder]  ✓  {len(explicaciones)} explicaciones generadas")

    traza = {
        "agente":    "explanation_builder",
        "tipo":      "llm_groq",
        "modelo":    LLM_MODEL,
        "timestamp": datetime.datetime.now().isoformat(),
        "explicaciones_generadas": len(explicaciones),
        "errores":   errores,
    }

    return {
        "explicaciones": explicaciones,
        "trazas":        [traza],
        "errores":       errores,
    }