# src/tools/pdf_tools.py
import hashlib
import fitz   # PyMuPDF


def extraer_segmentos(pdf_path: str) -> list[dict]:
    """
    Lee el PDF página por página.
    Devuelve lista de fragmentos con id, página, texto y hash.
    No usa LLM — es completamente determinístico.
    """
    doc = fitz.open(pdf_path)
    segmentos = []

    for num, page in enumerate(doc, start=1):
        texto = page.get_text("text").strip()
        if not texto:
            continue
        hash_val = hashlib.sha256(texto.encode()).hexdigest()[:10]
        segmentos.append({
            "frag_id":  f"frag-{num:03d}",
            "pagina":   num,
            "texto":    texto,
            "hash":     hash_val,
        })

    doc.close()
    return segmentos


def texto_para_llm(segmentos: list[dict], max_seg: int = 12) -> str:
    """
    Convierte los primeros N segmentos en texto plano con etiquetas
    de página, listo para incluir en un prompt.
    """
    return "\n\n---\n\n".join(
        f"[Página {s['pagina']} | {s['frag_id']}]\n{s['texto']}"
        for s in segmentos[:max_seg]
    )