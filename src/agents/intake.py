"""
intake.py — Agente 1: Ingesta del PDF
Tipo: Python puro (sin LLM)
Función: Lee el PDF, segmenta por página, asigna frag_id y hash.
Entrada: pdf_path del estado
Salida:  segmentos con página, texto y hash
"""

import datetime
from src.state import CaseState
from src.tools.pdf_tools import extraer_segmentos


def intake_node(state: CaseState) -> dict:
    print("[intake]  Leyendo PDF...")

    pdf_path = state["pdf_path"]
    segmentos = []
    errores = []

    try:
        segmentos = extraer_segmentos(pdf_path)
        print(f"[intake]  ✓  {len(segmentos)} segmentos extraídos")
    except Exception as e:
        msg = f"Error en intake: {e}"
        errores.append(msg)
        print(f"[intake]  ✗  {msg}")

    traza = {
        "agente":     "intake",
        "tipo":       "python_puro",
        "timestamp":  datetime.datetime.now().isoformat(),
        "resultado":  f"{len(segmentos)} segmentos extraídos de {pdf_path}",
        "errores":    errores,
    }

    return {
        "segmentos": segmentos,
        "trazas":    [traza],
        "errores":   errores,
    }
