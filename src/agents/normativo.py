"""
normativo.py — Agente 4: Normativo
Tipo: LLM (Groq)
Función: Identifica normas, reglas, requisitos jurídicos y precedentes.
Entrada: hechos, segmentos
Salida:  normas
"""

import json
import datetime
from langchain_core.prompts import ChatPromptTemplate
from src.state import CaseState
from src.tools.pdf_tools import texto_resumido
from src.config import MAX_SEGMENTOS_POR_LLAMADA
from src.llm_client import invoke_llm

PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Eres el Agente Normativo de un sistema de análisis jurídico.

Tu tarea es identificar todas las NORMAS, REGLAS JURÍDICAS y REQUISITOS LEGALES 
relevantes que aparecen en el expediente o que son claramente aplicables al caso.

TIPOS: ley, decreto, clausula_contractual, reglamento, precedente_jurisprudencial, 
       principio_general, norma_procesal, otro.

FUENTES posibles:
- "expediente": la norma está citada explícitamente en el expediente.
- "inferida": es claramente aplicable por el tipo de caso aunque no se cite textualmente.

REGLAS CRÍTICAS:
- Marca como "expediente" SOLO si la norma aparece textualmente en los fragmentos.
- Marca como "inferida" si la deduces del tipo de caso. Sé conservador.
- NUNCA inventes números de artículos o leyes específicas que no estén en el texto.
- Si no hay norma clara para un hecho, indícalo en la lista de vacíos normativos.
- Usa SOLO los frag_id de esta lista: {frag_ids}. NO inventes frag_id nuevos.

Devuelve ÚNICAMENTE JSON válido, sin texto adicional:
{{
  "normas": [
    {{
      "id": "N001",
      "texto": "descripción de la norma o cláusula aplicable",
      "tipo": "clausula_contractual",
      "fuente": "expediente",
      "hecho_relacionado": "H001",
      "frag_id": "frag-002"
    }}
  ],
  "vacios_normativos": [
    {{
      "hecho_id": "H003",
      "descripcion": "No se identifica norma aplicable al nexo causal",
      "accion_sugerida": "Buscar precedentes jurisprudenciales sobre responsabilidad contractual"
    }}
  ]
}}"""),
    ("human", """Hechos identificados:
{hechos}

Fragmentos del expediente:
{fragmentos}

frag_id válidos: {frag_ids}"""),
])


def normativo_node(state: CaseState) -> dict:
    print("[normativo]  Identificando normas aplicables...")

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
        errores.append(f"Error parseando JSON del normativo: {e}")
        datos = {"normas": [], "vacios_normativos": []}
    except Exception as e:
        errores.append(f"Error en normativo: {e}")
        datos = {"normas": [], "vacios_normativos": []}

    normas = datos.get("normas", [])

    # Filtrar frag_id inválidos
    for n in normas:
        if n.get("frag_id") and n["frag_id"] not in frag_ids_reales:
            n["frag_id"] = None

    print(f"[normativo]  ✓  {len(normas)} normas identificadas")

    traza = {
        "agente":    "normativo",
        "tipo":      f"llm_{llm_meta['proveedor']}",
        "modelo":    llm_meta["modelo"],
        "timestamp": datetime.datetime.now().isoformat(),
        "normas_identificadas":   len(normas),
        "vacios_normativos":      len(datos.get("vacios_normativos", [])),
        "errores":   errores,
    }

    return {
        "normas":  normas,
        "trazas":  [traza],
        "errores": errores,
    }
