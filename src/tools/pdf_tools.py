"""
pdf_tools.py
Extracción de texto del PDF usando PyMuPDF.
Sin LLM — completamente determinístico y reproducible.
"""

import hashlib
import fitz  # PyMuPDF


def extraer_segmentos(pdf_path: str) -> list[dict]:
    """
    Lee el PDF página por página.
    Devuelve lista de segmentos con: frag_id, pagina, texto, hash.
    El hash permite detectar duplicados y auditar fuentes.
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        raise RuntimeError(f"No se pudo abrir el PDF: {e}")

    segmentos = []
    for num_pagina, pagina in enumerate(doc, start=1):
        texto = pagina.get_text("text").strip()
        if not texto:
            continue  # página vacía o solo imágenes

        hash_val = hashlib.sha256(texto.encode("utf-8")).hexdigest()[:12]
        segmentos.append({
            "frag_id":  f"frag-{num_pagina:03d}",
            "pagina":   num_pagina,
            "texto":    texto,
            "hash":     hash_val,
        })

    doc.close()
    return segmentos


def texto_completo(segmentos: list[dict]) -> str:
    """Une todos los segmentos en un solo texto para pasarlo al LLM."""
    partes = []
    for s in segmentos:
        partes.append(f"[Página {s['pagina']} | {s['frag_id']}]\n{s['texto']}")
    return "\n\n---\n\n".join(partes)


def texto_resumido(segmentos: list[dict], max_segmentos: int = 15) -> str:
    """
    Versión recortada para no exceder el contexto del LLM.
    Toma los primeros max_segmentos fragmentos.
    """
    return texto_completo(segmentos[:max_segmentos])
