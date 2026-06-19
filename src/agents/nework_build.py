"""
network_builder.py — Agente 6: Constructor de Red Multicapa
Tipo: Python puro + NetworkX (sin LLM)
Función: Convierte la Matriz HPN en una red compleja multicapa.
Entrada: matriz_hpn, actores
Salida:  grafo (dict serializable)
"""

import json
import datetime
from src.state import CaseState
from src.tools.graph_tools import construir_grafo, grafo_a_dict, exportar_html
from src.config import OUTPUT_RED_HTML


def network_builder_node(state: CaseState) -> dict:
    print("[network_builder]  Construyendo red multicapa...")

    matriz  = state.get("matriz_hpn", [])
    actores = state.get("actores", [])
    errores = []

    try:
        G = construir_grafo(matriz, actores)
        grafo_dict = grafo_a_dict(G)

        # Exportar HTML interactivo (para el dashboard y entregable)
        try:
            exportar_html(G, str(OUTPUT_RED_HTML))
            print(f"[network_builder]  ✓  Red HTML exportada → {OUTPUT_RED_HTML}")
        except Exception as e:
            errores.append(f"No se pudo exportar HTML de red: {e}")

        total_nodos   = G.number_of_nodes()
        total_aristas = G.number_of_edges()
        capas = list({d.get("capa", "?") for _, d in G.nodes(data=True)})

        print(f"[network_builder]  ✓  {total_nodos} nodos | "
              f"{total_aristas} aristas | capas: {capas}")

    except Exception as e:
        msg = f"Error en network_builder: {e}"
        errores.append(msg)
        print(f"[network_builder]  ✗  {msg}")
        grafo_dict    = {"nodes": [], "links": []}
        total_nodos   = 0
        total_aristas = 0

    traza = {
        "agente":    "network_builder",
        "tipo":      "python_puro_networkx",
        "timestamp": datetime.datetime.now().isoformat(),
        "total_nodos":   total_nodos,
        "total_aristas": total_aristas,
        "errores":   errores,
    }

    return {
        "grafo":   grafo_dict,
        "trazas":  [traza],
        "errores": errores,
    }
