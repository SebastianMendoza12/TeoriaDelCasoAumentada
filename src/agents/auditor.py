"""
auditor.py — Agente 10: Auditor de Fuentes y Trazabilidad
Tipo: LLM (Groq) — opera SEPARADO del agente que construyó la matriz
Función: Verifica fuentes, coherencia, duplicados, claims sin soporte.
         Produce score de calidad y alertas accionables.
Entrada: matriz_hpn, segmentos, trazas
Salida:  reporte_auditoria, revision_humana_requerida
"""

import json
import datetime
from langchain_core.prompts import ChatPromptTemplate
from src.state import CaseState
from src.config import UMBRAL_CALIDAD_AUDITOR
from src.llm_client import invoke_llm

PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Eres el Agente Auditor INDEPENDIENTE de un sistema de análisis jurídico.

Tu función es CRÍTICA: verificar la calidad y trazabilidad de la Matriz HPN.
Eres independiente del agente que construyó la matriz — no tienes sesgo de confirmación.

VERIFICACIONES OBLIGATORIAS:
1. Filas sin fuente_expediente verificable.
2. Normas marcadas como "expediente" que no aparecen en los fragmentos disponibles.
3. Pruebas marcadas como "soporta" con fuerza < 0.3 (soporte débil presentado como fuerte).
4. Estado "completo" sin prueba real de soporte.
5. Contradicciones no resueltas que aumentan el riesgo litigioso.
6. Filas duplicadas o con elemento jurídico demasiado vago.
7. Claims sin ningún frag_id de origen.

SCORE DE CALIDAD (0.0 a 1.0):
- 1.0: Toda fila tiene fuente, prueba real y norma verificable.
- 0.7–0.9: Mayoría correcta, algunos vacíos menores.
- 0.5–0.7: Vacíos importantes o inconsistencias moderadas.
- < 0.5: Problemas graves de trazabilidad o coherencia.

Devuelve ÚNICAMENTE JSON válido, sin texto adicional:
{{
  "score_calidad": 0.82,
  "alertas": [
    {{
      "tipo": "sin_fuente | norma_no_verificable | soporte_debil | estado_incorrecto | contradiccion | duplicado",
      "fila_hpn": "HPN-003",
      "descripcion": "descripción concreta del problema",
      "severidad": "info | advertencia | critico"
    }}
  ],
  "filas_aprobadas": ["HPN-001", "HPN-002"],
  "filas_con_problemas": ["HPN-003"],
  "recomendaciones_criticas": [
    "Obtener frag_id de origen para HPN-003 antes de usar en memorial"
  ],
  "requiere_revision_humana": true
}}"""),
    ("human", """Matriz HPN a auditar:
{matriz}

Fragmentos disponibles del expediente (para verificar fuentes):
{fragmentos_resumen}

Trazas de los agentes:
{trazas_resumen}"""),
])


def auditor_node(state: CaseState) -> dict:
    print("[auditor]  Verificando fuentes y trazabilidad...")

    matriz    = state.get("matriz_hpn", [])
    segmentos = state.get("segmentos", [])
    trazas    = state.get("trazas", [])
    errores   = []
    llm_meta = {"proveedor": "no_ejecutado", "modelo": "sin_modelo"}

    # Resumen de fragmentos (solo primeras líneas de cada página)
    fragmentos_resumen = "\n".join(
        f"[{s['frag_id']} p.{s['pagina']}]: {s['texto'][:150]}..."
        for s in segmentos[:10]
    )

    # Resumen de trazas
    trazas_resumen = json.dumps(
        [{"agente": t.get("agente"), "errores": t.get("errores", [])} for t in trazas],
        ensure_ascii=False,
        indent=2,
    )

    try:
        respuesta, llm_meta = invoke_llm(PROMPT, {
            "matriz":            json.dumps(matriz, ensure_ascii=False, indent=2),
            "fragmentos_resumen": fragmentos_resumen,
            "trazas_resumen":    trazas_resumen,
        })
        contenido = respuesta.content.strip()
        if contenido.startswith("```"):
            contenido = contenido.split("```")[1]
            if contenido.startswith("json"):
                contenido = contenido[4:]

        reporte = json.loads(contenido)

    except json.JSONDecodeError as e:
        errores.append(f"Error parseando JSON del auditor: {e}")
        reporte = {
            "score_calidad": 0.5,
            "alertas": [],
            "requiere_revision_humana": True,
        }
    except Exception as e:
        errores.append(f"Error en auditor: {e}")
        reporte = {
            "score_calidad": 0.5,
            "alertas": [],
            "requiere_revision_humana": True,
        }

    # Agregar timestamp al reporte
    reporte["timestamp"] = datetime.datetime.now().isoformat()

    score          = reporte.get("score_calidad", 0.5)
    n_alertas      = len(reporte.get("alertas", []))
    rev_requerida  = score < UMBRAL_CALIDAD_AUDITOR or reporte.get("requiere_revision_humana", True)

    print(f"[auditor]  ✓  score_calidad={score} | alertas={n_alertas} | "
          f"revision_humana={'SÍ' if rev_requerida else 'NO'}")

    traza = {
        "agente":    "auditor",
        "tipo":      f"llm_{llm_meta['proveedor']}_independiente",
        "modelo":    llm_meta["modelo"],
        "timestamp": datetime.datetime.now().isoformat(),
        "score_calidad": score,
        "alertas_generadas": n_alertas,
        "revision_requerida": rev_requerida,
        "errores":   errores,
    }

    return {
        "reporte_auditoria":        reporte,
        "revision_humana_requerida": rev_requerida,
        "trazas":                   [traza],
        "errores":                  errores,
    }
