"""
graph.py — Grafo LangGraph y punto de entrada principal del sistema.

Orquesta los 10 agentes en secuencia con estado compartido.
Guarda todos los artefactos en la carpeta output/.

Uso:
    python src/graph.py
"""

import json
import datetime
from pathlib import Path

from langgraph.graph import StateGraph, START, END

from src.state import CaseState
from src.agents.intake          import intake_node
from src.agents.extractor       import extractor_node
from src.agents.probatorio      import probatorio_node
from src.agents.normativo       import normativo_node
from src.agents.hpn_builder     import hpn_builder_node
from src.agents.network_builder import network_builder_node
from src.agents.metrics         import metrics_node
from src.agents.adversarial     import adversarial_node
from src.agents.simulator       import simulator_node
from src.agents.auditor         import auditor_node

from src.config import (
    PDF_PATH,
    OUTPUT_HPN, OUTPUT_GRAFO, OUTPUT_METRICAS,
    OUTPUT_ESCENARIOS, OUTPUT_TRAZAS,
)


# ── Construcción del grafo ────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    builder = StateGraph(CaseState)

    # Registrar los 10 nodos
    builder.add_node("intake",          intake_node)
    builder.add_node("extractor",       extractor_node)
    builder.add_node("probatorio",      probatorio_node)
    builder.add_node("normativo",       normativo_node)
    builder.add_node("hpn_builder",     hpn_builder_node)
    builder.add_node("network_builder", network_builder_node)
    builder.add_node("metrics",         metrics_node)
    builder.add_node("adversarial",     adversarial_node)
    builder.add_node("simulator",       simulator_node)
    builder.add_node("auditor",         auditor_node)

    # Flujo secuencial
    # intake → extractor → probatorio y normativo (paralelos) → hpn_builder
    # → network_builder → metrics → adversarial → simulator → auditor → END
    builder.add_edge(START,            "intake")
    builder.add_edge("intake",         "extractor")
    builder.add_edge("extractor",      "probatorio")
    builder.add_edge("probatorio",     "normativo")
    builder.add_edge("normativo",      "hpn_builder")
    builder.add_edge("hpn_builder",    "network_builder")
    builder.add_edge("network_builder","metrics")
    builder.add_edge("metrics",        "adversarial")
    builder.add_edge("adversarial",    "simulator")
    builder.add_edge("simulator",      "auditor")
    builder.add_edge("auditor",        END)

    return builder.compile()


# ── Persistencia de artefactos ────────────────────────────────────────────────

def guardar_artefactos(estado: CaseState) -> None:
    """Guarda todos los artefactos generados en la carpeta output/."""

    def _escribir_json(ruta: Path, datos: object) -> None:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        print(f"  💾  {ruta}")

    def _escribir_jsonl(ruta: Path, datos: list) -> None:
        with open(ruta, "w", encoding="utf-8") as f:
            for item in datos:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"  💾  {ruta}")

    print("\n── Guardando artefactos ──────────────────────────────────────────────")

    # E4: Matriz HPN
    _escribir_json(OUTPUT_HPN, {
        "case_id":    estado.get("case_id"),
        "timestamp":  datetime.datetime.now().isoformat(),
        "total_filas": len(estado.get("matriz_hpn", [])),
        "filas":      estado.get("matriz_hpn", []),
    })

    # E5: Red multicapa
    _escribir_json(OUTPUT_GRAFO, estado.get("grafo", {}))

    # E6: Métricas
    _escribir_json(OUTPUT_METRICAS, estado.get("metricas", {}))

    # E7: Escenarios
    _escribir_json(OUTPUT_ESCENARIOS, {
        "case_id":    estado.get("case_id"),
        "timestamp":  datetime.datetime.now().isoformat(),
        "escenarios": estado.get("escenarios", []),
    })

    # E3: Trazas (log de auditoría en JSONL)
    _escribir_jsonl(OUTPUT_TRAZAS, estado.get("trazas", []))

    print("── Artefactos guardados ✓ ───────────────────────────────────────────\n")


# ── Punto de entrada ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    # Verificar que el PDF existe
    if not PDF_PATH.exists():
        print(f"\n❌  No se encontró el PDF del expediente en: {PDF_PATH}")
        print("    Copia el expediente como:  data/input/expediente.pdf")
        sys.exit(1)

    print("\n" + "═" * 60)
    print("  Sistema Multiagente — Teoría del Caso Aumentada")
    print("  Ciencia de Datos 2026-1 — Universidad de Pamplona")
    print("═" * 60)
    print(f"  PDF:  {PDF_PATH}")
    print("═" * 60 + "\n")

    # Estado inicial
    estado_inicial: CaseState = {
        "case_id":   f"caso-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "pdf_path":  str(PDF_PATH),
        # Campos vacíos — cada agente los llena
        "segmentos":  [],
        "hechos":     [],
        "actores":    [],
        "cronologia": [],
        "pruebas":    [],
        "vacios":     [],
        "normas":     [],
        "matriz_hpn": [],
        "grafo":      {},
        "metricas":   {},
        "ataques":    [],
        "escenarios": [],
        "reporte_auditoria":        {},
        "revision_humana_requerida": False,
        "trazas":  [],
        "errores": [],
    }

    # Construir y ejecutar el grafo
    graph = build_graph()
    estado_final = graph.invoke(estado_inicial)

    # Guardar todos los artefactos
    guardar_artefactos(estado_final)

    # Resumen final en consola
    print("═" * 60)
    print("  RESUMEN FINAL")
    print("═" * 60)
    print(f"  Segmentos extraídos:  {len(estado_final.get('segmentos', []))}")
    print(f"  Hechos identificados: {len(estado_final.get('hechos', []))}")
    print(f"  Pruebas catalogadas:  {len(estado_final.get('pruebas', []))}")
    print(f"  Normas identificadas: {len(estado_final.get('normas', []))}")
    print(f"  Filas HPN generadas:  {len(estado_final.get('matriz_hpn', []))}")
    print(f"  Ataques identificados:{len(estado_final.get('ataques', []))}")
    print(f"  Escenarios simulados: {len(estado_final.get('escenarios', []))}")

    metricas_hpn = estado_final.get("metricas", {}).get("hpn", {})
    if metricas_hpn:
        print(f"\n  Cobertura probatoria: {metricas_hpn.get('cobertura_probatoria', '?')}")
        print(f"  Vacíos críticos:      {metricas_hpn.get('vacios_criticos', '?')}")
        print(f"  Trazabilidad:         {metricas_hpn.get('trazabilidad', '?')}")

    score = estado_final.get("reporte_auditoria", {}).get("score_calidad", "?")
    rev   = estado_final.get("revision_humana_requerida", True)
    print(f"\n  Score de calidad:     {score}")
    print(f"  Revisión humana:      {'⚠️  SÍ REQUERIDA' if rev else '✓  No urgente'}")

    if estado_final.get("errores"):
        print(f"\n  ⚠️  Errores registrados: {len(estado_final['errores'])}")
        for e in estado_final["errores"]:
            print(f"     - {e}")

    print("\n  Dashboard → ejecuta: streamlit run dashboard/app.py")
    print("═" * 60 + "\n")
