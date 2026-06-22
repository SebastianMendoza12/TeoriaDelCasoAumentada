"""
metrics.py — Agente 7: Métricas
Tipo: Python puro (sin LLM)
Función: Calcula todas las métricas de la Matriz HPN y de la red multicapa.
Entrada: matriz_hpn, grafo
Salida:  metricas
"""

import datetime
import networkx as nx
from src.state import CaseState
from src.tools.hpn_tools import calcular_metricas_hpn
from src.tools.graph_tools import calcular_metricas_red


def metrics_node(state: CaseState) -> dict:
    print("[metrics]  Calculando métricas...")

    matriz = state.get("matriz_hpn", [])
    grafo_dict = state.get("grafo", {})
    errores = []

    # ── Métricas de la Matriz HPN ─────────────────────────────────────────────
    metricas_hpn = {}
    try:
        metricas_hpn = calcular_metricas_hpn(matriz)
    except Exception as e:
        errores.append(f"Error calculando métricas HPN: {e}")

    # ── Métricas de la Red Multicapa ──────────────────────────────────────────
    metricas_red = {}
    try:
        if grafo_dict.get("nodes"):
            G = nx.node_link_graph(grafo_dict, edges="links")
            metricas_red = calcular_metricas_red(G)
        else:
            metricas_red = {"advertencia": "Grafo vacío, no se calcularon métricas de red"}
    except Exception as e:
        errores.append(f"Error calculando métricas de red: {e}")

    metricas = {
        "hpn":        metricas_hpn,
        "red":        metricas_red,
        "timestamp":  datetime.datetime.now().isoformat(),
    }

    # Resumen en consola
    if metricas_hpn:
        print(f"[metrics]  ✓  HPN → "
              f"cobertura_probatoria={metricas_hpn.get('cobertura_probatoria', '?')} | "
              f"vacios={metricas_hpn.get('vacios_criticos', '?')} | "
              f"contradicciones={metricas_hpn.get('indice_contradiccion', '?')}")
    if metricas_red:
        print(f"[metrics]  ✓  Red → "
              f"nodos={metricas_red.get('total_nodos', '?')} | "
              f"densidad={metricas_red.get('densidad', '?')} | "
              f"puntos_falla={len(metricas_red.get('puntos_unicos_de_falla', []))}")

    traza = {
        "agente":    "metrics",
        "tipo":      "python_puro",
        "timestamp": datetime.datetime.now().isoformat(),
        "metricas_hpn_calculadas": list(metricas_hpn.keys()),
        "metricas_red_calculadas": list(metricas_red.keys()),
        "errores":   errores,
    }

    return {
        "metricas": metricas,
        "trazas":   [traza],
        "errores":  errores,
    }
