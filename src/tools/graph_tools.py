# src/tools/graph_tools.py
import networkx as nx
from src.config import UMBRAL_FRAGILIDAD


def construir_grafo(matriz: list[dict], actores: list[dict] = None) -> dict:
    """
    Convierte la matriz HPN en un grafo dirigido y tipado (red multicapa).
    Cada nodo lleva atributos: tipo (hecho/prueba/norma/actor) y capa.
    Cada arista lleva: tipo de relación, peso, fuente.
    Devuelve node_link_data serializable a JSON.
    """
    G = nx.DiGraph()

    # ── Nodos y aristas desde la matriz HPN ──────────────────────
    for fila in matriz:
        h = fila.get("hecho", {})
        hecho_id = h.get("id", f"H-{fila.get('id','?')}")

        G.add_node(hecho_id,
                   tipo="hecho",
                   capa="hechos",
                   texto=h.get("texto", ""),
                   estado=fila.get("estado", "pendiente"),
                   riesgo=fila.get("riesgo", "medio"))

        for prueba in fila.get("pruebas", []):
            p_id = prueba.get("id", "P?")
            if not G.has_node(p_id):
                G.add_node(p_id,
                           tipo="prueba",
                           capa="pruebas",
                           tipo_prueba=prueba.get("tipo", ""),
                           descripcion=prueba.get("descripcion", ""))

            relacion = prueba.get("relacion", "soporta")
            peso     = prueba.get("fuerza", 0.5)
            G.add_edge(p_id, hecho_id,
                       tipo=relacion,
                       peso=peso,
                       fuente=str(fila.get("fuente_expediente", {})))

        for norma in fila.get("normas", []):
            n_id = norma.get("id", "N?")
            if not G.has_node(n_id):
                G.add_node(n_id,
                           tipo="norma",
                           capa="normas",
                           texto=norma.get("texto", ""),
                           origen=norma.get("fuente", "expediente"))
            G.add_edge(hecho_id, n_id,
                       tipo="activa",
                       peso=1.0,
                       fuente="hpn")

    # ── Actores como nodos de capa "actores" ─────────────────────
    for actor in (actores or []):
        a_id = actor.get("id", "A?")
        if not G.has_node(a_id):
            G.add_node(a_id,
                       tipo="actor",
                       capa="actores",
                       nombre=actor.get("nombre", ""),
                       rol=actor.get("rol", ""))

    return nx.node_link_data(G)


def calcular_metricas_red(grafo_data: dict) -> dict:
    """
    Calcula las métricas de red de la sección 6.5 del enunciado.
    No usa LLM — NetworkX puro.
    """
    G = nx.node_link_graph(grafo_data)

    if len(G.nodes) == 0:
        return {"error": "El grafo está vacío"}

    betweenness = nx.betweenness_centrality(G)
    grado       = dict(G.degree())

    top5_centrales = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:5]

    puntos_falla = [n for n, v in betweenness.items() if v > UMBRAL_FRAGILIDAD]

    aislados = [n for n, d in grado.items() if d == 0]

    # Fragilidad: nodos prueba con betweenness alto
    pruebas_fragiles = [
        n for n in G.nodes
        if G.nodes[n].get("tipo") == "prueba" and betweenness.get(n, 0) > UMBRAL_FRAGILIDAD
    ]

    # Cobertura de rutas: hechos que tienen al menos una prueba que los soporta
    hechos = [n for n in G.nodes if G.nodes[n].get("tipo") == "hecho"]
    hechos_con_soporte = [
        h for h in hechos
        if any(G.edges[e].get("tipo") == "soporta"
               for e in G.in_edges(h))
    ]

    cobertura_rutas = (
        round(len(hechos_con_soporte) / len(hechos), 3)
        if hechos else 0
    )

    # Redundancia: hechos con más de una prueba de soporte
    redundancia = {
        h: sum(1 for e in G.in_edges(h) if G.edges[e].get("tipo") == "soporta")
        for h in hechos
    }

    return {
        "total_nodos":              G.number_of_nodes(),
        "total_aristas":            G.number_of_edges(),
        "densidad":                 round(nx.density(G), 4),
        "nodo_mas_central":         top5_centrales[0][0] if top5_centrales else None,
        "top5_betweenness":         top5_centrales,
        "puntos_unicos_de_falla":   puntos_falla,
        "pruebas_fragiles":         pruebas_fragiles,
        "nodos_aislados":           aislados,
        "cobertura_rutas_juridicas": cobertura_rutas,
        "redundancia_probatoria":   redundancia,
    }