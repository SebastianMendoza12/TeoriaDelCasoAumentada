"""
graph_tools.py
Construcción de la red compleja multicapa y cálculo de métricas de red.
Usa NetworkX. Sin LLM — determinístico y reproducible.
"""

import networkx as nx
from src.config import UMBRAL_BETWEENNESS_FALLA


# Capas de la red multicapa (según Tabla de Capas del enunciado)
CAPA_POR_TIPO = {
    "hecho":       "hechos",
    "prueba":      "pruebas",
    "norma":       "normas",
    "actor":       "actores",
    "argumento":   "argumentos",
    "riesgo":      "riesgos",
    "tiempo":      "tiempo",
    "pretension":  "pretensiones",
}


def construir_grafo(matriz_hpn: list[dict], actores: list[dict] = None) -> nx.DiGraph:
    """
    Convierte la Matriz HPN en un grafo dirigido tipado con capas.
    Nodos: hechos, pruebas, normas, actores.
    Aristas: soporta, contradice, activa, precede, amenaza.
    """
    G = nx.DiGraph()

    for fila in matriz_hpn:
        # ── Nodo hecho ────────────────────────────────────────────────────────
        hecho = fila.get("hecho", {})
        hecho_id = hecho.get("id", f"H-{fila.get('id', '?')}")
        G.add_node(
            hecho_id,
            tipo="hecho",
            capa="hechos",
            texto=hecho.get("texto", ""),
            estado=fila.get("estado", "pendiente"),
            riesgo=fila.get("riesgo", "medio"),
            frag_id=hecho.get("frag_id", ""),
            pagina=hecho.get("pagina", 0),
        )

        # ── Nodos prueba + aristas ────────────────────────────────────────────
        for prueba in fila.get("pruebas", []):
            p_id = prueba.get("id", "P?")
            G.add_node(
                p_id,
                tipo="prueba",
                capa="pruebas",
                tipo_prueba=prueba.get("tipo", "desconocido"),
                disponible=prueba.get("disponible", True),
            )
            relacion = prueba.get("relacion", "soporta")
            peso = float(prueba.get("fuerza", 0.5))
            G.add_edge(
                p_id, hecho_id,
                tipo=relacion,
                peso=peso,
                capa_origen="pruebas",
                capa_destino="hechos",
                fila_hpn=fila.get("id", ""),
            )

        # ── Nodos norma + aristas ─────────────────────────────────────────────
        for norma in fila.get("normas", []):
            n_id = norma.get("id", "N?")
            G.add_node(
                n_id,
                tipo="norma",
                capa="normas",
                texto=norma.get("texto", ""),
                fuente=norma.get("fuente", "expediente"),
            )
            G.add_edge(
                hecho_id, n_id,
                tipo="activa",
                peso=1.0,
                capa_origen="hechos",
                capa_destino="normas",
                fila_hpn=fila.get("id", ""),
            )

        # ── Nodo riesgo si hay contradicciones ────────────────────────────────
        contradicciones = fila.get("contradicciones", [])
        if contradicciones:
            r_id = f"R-{fila.get('id', '?')}"
            G.add_node(
                r_id,
                tipo="riesgo",
                capa="riesgos",
                descripcion="; ".join(contradicciones),
            )
            G.add_edge(
                r_id, hecho_id,
                tipo="amenaza",
                peso=0.8,
                capa_origen="riesgos",
                capa_destino="hechos",
            )

    # ── Agregar actores si se pasan ───────────────────────────────────────────
    for actor in (actores or []):
        a_id = actor.get("id", "A?")
        G.add_node(
            a_id,
            tipo="actor",
            capa="actores",
            nombre=actor.get("nombre", ""),
            rol=actor.get("rol", ""),
        )

    return G


def grafo_a_dict(G: nx.DiGraph) -> dict:
    """Serializa el grafo a dict compatible con JSON (formato node_link_data)."""
    return nx.node_link_data(G)


def calcular_metricas_red(G: nx.DiGraph) -> dict:
    """
    Calcula métricas de red de la Tabla 4 del enunciado del proyecto.
    """
    if G.number_of_nodes() == 0:
        return {"error": "Grafo vacío", "total_nodos": 0}

    # Métricas básicas
    total_nodos   = G.number_of_nodes()
    total_aristas = G.number_of_edges()
    densidad      = round(nx.density(G), 4)

    # Grado de cada nodo
    grados = dict(G.degree())
    nodo_max_grado = max(grados, key=grados.get) if grados else None

    # Centralidad de intermediación (identifica puentes críticos)
    betweenness = nx.betweenness_centrality(G, normalized=True)
    top5_betweenness = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:5]

    # Puntos únicos de falla (betweenness > umbral)
    puntos_falla = [
        n for n, v in betweenness.items()
        if v > UMBRAL_BETWEENNESS_FALLA
    ]

    # Nodos aislados (sin conexiones)
    nodos_aislados = [n for n, d in grados.items() if d == 0]

    # Redundancia probatoria: pruebas que apuntan al mismo hecho
    redundancia = {}
    for u, v, data in G.edges(data=True):
        if data.get("tipo") == "soporta":
            redundancia[v] = redundancia.get(v, 0) + 1
    hechos_con_redundancia = {h: c for h, c in redundancia.items() if c > 1}

    # Fragilidad probatoria: impacto de eliminar cada prueba
    fragilidad = {}
    nodos_prueba = [n for n, d in G.nodes(data=True) if d.get("tipo") == "prueba"]
    score_base = total_aristas  # proxy simple del score total
    for prueba in nodos_prueba:
        G_temp = G.copy()
        G_temp.remove_node(prueba)
        score_sin = G_temp.number_of_edges()
        fragilidad[prueba] = round((score_base - score_sin) / max(score_base, 1), 3)

    prueba_mas_fragil = max(fragilidad, key=fragilidad.get) if fragilidad else None

    # Capas presentes
    capas = list({d.get("capa", "sin_capa") for _, d in G.nodes(data=True)})

    # Conteo por capa
    nodos_por_capa = {}
    for _, data in G.nodes(data=True):
        capa = data.get("capa", "sin_capa")
        nodos_por_capa[capa] = nodos_por_capa.get(capa, 0) + 1

    # Aristas por tipo de relación
    aristas_por_tipo = {}
    for _, _, data in G.edges(data=True):
        tipo = data.get("tipo", "desconocido")
        aristas_por_tipo[tipo] = aristas_por_tipo.get(tipo, 0) + 1

    return {
        # Básicas
        "total_nodos":            total_nodos,
        "total_aristas":          total_aristas,
        "densidad":               densidad,
        "capas":                  capas,
        "nodos_por_capa":         nodos_por_capa,
        "aristas_por_tipo":       aristas_por_tipo,
        # Centralidad
        "nodo_max_grado":         nodo_max_grado,
        "grado_max":              grados.get(nodo_max_grado, 0),
        "top5_betweenness":       top5_betweenness,
        # Fragilidad
        "puntos_unicos_de_falla": puntos_falla,
        "nodos_aislados":         nodos_aislados,
        "fragilidad_por_prueba":  fragilidad,
        "prueba_mas_fragil":      prueba_mas_fragil,
        # Redundancia
        "hechos_con_redundancia": hechos_con_redundancia,
        "redundancia_promedio":   round(
            sum(redundancia.values()) / max(len(redundancia), 1), 2
        ),
    }


def exportar_html(G: nx.DiGraph, output_path: str) -> None:
    """
    Exporta el grafo como HTML interactivo con PyVis.
    Se puede abrir directamente en el navegador.
    """
    try:
        from pyvis.network import Network
    except ImportError:
        print("PyVis no instalado. Omitiendo exportación HTML.")
        return

    # Colores por capa
    COLOR_CAPA = {
        "hechos":       "#4e79a7",
        "pruebas":      "#f28e2b",
        "normas":       "#e15759",
        "actores":      "#76b7b2",
        "riesgos":      "#edc948",
        "pretensiones": "#b07aa1",
        "argumentos":   "#59a14f",
        "tiempo":       "#ff9da7",
        "sin_capa":     "#bab0ac",
    }

    net = Network(height="700px", width="100%", directed=True,
                  notebook=False, bgcolor="#1a1a2e", font_color="white")

    for node_id, data in G.nodes(data=True):
        capa  = data.get("capa", "sin_capa")
        color = COLOR_CAPA.get(capa, "#bab0ac")
        label = str(node_id)
        title = (
            f"Tipo: {data.get('tipo', '?')}\n"
            f"Capa: {capa}\n"
            f"Texto: {data.get('texto', data.get('nombre', ''))[:80]}"
        )
        net.add_node(node_id, label=label, color=color, title=title, size=20)

    for u, v, data in G.edges(data=True):
        tipo  = data.get("tipo", "")
        peso  = data.get("peso", 0.5)
        color = "#e15759" if tipo == "contradice" else \
                "#edc948" if tipo == "amenaza"    else "#59a14f"
        net.add_edge(u, v, title=tipo, width=peso * 3, color=color, arrows="to")

    net.set_options("""
    {
      "physics": {
        "barnesHut": {"gravitationalConstant": -8000, "springLength": 200},
        "stabilization": {"iterations": 100}
      }
    }
    """)
    net.save_graph(output_path)
