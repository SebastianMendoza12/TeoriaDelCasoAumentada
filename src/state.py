# src/state.py
from typing import TypedDict, Annotated
import operator


def _acumular(a: list, b: list) -> list:
    """Reducer: acumula listas entre nodos sin sobrescribir."""
    return a + b


class CaseState(TypedDict):
    # ── Metadatos ─────────────────────────────────────────────────
    case_id:  str
    pdf_path: str

    # ── Ingesta (intake) ──────────────────────────────────────────
    segmentos: list[dict]   # [{frag_id, pagina, texto, hash}]

    # ── Extracción (extractor) ────────────────────────────────────
    hechos:    list[dict]   # [{id, texto, fecha, actor, frag_id, confianza}]
    actores:   list[dict]   # [{id, nombre, rol}]
    cronologia: list[dict]  # [{fecha, evento, frag_id}]

    # ── Probatorio ────────────────────────────────────────────────
    pruebas: list[dict]     # [{id, tipo, descripcion, estado, frag_id}]

    # ── Normativo ─────────────────────────────────────────────────
    normas: list[dict]      # [{id, texto, fuente}]

    # ── Artefactos centrales ──────────────────────────────────────
    matriz_hpn: list[dict]  # filas HPN validadas
    grafo:      dict        # node_link_data de NetworkX
    metricas:   dict        # indicadores calculados

    # ── Análisis estratégico ──────────────────────────────────────
    ataques:   list[dict]   # adversarial: excepciones y objeciones
    escenarios: list[dict]  # simulator: S1..Sn con antes/después

    # ── Auditoría ─────────────────────────────────────────────────
    auditoria:              list[dict]
    revision_humana:        bool
    trazas: Annotated[list[dict], _acumular]   # log acumulado de todos los nodos

    # ── Control ───────────────────────────────────────────────────
    errores: list[str]