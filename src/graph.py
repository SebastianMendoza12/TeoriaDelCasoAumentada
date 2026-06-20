"""
graph.py — Grafo LangGraph y punto de entrada principal del sistema.

Orquesta los 13 agentes en secuencia con estado compartido.
Incluye middleware de PreCompletionChecklist y LoopDetection.

Uso:
    python -m src.graph
"""

import json
import datetime
from pathlib import Path

from langgraph.graph import StateGraph, START, END

from src.state import CaseState
from src.agents.intake               import intake_node
from src.agents.extractor            import extractor_node
from src.agents.probatorio           import probatorio_node
from src.agents.normativo            import normativo_node
from src.agents.hpn_builder          import hpn_builder_node
from src.agents.network_builder      import network_builder_node
from src.agents.metrics              import metrics_node
from src.agents.adversarial          import adversarial_node
from src.agents.simulator            import simulator_node
from src.agents.auditor              import auditor_node
from src.agents.dashboard_node       import dashboard_node
from src.agents.explanation_builder  import explanation_builder_node
from src.agents.explanation_verifier import explanation_verifier_node

from src.middleware.pre_completion_checklist import aplicar_checklist
from src.middleware.loop_detection           import aplicar_loop_detection

from src.config import (
    PDF_PATH, OUTPUT_DIR,
    OUTPUT_HPN, OUTPUT_GRAFO, OUTPUT_METRICAS,
    OUTPUT_ESCENARIOS, OUTPUT_TRAZAS,
)

OUTPUT_EXPLICACIONES   = OUTPUT_DIR / "explicaciones.json"
OUTPUT_CHECKLIST       = OUTPUT_DIR / "checklist.json"
OUTPUT_LOOP_DETECTION  = OUTPUT_DIR / "loop_detection.json"


# ── Construcción del grafo ────────────────────────────────────────────────────

def build_graph():
    builder = StateGraph(CaseState)

    # Registrar los 13 nodos
    builder.add_node("intake",                intake_node)
    builder.add_node("extractor",             extractor_node)
    builder.add_node("probatorio",            probatorio_node)
    builder.add_node("normativo",             normativo_node)
    builder.add_node("hpn_builder",           hpn_builder_node)
    builder.add_node("network_builder",       network_builder_node)
    builder.add_node("metrics",               metrics_node)
    builder.add_node("adversarial",           adversarial_node)
    builder.add_node("simulator",             simulator_node)
    builder.add_node("auditor",               auditor_node)
    builder.add_node("dashboard_node",        dashboard_node)
    builder.add_node("explanation_builder",   explanation_builder_node)
    builder.add_node("explanation_verifier",  explanation_verifier_node)

    # Flujo secuencial completo
    builder.add_edge(START,                  "intake")
    builder.add_edge("intake",               "extractor")
    builder.add_edge("extractor",            "probatorio")
    builder.add_edge("probatorio",           "normativo")
    builder.add_edge("normativo",            "hpn_builder")
    builder.add_edge("hpn_builder",          "network_builder")
    builder.add_edge("network_builder",      "metrics")
    builder.add_edge("metrics",              "adversarial")
    builder.add_edge("adversarial",          "simulator")
    builder.add_edge("simulator",            "auditor")
    builder.add_edge("auditor",              "dashboard_node")
    builder.add_edge("dashboard_node",       "explanation_builder")
    builder.add_edge("explanation_builder",  "explanation_verifier")
    builder.add_edge("explanation_verifier", END)

    return builder.compile()


# ── Persistencia de artefactos ────────────────────────────────────────────────

def guardar_artefactos(estado: CaseState, checklist: dict, loop: dict) -> None:
    def _json(ruta, datos):
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        print(f"  💾  {ruta.name}")

    def _jsonl(ruta, datos):
        with open(ruta, "w", encoding="utf-8") as f:
            for item in datos:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"  💾  {ruta.name}")

    print("\n── Guardando artefactos ──────────────────────────────────────────────")

    _json(OUTPUT_HPN, {
        "case_id":    estado.get("case_id"),
        "timestamp":  datetime.datetime.now().isoformat(),
        "total_filas": len(estado.get("matriz_hpn", [])),
        "filas":      estado.get("matriz_hpn", []),
    })
    _json(OUTPUT_GRAFO,      estado.get("grafo", {}))
    _json(OUTPUT_METRICAS,   estado.get("metricas", {}))
    _json(OUTPUT_ESCENARIOS, {
        "case_id":    estado.get("case_id"),
        "timestamp":  datetime.datetime.now().isoformat(),
        "escenarios": estado.get("escenarios", []),
    })
    _json(OUTPUT_EXPLICACIONES, {
        "case_id":       estado.get("case_id"),
        "timestamp":     datetime.datetime.now().isoformat(),
        "explicaciones": estado.get("explicaciones", []),
    })
    _json(OUTPUT_CHECKLIST,      checklist)
    _json(OUTPUT_LOOP_DETECTION, loop)
    _jsonl(OUTPUT_TRAZAS,        estado.get("trazas", []))

    print("── Artefactos guardados ✓ ───────────────────────────────────────────\n")


# ── Punto de entrada ──────────────────────────────────────────────────────────

def ejecutar(pdf_path: str = None) -> CaseState:
    """
    Ejecuta el sistema completo sobre un PDF.
    Puede llamarse desde graph.py o desde el dashboard.
    """
    ruta_pdf = Path(pdf_path) if pdf_path else PDF_PATH

    if not ruta_pdf.exists():
        raise FileNotFoundError(
            f"No se encontró el PDF en: {ruta_pdf}\n"
            "Copia el expediente como: data/input/expediente.pdf"
        )

    print("\n" + "═" * 60)
    print("  Sistema Multiagente — Teoría del Caso Aumentada")
    print("  Ciencia de Datos 2026-1 — Universidad de Pamplona")
    print("═" * 60)
    print(f"  PDF:  {ruta_pdf}")
    print("═" * 60 + "\n")

    estado_inicial: CaseState = {
        "case_id":   f"caso-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "pdf_path":  str(ruta_pdf),
        "segmentos":  [], "hechos": [], "actores": [], "cronologia": [],
        "pruebas": [], "vacios": [], "normas": [],
        "matriz_hpn": [], "grafo": {}, "metricas": {},
        "ataques": [], "escenarios": [],
        "reporte_auditoria": {},
        "revision_humana_requerida": False,
        "explicaciones": [],
        "trazas": [], "errores": [],
    }

    graph = build_graph()
    estado_final = graph.invoke(estado_inicial)

    # ── Middleware: Loop Detection ─────────────────────────────────────────────
    print("\n── Middleware ────────────────────────────────────────────────────────")
    resultado_loop = aplicar_loop_detection(estado_final.get("trazas", []))

    # ── Middleware: PreCompletion Checklist ───────────────────────────────────
    resultado_checklist = aplicar_checklist(estado_final)

    # ── Guardar todo ──────────────────────────────────────────────────────────
    guardar_artefactos(estado_final, resultado_checklist, resultado_loop)

    # ── Resumen final ─────────────────────────────────────────────────────────
    print("═" * 60)
    print("  RESUMEN FINAL")
    print("═" * 60)
    print(f"  Segmentos extraídos:   {len(estado_final.get('segmentos', []))}")
    print(f"  Hechos identificados:  {len(estado_final.get('hechos', []))}")
    print(f"  Pruebas catalogadas:   {len(estado_final.get('pruebas', []))}")
    print(f"  Normas identificadas:  {len(estado_final.get('normas', []))}")
    print(f"  Filas HPN generadas:   {len(estado_final.get('matriz_hpn', []))}")
    print(f"  Ataques identificados: {len(estado_final.get('ataques', []))}")
    print(f"  Escenarios simulados:  {len(estado_final.get('escenarios', []))}")
    print(f"  Explicaciones:         {len(estado_final.get('explicaciones', []))}")

    metricas_hpn = estado_final.get("metricas", {}).get("hpn", {})
    if metricas_hpn:
        print(f"\n  Cobertura probatoria:  {metricas_hpn.get('cobertura_probatoria', '?')}")
        print(f"  Vacíos críticos:       {metricas_hpn.get('vacios_criticos', '?')}")
        print(f"  Trazabilidad:          {metricas_hpn.get('trazabilidad', '?')}")

    score = estado_final.get("reporte_auditoria", {}).get("score_calidad", "?")
    rev   = estado_final.get("revision_humana_requerida", True)
    print(f"\n  Score de calidad:      {score}")
    print(f"  Checklist aprobado:    {'✅ SÍ' if resultado_checklist.get('aprobado') else '❌ NO'}")
    print(f"  Loop detectado:        {'⚠️ SÍ' if resultado_loop.get('loop_detectado') else '✓ NO'}")
    print(f"  Revisión humana:       {'⚠️  SÍ REQUERIDA' if rev else '✓  No urgente'}")

    if estado_final.get("errores"):
        print(f"\n  ⚠️  Errores: {len(estado_final['errores'])}")
        for e in estado_final["errores"][:5]:
            print(f"     - {e}")

    print("\n  Dashboard → ejecuta: streamlit run dashboard/app.py")
    print("═" * 60 + "\n")

    return estado_final


if __name__ == "__main__":
    ejecutar()