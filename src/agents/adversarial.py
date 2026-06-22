"""
adversarial.py — Agente 8: Adversarial
Tipo: LLM (Groq)
Función: Ataca la teoría del caso desde la perspectiva de la contraparte.
Entrada: matriz_hpn, metricas
Salida:  ataques
"""

import json
import datetime
from langchain_core.prompts import ChatPromptTemplate
from src.state import CaseState
from src.llm_client import invoke_llm

PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Eres el Agente Adversarial de un sistema de análisis jurídico.

Tu rol es el de un abogado crítico o un juez exigente que analiza la teoría del caso
y busca sus puntos débiles: excepciones que pueden prosperar, pruebas atacables,
argumentos débiles, vacíos normativos y contradicciones explotables.

PROPÓSITO: Que el abogado llegue mejor preparado anticipando los ataques de la contraparte.

REGLAS:
- Basa tus ataques en los datos reales de la matriz HPN. No inventes hechos nuevos.
- Marca claramente si el ataque es "certero" (alta probabilidad de prosperar) o 
  "hipotético" (depende de contexto adicional).
- Propón contramedidas concretas para cada ataque.

Devuelve ÚNICAMENTE JSON válido, sin texto adicional:
{{
  "ataques": [
    {{
      "id": "AT001",
      "tipo": "excepcion | contradiccion | vacío_probatorio | vacío_normativo | debilidad_argumental",
      "descripcion": "descripción del ataque",
      "fila_hpn_afectada": "HPN-002",
      "certeza": "certero | hipotetico",
      "riesgo": "bajo | medio | alto | critico",
      "contramedida": "acción concreta para contrarrestar este ataque"
    }}
  ]
}}"""),
    ("human", """Matriz HPN del caso:
{matriz}

Métricas calculadas:
{metricas}

Identifica todos los ataques posibles de la contraparte o un juez crítico."""),
])


def adversarial_node(state: CaseState) -> dict:
    print("[adversarial]  Simulando ataques de la contraparte...")

    matriz   = state.get("matriz_hpn", [])
    metricas = state.get("metricas", {})
    errores  = []
    llm_meta = {"proveedor": "no_ejecutado", "modelo": "sin_modelo"}

    # Resumen de la matriz para no exceder contexto
    matriz_resumen = [
        {
            "id":               f.get("id"),
            "elemento_juridico": f.get("elemento_juridico"),
            "estado":           f.get("estado"),
            "riesgo":           f.get("riesgo"),
            "contradicciones":  f.get("contradicciones", []),
            "n_pruebas":        len(f.get("pruebas", [])),
            "n_normas":         len(f.get("normas", [])),
        }
        for f in matriz
    ]

    try:
        respuesta, llm_meta = invoke_llm(PROMPT, {
            "matriz":   json.dumps(matriz_resumen, ensure_ascii=False, indent=2),
            "metricas": json.dumps(metricas.get("hpn", {}), ensure_ascii=False, indent=2),
        }, temperature=0.2)
        contenido = respuesta.content.strip()
        if contenido.startswith("```"):
            contenido = contenido.split("```")[1]
            if contenido.startswith("json"):
                contenido = contenido[4:]

        datos = json.loads(contenido)

    except json.JSONDecodeError as e:
        errores.append(f"Error parseando JSON del adversarial: {e}")
        datos = {"ataques": []}
    except Exception as e:
        errores.append(f"Error en adversarial: {e}")
        datos = {"ataques": []}

    ataques = datos.get("ataques", [])
    print(f"[adversarial]  ✓  {len(ataques)} ataques identificados")

    traza = {
        "agente":    "adversarial",
        "tipo":      f"llm_{llm_meta['proveedor']}",
        "modelo":    llm_meta["modelo"],
        "timestamp": datetime.datetime.now().isoformat(),
        "ataques_identificados": len(ataques),
        "errores":   errores,
    }

    return {
        "ataques": ataques,
        "trazas":  [traza],
        "errores": errores,
    }
