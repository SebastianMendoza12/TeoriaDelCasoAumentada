"""
graph_tools.py
Construcción de la red compleja multicapa y cálculo de métricas de red.
Usa NetworkX. Sin LLM — determinístico y reproducible.

Capas implementadas (9, según Sección 6.2 del enunciado):
    hechos, pruebas, normas, precedentes, argumentos, riesgos,
    tiempo, actores, pretensiones.

Relaciones implementadas (Sección 6.3):
    soporta, contradice, activa, fundamenta, derrota, precede,
    distingue, riesgo.

Nota de diseño: las capas "argumentos" y "pretensiones" se sintetizan
deterministamente a partir de cada fila HPN (un argumento por fila,
una pretensión por elemento_juridico único), porque el enunciado no
exige un agente LLM adicional para producirlas — solo exige que la red
las represente como capas diferenciadas con métricas estructurales.
Las heurísticas "derrota" y "distingue" están marcadas explícitamente
en el código: no dependen de un LLM, se derivan de banderas ya
existentes en la matriz HPN (riesgo, estado, tipo de norma).
"""

import networkx as nx
from src.config import UMBRAL_BETWEENNESS_FALLA


def construir_grafo(
    matriz_hpn: list[dict],
    actores: list[dict] = None,
    normas_extraidas: list[dict] = None,
    cronologia: list[dict] = None,
) -> nx.DiGraph:
    """
    Convierte la Matriz HPN (+ datos auxiliares del estado) en un grafo
    dirigido tipado con 9 capas y 8 tipos de relación.

    Parámetros adicionales respecto a la versión anterior:
        normas_extraidas: state["normas"] — trae el campo 'tipo' que
            permite distinguir una norma común de un precedente
            jurisprudencial (la fila HPN no conserva ese campo).
        cronologia: state["cronologia"] — eventos con fecha, usados para
            construir la capa 'tiempo' y la relación 'precede'.
    """
    G = nx.DiGraph()
    actores = actores or []
    normas_extraidas = normas_extraidas or []
    cronologia = cronologia or []

    tipo_por_norma = {n.get("id"): n.get("tipo", "") for n in normas_extraidas}
    pretensiones_creadas = set()

    for fila in matriz_hpn:
        fila_id = fila.get("id", "?")
        hecho = fila.get("hecho", {})
        hecho_id = hecho.get("id", f"H-{fila_id}")

        # ── Capa hechos ──────────────────────────────────────────────────
        G.add_node(
            hecho_id, tipo="hecho", capa="hechos",
            texto=hecho.get("texto", ""), estado=fila.get("estado", "pendiente"),
            riesgo=fila.get("riesgo", "medio"), frag_id=hecho.get("frag_id", ""),
            pagina=hecho.get("pagina", 0),
        )

        # ── Capa pretensiones (una por elemento jurídico único) ──────────
        elemento = fila.get("elemento_juridico", "Elemento sin nombre")
        pretension_id = f"PR-{elemento[:30]}"
        if pretension_id not in pretensiones_creadas:
            G.add_node(pretension_id, tipo="pretension", capa="pretensiones",
                       texto=elemento)
            pretensiones_creadas.add(pretension_id)

        # ── Capa argumentos (uno por fila HPN) ────────────────────────────
        argumento_id = f"A-{fila_id}"
        G.add_node(argumento_id, tipo="argumento", capa="argumentos",
                   elemento_juridico=elemento, estado=fila.get("estado", ""))
        G.add_edge(hecho_id, argumento_id, tipo="fundamenta", peso=0.8,
                   capa_origen="hechos", capa_destino="argumentos", fila_hpn=fila_id)
        G.add_edge(argumento_id, pretension_id, tipo="fundamenta", peso=1.0,
                   capa_origen="argumentos", capa_destino="pretensiones", fila_hpn=fila_id)

        # ── Capa pruebas ───────────────────────────────────────────────────
        for prueba in fila.get("pruebas", []):
            p_id = prueba.get("id", "P?")
            G.add_node(p_id, tipo="prueba", capa="pruebas",
                       tipo_prueba=prueba.get("tipo", "desconocido"),
                       disponible=prueba.get("disponible", True))
            relacion = prueba.get("relacion", "soporta")
            peso = float(prueba.get("fuerza", 0.5))
            G.add_edge(p_id, hecho_id, tipo=relacion, peso=peso,
                       capa_origen="pruebas", capa_destino="hechos", fila_hpn=fila_id)

        # ── Capa normas / precedentes ───────────────────────────────────
        for norma in fila.get("normas", []):
            n_id = norma.get("id", "N?")
            es_precedente = tipo_por_norma.get(n_id) == "precedente_jurisprudencial"
            capa_norma = "precedentes" if es_precedente else "normas"
            G.add_node(n_id, tipo="precedente" if es_precedente else "norma",
                       capa=capa_norma, texto=norma.get("texto", ""),
                       fuente=norma.get("fuente", "expediente"))
            G.add_edge(hecho_id, n_id, tipo="activa", peso=1.0,
                       capa_origen="hechos", capa_destino=capa_norma, fila_hpn=fila_id)
            G.add_edge(n_id, argumento_id, tipo="fundamenta", peso=0.9,
                       capa_origen=capa_norma, capa_destino="argumentos", fila_hpn=fila_id)

            # Heurística determinística "distingue": precedente que
            # sostiene una fila de riesgo alto/crítico puede ser
            # distinguido por el juez (no requiere LLM ni simulación
            # adicional — se marca como riesgo estructural visible).
            if es_precedente and fila.get("riesgo") in {"alto", "critico"}:
                dist_id = f"DIST-{fila_id}"
                G.add_node(dist_id, tipo="riesgo", capa="riesgos",
                           descripcion=f"Posible distinción del precedente {n_id}")
                G.add_edge(dist_id, n_id, tipo="distingue", peso=0.6,
                           capa_origen="riesgos", capa_destino=capa_norma, fila_hpn=fila_id)

        # ── Capa riesgos: contradicciones declaradas en la fila ──────────
        contradicciones = fila.get("contradicciones", [])
        if contradicciones:
            r_id = f"R-{fila_id}"
            G.add_node(r_id, tipo="riesgo", capa="riesgos",
                       descripcion="; ".join(contradicciones))
            G.add_edge(r_id, hecho_id, tipo="riesgo", peso=0.8,
                       capa_origen="riesgos", capa_destino="hechos", fila_hpn=fila_id)

        # Heurística determinística "derrota": filas marcadas por el
        # hpn_builder/auditor como riesgo_adversarial o riesgo crítico
        # representan una excepción/ataque que tumba la conclusión.
        if fila.get("estado") == "riesgo_adversarial" or fila.get("riesgo") == "critico":
            exc_id = f"EXC-{fila_id}"
            G.add_node(exc_id, tipo="riesgo", capa="riesgos",
                       descripcion=f"Excepción/ataque que puede derrotar {argumento_id}")
            G.add_edge(exc_id, argumento_id, tipo="derrota", peso=0.9,
                       capa_origen="riesgos", capa_destino="argumentos", fila_hpn=fila_id)

    # ── Capa actores ────────────────────────────────────────────────────
    for actor in actores:
        a_id = actor.get("id", "A?")
        G.add_node(a_id, tipo="actor", capa="actores",
                   nombre=actor.get("nombre", ""), rol=actor.get("rol", ""))

    # ── Capa tiempo (relación 'precede') ────────────────────────────────
    eventos_ordenados = sorted(
        [e for e in cronologia if e.get("fecha")],
        key=lambda e: str(e.get("fecha", "")),
    )
    nodo_anterior = None
    for i, evento in enumerate(eventos_ordenados):
        t_id = f"T-{i:03d}"
        G.add_node(t_id, tipo="tiempo", capa="tiempo",
                   fecha=evento.get("fecha", ""), evento=evento.get("evento", ""),
                   actor=evento.get("actor", ""))
        if nodo_anterior:
            G.add_edge(nodo_anterior, t_id, tipo="precede", peso=1.0,
                       capa_origen="tiempo", capa_destino="tiempo")
        nodo_anterior = t_id

        frag = evento.get("frag_id")
        if frag:
            for nodo_id, data in list(G.nodes(data=True)):
                if data.get("tipo") == "hecho" and data.get("frag_id") == frag:
                    G.add_edge(t_id, nodo_id, tipo="precede", peso=0.5,
                               capa_origen="tiempo", capa_destino="hechos")

    return G


def grafo_a_dict(G: nx.DiGraph) -> dict:
    """Serializa el grafo a dict compatible con JSON (formato node_link_data)."""
    return nx.node_link_data(G, edges="links")


def calcular_metricas_red(G: nx.DiGraph) -> dict:
    """
    Calcula todas las métricas de la Tabla 4 del enunciado del proyecto.
    """
    if G.number_of_nodes() == 0:
        return {"error": "Grafo vacío", "total_nodos": 0}

    total_nodos   = G.number_of_nodes()
    total_aristas = G.number_of_edges()
    densidad      = round(nx.density(G), 4)

    grados = dict(G.degree())
    nodo_max_grado = max(grados, key=grados.get) if grados else None

    betweenness = nx.betweenness_centrality(G, normalized=True)
    top5_betweenness = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:5]
    puntos_falla = [n for n, v in betweenness.items() if v > UMBRAL_BETWEENNESS_FALLA]
    nodos_aislados = [n for n, d in grados.items() if d == 0]

    redundancia = {}
    for u, v, data in G.edges(data=True):
        if data.get("tipo") == "soporta":
            redundancia[v] = redundancia.get(v, 0) + 1
    hechos_con_redundancia = {h: c for h, c in redundancia.items() if c > 1}

    fragilidad = {}
    nodos_prueba = [n for n, d in G.nodes(data=True) if d.get("tipo") == "prueba"]
    score_base = total_aristas
    for prueba in nodos_prueba:
        G_temp = G.copy()
        G_temp.remove_node(prueba)
        score_sin = G_temp.number_of_edges()
        fragilidad[prueba] = round((score_base - score_sin) / max(score_base, 1), 3)
    prueba_mas_fragil = max(fragilidad, key=fragilidad.get) if fragilidad else None

    capas = list({d.get("capa", "sin_capa") for _, d in G.nodes(data=True)})
    nodos_por_capa = {}
    for _, data in G.nodes(data=True):
        capa = data.get("capa", "sin_capa")
        nodos_por_capa[capa] = nodos_por_capa.get(capa, 0) + 1

    aristas_por_tipo = {}
    for _, _, data in G.edges(data=True):
        tipo = data.get("tipo", "desconocido")
        aristas_por_tipo[tipo] = aristas_por_tipo.get(tipo, 0) + 1

    # ── Métricas adicionales del Cuadro 4 (requieren las capas nuevas) ────

    nodos_argumento  = [n for n, d in G.nodes(data=True) if d.get("tipo") == "argumento"]
    nodos_pretension = [n for n, d in G.nodes(data=True) if d.get("tipo") == "pretension"]
    nodos_hecho      = [n for n, d in G.nodes(data=True) if d.get("tipo") == "hecho"]
    total_argumentos = max(len(nodos_argumento), 1)

    # Cobertura de rutas jurídicas: % de argumentos con hecho Y norma/precedente
    argumentos_completos = 0
    for arg in nodos_argumento:
        tipos_predecesores = {G.nodes[p].get("tipo") for p in G.predecessors(arg)}
        if "hecho" in tipos_predecesores and tipos_predecesores & {"norma", "precedente"}:
            argumentos_completos += 1
    cobertura_rutas_juridicas = round(argumentos_completos / total_argumentos, 3)

    # Densidad de soporte: aristas 'soporta' por hecho
    densidad_de_soporte = round(
        aristas_por_tipo.get("soporta", 0) / max(len(nodos_hecho), 1), 3
    )

    # Robustez adversarial / riesgo de derrotabilidad
    argumentos_derrotados = {
        v for u, v, d in G.edges(data=True)
        if d.get("tipo") == "derrota" and G.nodes[v].get("tipo") == "argumento"
    }
    riesgo_de_derrotabilidad = round(len(argumentos_derrotados) / total_argumentos, 3)
    robustez_adversarial = round(1 - riesgo_de_derrotabilidad, 3)

    # Consistencia temporal: ¿la subred 'precede' es acíclica?
    aristas_precede = [(u, v) for u, v, d in G.edges(data=True) if d.get("tipo") == "precede"]
    G_tiempo = nx.DiGraph(aristas_precede)
    consistencia_temporal = (
        nx.is_directed_acyclic_graph(G_tiempo) if G_tiempo.number_of_nodes() else True
    )

    # Dependencia jurisprudencial: % de argumentos sostenidos por un precedente
    argumentos_con_precedente = {
        v for u, v, d in G.edges(data=True)
        if d.get("tipo") == "fundamenta" and G.nodes[u].get("tipo") == "precedente"
    }
    dependencia_jurisprudencial = round(len(argumentos_con_precedente) / total_argumentos, 3)

    # Trazabilidad de ruta: % de argumentos cuyo hecho de origen tiene frag_id
    argumentos_trazables = 0
    for arg in nodos_argumento:
        for p in G.predecessors(arg):
            if G.nodes[p].get("tipo") == "hecho" and G.nodes[p].get("frag_id"):
                argumentos_trazables += 1
                break
    trazabilidad_de_ruta = round(argumentos_trazables / total_argumentos, 3)

    # Proximidad a la pretensión: distancia promedio prueba → pretensión
    distancias = []
    for p in nodos_prueba:
        for pretension in nodos_pretension:
            try:
                distancias.append(nx.shortest_path_length(G, source=p, target=pretension))
                break
            except nx.NetworkXNoPath:
                continue
    proximidad_a_pretension = round(sum(distancias) / len(distancias), 2) if distancias else None

    # Índice de contradicción a nivel de red
    indice_contradiccion_red = (
        aristas_por_tipo.get("contradice", 0) + aristas_por_tipo.get("derrota", 0)
    )

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
        # Nuevas (Cuadro 4 completo)
        "cobertura_rutas_juridicas":   cobertura_rutas_juridicas,
        "densidad_de_soporte":         densidad_de_soporte,
        "robustez_adversarial":        robustez_adversarial,
        "riesgo_de_derrotabilidad":    riesgo_de_derrotabilidad,
        "consistencia_temporal":       consistencia_temporal,
        "dependencia_jurisprudencial": dependencia_jurisprudencial,
        "trazabilidad_de_ruta":        trazabilidad_de_ruta,
        "proximidad_a_pretension":     proximidad_a_pretension,
        "indice_contradiccion_red":    indice_contradiccion_red,
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

    COLOR_CAPA = {
        "hechos":       "#4e79a7",
        "pruebas":      "#f28e2b",
        "normas":       "#e15759",
        "precedentes":  "#af7aa1",
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
            f"Texto: {str(data.get('texto', data.get('nombre', '')))[:80]}"
        )
        net.add_node(node_id, label=label, color=color, title=title, size=20)

    for u, v, data in G.edges(data=True):
        tipo  = data.get("tipo", "")
        peso  = data.get("peso", 0.5)
        color = ("#e15759" if tipo in ("contradice", "derrota") else
                 "#edc948" if tipo in ("riesgo", "distingue")    else "#59a14f")
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