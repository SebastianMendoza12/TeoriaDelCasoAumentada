"""
probatorio.py — Agente 3: Probatorio
Tipo: LLM (Groq)
Función: Cataloga pruebas disponibles, detecta vacíos y contradicciones.
Entrada: hechos, segmentos
Salida:  pruebas, vacios
"""

import json
import datetime
from langchain_core.prompts import ChatPromptTemplate
from src.state import CaseState
from src.tools.pdf_tools import texto_resumido
from src.config import MAX_SEGMENTOS_POR_LLAMADA
from src.llm_client import invoke_llm

PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Eres el Agente Probatorio de un sistema de análisis jurídico.

Tu tarea es identificar todas las PRUEBAS mencionadas en el expediente y detectar VACÍOS probatorios.

TIPOS DE PRUEBA: documento, contrato, correo, comunicacion, testimonio, peritaje, 
                  audio, video, fotografia, factura, acta, certificado, otro.

Para cada prueba indica:
- Si está DISPONIBLE en el expediente o solo se menciona que falta/se necesita.
- Su FUERZA probatoria estimada (0.0 a 1.0).
- Si SOPORTA o CONTRADICE algún hecho identificado.

REGLAS:
- NUNCA inventes pruebas que no estén mencionadas en el expediente.
- Si una prueba contradice un hecho, márcala como "contradice".
- Los vacíos son hechos esenciales que NO tienen ninguna prueba que los soporte.
- Usa SOLO los frag_id de esta lista: {frag_ids}. NO inventes frag_id nuevos.

Devuelve ÚNICAMENTE JSON válido, sin texto adicional:
{{
  "pruebas": [
    {{
      "id": "P001",
      "tipo": "correo",
      "descripcion": "correos de requerimiento enviados al demandado",
      "hecho_relacionado": "H001",
      "relacion": "soporta",
      "disponible": true,
      "fuerza": 0.75,
      "frag_id": "frag-003"
    }}
  ],
  "vacios": [
    {{
      "hecho_id": "H002",
      "descripcion": "No hay prueba documental del nexo causal",
      "accion_sugerida": "Solicitar peritaje técnico"
    }}
  ]
}}"""),
    ("human", """Hechos identificados:
{hechos}

Fragmentos del expediente:
{fragmentos}

frag_id válidos: {frag_ids}"""),
])


def probatorio_node(state: CaseState) -> dict:
    print("[probatorio]  Catalogando pruebas y vacíos...")

    segmentos = state.get("segmentos", [])
    hechos    = state.get("hechos", [])
    errores   = []
    llm_meta = {"proveedor": "no_ejecutado", "modelo": "sin_modelo"}

    frag_ids_reales = sorted({s["frag_id"] for s in segmentos}) if segmentos else []
    frag_ids_str = ", ".join(frag_ids_reales)

    try:
        respuesta, llm_meta = invoke_llm(PROMPT, {
            "hechos":     json.dumps(hechos, ensure_ascii=False, indent=2),
            "fragmentos": texto_resumido(segmentos, MAX_SEGMENTOS_POR_LLAMADA),
            "frag_ids":   frag_ids_str,
        })
        contenido = respuesta.content.strip()
        if contenido.startswith("```"):
            contenido = contenido.split("```")[1]
            if contenido.startswith("json"):
                contenido = contenido[4:]

        datos = json.loads(contenido)

    except json.JSONDecodeError as e:
        errores.append(f"Error parseando JSON del probatorio: {e}")
        datos = {"pruebas": [], "vacios": []}
    except Exception as e:
        errores.append(f"Error en probatorio: {e}")
        datos = {"pruebas": [], "vacios": []}

    pruebas = datos.get("pruebas", [])
    vacios  = datos.get("vacios", [])

    # Filtrar frag_id inválidos
    for p in pruebas:
        if p.get("frag_id") and p["frag_id"] not in frag_ids_reales:
            p["frag_id"] = None

    print(f"[probatorio]  ✓  {len(pruebas)} pruebas | {len(vacios)} vacíos críticos")

    traza = {
        "agente":    "probatorio",
        "tipo":      f"llm_{llm_meta['proveedor']}",
        "modelo":    llm_meta["modelo"],
        "timestamp": datetime.datetime.now().isoformat(),
        "pruebas_encontradas": len(pruebas),
        "vacios_detectados":   len(vacios),
        "errores":   errores,
    }

    return {
        "pruebas": pruebas,
        "vacios":  vacios,
        "trazas":  [traza],
        "errores": errores,
    }
