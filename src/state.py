"""
state.py
Define CaseState: el único diccionario que fluye por todos los agentes.
Cada agente lee lo que necesita y devuelve solo los campos que modifica.
"""

from typing import TypedDict, Annotated
import operator


def _acumular(a: list, b: list) -> list:
    """Reducer: acumula listas entre nodos en lugar de sobrescribir."""
    return (a or []) + (b or [])


class CaseState(TypedDict):
    # ── Metadatos del caso ────────────────────────────────────────────────────
    case_id:   str
    pdf_path:  str

    # ── Salida de intake ──────────────────────────────────────────────────────
    # Lista de fragmentos: {"frag_id", "pagina", "texto", "hash"}
    segmentos: list[dict]

    # ── Salida de extractor ───────────────────────────────────────────────────
    # Hechos: {"id", "texto", "fecha", "actor", "frag_id", "confianza"}
    hechos: list[dict]
    # Actores: {"id", "nombre", "rol", "frag_id"}
    actores: list[dict]
    # Cronología: {"fecha", "evento", "actor", "frag_id"}
    cronologia: list[dict]

    # ── Salida de probatorio ──────────────────────────────────────────────────
    # Pruebas: {"id", "tipo", "descripcion", "hecho_relacionado", "disponible", "fuerza", "frag_id"}
    pruebas: list[dict]
    # Vacíos: {"hecho_id", "descripcion", "accion_sugerida"}
    vacios: list[dict]

    # ── Salida de normativo ───────────────────────────────────────────────────
    # Normas: {"id", "texto", "fuente", "hecho_relacionado"}
    normas: list[dict]

    # ── Artefacto central: Matriz HPN ─────────────────────────────────────────
    # Filas HPN según esquema del proyecto
    matriz_hpn: list[dict]

    # ── Artefacto central: Red multicapa ─────────────────────────────────────
    # Formato node_link_data de NetworkX: {"nodes": [...], "links": [...]}
    grafo: dict

    # ── Métricas ──────────────────────────────────────────────────────────────
    metricas: dict

    # ── Análisis adversarial ──────────────────────────────────────────────────
    # Ataques: {"tipo", "descripcion", "fila_hpn_afectada", "riesgo", "contramedida"}
    ataques: list[dict]

    # ── Escenarios de simulación ──────────────────────────────────────────────
    # Escenarios: {"id", "nombre", "supuesto", "hechos_afectados",
    #              "metricas_antes", "metricas_despues", "accion_sugerida"}
    escenarios: list[dict]

    # ── Auditoría ─────────────────────────────────────────────────────────────
    reporte_auditoria: dict
    revision_humana_requerida: bool
    explicaciones: list[dict]

    # ── Trazas acumuladas de TODOS los agentes ────────────────────────────────
    # Annotated con _acumular para que cada agente AÑADA sin sobrescribir
    trazas: Annotated[list[dict], _acumular]

    # ── Errores capturados ────────────────────────────────────────────────────
    errores: Annotated[list[str], _acumular]
