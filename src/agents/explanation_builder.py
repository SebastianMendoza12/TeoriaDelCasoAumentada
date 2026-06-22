"""
explanation_builder.py — Agente 12: ExplanationBuilder (+ verificación inline)
Tipo: LLM (Groq) + verificación determinística en el mismo paso
Basado en: Capítulos 19-20 del documento deep_agents_harness_v3.pdf

Propósito: generar explicaciones legibles para el abogado de POR QUÉ
el sistema tomó cada decisión relevante, y verificarlas de inmediato
contra las fuentes reales del expediente.

NOTA DE DISEÑO (fix aplicado): originalmente la verificación corría en
un nodo de LangGraph separado (explanation_verifier), leyendo
state["explicaciones"] escrito por este nodo. En la práctica esa
propagación entre nodos resultaba en una lista vacía al llegar al
verificador, aunque el builder sí generaba explicaciones (confirmado
con output/explicaciones.json quedando en [] pese al log "6
explicaciones generadas"). Para eliminar esa dependencia frágil, la
verificación ahora se ejecuta aquí mismo, en el mismo return de
Python, sin pasar por otro paso del grafo. La función pura
`verificar_explicaciones` sigue siendo la misma e independiente del
LLM — solo cambió DÓNDE se llama, no CÓMO verifica.
"""

import json
import datetime
from langchain_core.prompts import ChatPromptTemplate
from src.state import CaseState
from src.agents.explanation_verifier import verificar_explicaciones
from src.config import OUTPUT_DIR
from src.llm_client import invoke_llm

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

    matriz    = state.get("matriz_hpn", [])
    segmentos = state.get("segmentos", [])
    reporte   = state.get("reporte_auditoria", {})
    errores   = []
    llm_meta = {"proveedor": "no_ejecutado", "modelo": "sin_modelo"}

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
        respuesta, llm_meta = invoke_llm(PROMPT, {
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

    traza_builder = {
        "agente":    "explanation_builder",
        "tipo":      f"llm_{llm_meta['proveedor']}",
        "modelo":    llm_meta["modelo"],
        "timestamp": datetime.datetime.now().isoformat(),
        "explicaciones_generadas": len(explicaciones),
        "errores":   errores,
    }

    # ── Verificación INLINE (antes era un nodo separado del grafo) ───────
    print("[explanation_verifier]  Verificando explicaciones...")
    errores_verificacion = []
    try:
        reporte_explicabilidad = verificar_explicaciones(explicaciones, segmentos, matriz)
        print(f"[explanation_verifier]  ✓  "
              f"score_explicabilidad={reporte_explicabilidad['score_explicabilidad']} | "
              f"aprobadas={reporte_explicabilidad['explicaciones_aprobadas']} | "
              f"rechazadas={reporte_explicabilidad['explicaciones_rechazadas']}")
    except Exception as e:
        msg = f"Error en explanation_verifier: {e}"
        errores_verificacion.append(msg)
        print(f"[explanation_verifier]  ✗  {msg}")
        reporte_explicabilidad = {
            "total_explicaciones": len(explicaciones),
            "score_explicabilidad": 0,
            "error": msg,
        }

    traza_verificador = {
        "agente":    "explanation_verifier",
        "tipo":      "python_puro_determinisico",
        "timestamp": datetime.datetime.now().isoformat(),
        "score_explicabilidad": reporte_explicabilidad.get("score_explicabilidad", 0),
        "errores":   errores_verificacion,
    }

    metricas_actuales = state.get("metricas", {})
    metricas_actuales["explicabilidad"] = reporte_explicabilidad

    try:
        with open(OUTPUT_DIR / "explicaciones.json", "w", encoding="utf-8") as f:
            json.dump({
                "case_id":       state.get("case_id"),
                "timestamp":     datetime.datetime.now().isoformat(),
                "explicaciones": explicaciones,
            }, f, ensure_ascii=False, indent=2)
        print("[explanation_builder]  💾  explicaciones.json")
    except Exception as e:
        errores.append(f"No se pudo guardar explicaciones.json: {e}")

    return {
        "explicaciones": explicaciones,
        "metricas":      metricas_actuales,
        "trazas":        [traza_builder, traza_verificador],
        "errores":       errores + errores_verificacion,
    }
