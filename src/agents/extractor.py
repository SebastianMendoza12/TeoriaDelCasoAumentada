"""
extractor.py — Agente 2: Extractor fáctico-cronológico
Tipo: LLM (Groq — llama-3.3-70b)
Función: Extrae hechos, actores y cronología del expediente.
Entrada: segmentos del estado
Salida:  hechos, actores, cronologia
"""

import json
import datetime
from langchain_core.prompts import ChatPromptTemplate
from src.state import CaseState
from src.tools.pdf_tools import texto_resumido
from src.config import MAX_SEGMENTOS_POR_LLAMADA
from src.llm_client import invoke_llm

PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Eres el Agente Extractor Fáctico-Cronológico de un sistema de análisis jurídico.

Tu tarea es analizar los fragmentos del expediente y extraer tres listas:

1. HECHOS: cada afirmación fáctica relevante del caso.
2. ACTORES: todas las personas, entidades o instituciones mencionadas.
3. CRONOLOGÍA: eventos ordenados cronológicamente.

REGLAS ESTRICTAS:
- NUNCA inventes información. Si algo no está en el texto, no lo incluyas.
- Cada hecho debe referenciar el frag_id de la página donde aparece.
- Si no puedes determinar una fecha, usa null.
- Si la confianza en la extracción es baja, asígnale un valor menor.
- Usa SOLO los frag_id de esta lista: {frag_ids}. NO inventes frag_id nuevos.

Devuelve ÚNICAMENTE un JSON válido con esta estructura exacta, sin texto adicional:
{{
  "hechos": [
    {{
      "id": "H001",
      "texto": "descripción del hecho",
      "fecha": "YYYY-MM-DD o null",
      "actor": "nombre del actor principal",
      "frag_id": "frag-001",
      "pagina": 1,
      "confianza": 0.9
    }}
  ],
  "actores": [
    {{
      "id": "A001",
      "nombre": "nombre completo",
      "rol": "demandante | demandado | testigo | perito | autoridad | tercero",
      "frag_id": "frag-001"
    }}
  ],
  "cronologia": [
    {{
      "fecha": "YYYY-MM-DD o descripción",
      "evento": "descripción del evento",
      "actor": "actor principal",
      "frag_id": "frag-001"
    }}
  ]
}}"""),
    ("human", "Fragmentos del expediente:\n\n{fragmentos}\n\nfrag_id válidos: {frag_ids}"),
])


def extractor_node(state: CaseState) -> dict:
    print("[extractor]  Extrayendo hechos, actores y cronología...")

    segmentos = state.get("segmentos", [])
    errores = []
    llm_meta = {"proveedor": "no_ejecutado", "modelo": "sin_modelo"}

    if not segmentos:
        errores.append("No hay segmentos disponibles para extraer")
        return {"hechos": [], "actores": [], "cronologia": [],
                "trazas": [{"agente": "extractor", "error": "sin segmentos"}],
                "errores": errores}

    frag_ids_reales = sorted({s["frag_id"] for s in segmentos})
    frag_ids_str = ", ".join(frag_ids_reales)

    try:
        fragmentos = texto_resumido(segmentos, MAX_SEGMENTOS_POR_LLAMADA)
        respuesta, llm_meta = invoke_llm(PROMPT, {
            "fragmentos": fragmentos,
            "frag_ids": frag_ids_str,
        })
        contenido = respuesta.content.strip()

        # Limpiar posibles bloques markdown del LLM
        if contenido.startswith("```"):
            contenido = contenido.split("```")[1]
            if contenido.startswith("json"):
                contenido = contenido[4:]

        datos = json.loads(contenido)

    except json.JSONDecodeError as e:
        errores.append(f"Error parseando JSON del extractor: {e}")
        datos = {"hechos": [], "actores": [], "cronologia": []}
    except Exception as e:
        errores.append(f"Error en extractor: {e}")
        datos = {"hechos": [], "actores": [], "cronologia": []}

    hechos     = datos.get("hechos", [])
    actores    = datos.get("actores", [])
    cronologia = datos.get("cronologia", [])

    # Filtrar frag_id inválidos (el LLM a veces inventa)
    for lista in [hechos, actores, cronologia]:
        for item in lista:
            if item.get("frag_id") and item["frag_id"] not in frag_ids_reales:
                item["frag_id"] = None

    print(f"[extractor]  ✓  {len(hechos)} hechos | {len(actores)} actores | {len(cronologia)} eventos")

    traza = {
        "agente":     "extractor",
        "tipo":       f"llm_{llm_meta['proveedor']}",
        "modelo":     llm_meta["modelo"],
        "timestamp":  datetime.datetime.now().isoformat(),
        "hechos_extraidos":  len(hechos),
        "actores_encontrados": len(actores),
        "eventos_cronologia":  len(cronologia),
        "errores":    errores,
    }

    return {
        "hechos":     hechos,
        "actores":    actores,
        "cronologia": cronologia,
        "trazas":     [traza],
        "errores":    errores,
    }
