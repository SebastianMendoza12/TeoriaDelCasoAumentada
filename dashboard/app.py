"""
app.py — Dashboard del Abogado
Streamlit con 6 secciones: vista general, matriz HPN, red multicapa,
métricas, simulador y alertas.

Uso:
    streamlit run dashboard/app.py
"""

import json
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Configuración de página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Teoría del Caso Aumentada",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


# ── Helpers ───────────────────────────────────────────────────────────────────

@st.cache_data
def cargar_json(nombre: str):
    ruta = OUTPUT_DIR / nombre
    if not ruta.exists():
        return None
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def badge_estado(estado: str) -> str:
    colores = {
        "completo":           "🟢",
        "parcial":            "🟡",
        "controvertido":      "🟠",
        "debil":              "🔴",
        "vacio_critico":      "⛔",
        "riesgo_adversarial": "🔴",
        "bloqueado":          "⬛",
        "pendiente":          "⚪",
    }
    return f"{colores.get(estado, '❓')} {estado}"


def badge_riesgo(riesgo: str) -> str:
    colores = {
        "bajo":    "🟢 bajo",
        "medio":   "🟡 medio",
        "alto":    "🔴 alto",
        "critico": "⛔ crítico",
    }
    return colores.get(riesgo, riesgo)


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/fluency/96/scales.png", width=64)
st.sidebar.title("⚖️ Teoría del Caso Aumentada")
st.sidebar.caption("Sistema multiagente de apoyo al litigio\nUniversidad de Pamplona 2026-1")
st.sidebar.divider()

seccion = st.sidebar.radio(
    "Sección",
    [
        "🏠 Vista General",
        "📋 Matriz HPN",
        "🕸️ Red Multicapa",
        "📊 Métricas",
        "🎭 Simulador",
        "🚨 Alertas y Auditoría",
    ],
)

st.sidebar.divider()
st.sidebar.warning(
    "⚠️ La decisión jurídica final permanece en cabeza humana. "
    "Este sistema apoya la preparación del abogado, no sustituye su criterio."
)

# ── Cargar datos ──────────────────────────────────────────────────────────────
datos_hpn       = cargar_json("matriz_hpn.json")
datos_grafo     = cargar_json("grafo.json")
datos_metricas  = cargar_json("metricas.json")
datos_escenarios= cargar_json("escenarios.json")

hay_datos = datos_hpn is not None

if not hay_datos:
    st.title("⚖️ Teoría del Caso Aumentada")
    st.error("No se encontraron resultados en la carpeta `output/`.")
    st.info(
        "**Paso 1:** Copia el expediente en `data/input/expediente.pdf`\n\n"
        "**Paso 2:** Ejecuta el sistema: `python src/graph.py`\n\n"
        "**Paso 3:** Recarga esta página."
    )
    st.stop()

matriz = datos_hpn.get("filas", [])
case_id = datos_hpn.get("case_id", "sin ID")

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 1: VISTA GENERAL
# ══════════════════════════════════════════════════════════════════════════════
if seccion == "🏠 Vista General":
    st.title("🏠 Vista General del Caso")
    st.caption(f"Case ID: `{case_id}` | Generado: {datos_hpn.get('timestamp', '?')[:19]}")

    total = len(matriz)
    if total == 0:
        st.warning("La Matriz HPN está vacía. Verifica que el sistema procesó correctamente el PDF.")
        st.stop()

    # Tarjetas de resumen
    col1, col2, col3, col4, col5 = st.columns(5)
    completas     = sum(1 for f in matriz if f.get("estado") == "completo")
    parciales     = sum(1 for f in matriz if f.get("estado") in {"parcial", "controvertido"})
    debiles       = sum(1 for f in matriz if f.get("estado") in {"debil", "riesgo_adversarial"})
    criticas      = sum(1 for f in matriz if f.get("estado") == "vacio_critico")
    pendientes    = sum(1 for f in matriz if f.get("revision_humana") == "sin_revisar")

    col1.metric("Total filas HPN", total)
    col2.metric("Completas ✅",  completas,  f"{round(completas/total*100)}%")
    col3.metric("Parciales 🟡",  parciales)
    col4.metric("Débiles 🔴",    debiles)
    col5.metric("Vacíos críticos ⛔", criticas)

    st.divider()

    # Gráfico de estados
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Distribución de estados")
        conteo_estados = {}
        for f in matriz:
            e = f.get("estado", "desconocido")
            conteo_estados[e] = conteo_estados.get(e, 0) + 1
        df_estados = pd.DataFrame(
            list(conteo_estados.items()), columns=["Estado", "Filas"]
        ).sort_values("Filas", ascending=False)
        fig_estados = px.bar(
            df_estados, x="Estado", y="Filas",
            color="Estado",
            color_discrete_map={
                "completo": "#59a14f",
                "parcial": "#f28e2b",
                "controvertido": "#e15759",
                "debil": "#9c755f",
                "vacio_critico": "#bab0ac",
                "pendiente": "#76b7b2",
            },
        )
        fig_estados.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig_estados, use_container_width=True)

    with col_b:
        st.subheader("Distribución de riesgo")
        conteo_riesgo = {}
        for f in matriz:
            r = f.get("riesgo", "desconocido")
            conteo_riesgo[r] = conteo_riesgo.get(r, 0) + 1
        df_riesgo = pd.DataFrame(
            list(conteo_riesgo.items()), columns=["Riesgo", "Filas"]
        )
        fig_riesgo = px.pie(
            df_riesgo, names="Riesgo", values="Filas",
            color="Riesgo",
            color_discrete_map={
                "bajo": "#59a14f", "medio": "#f28e2b",
                "alto": "#e15759", "critico": "#b07aa1",
            },
            hole=0.4,
        )
        fig_riesgo.update_layout(height=300)
        st.plotly_chart(fig_riesgo, use_container_width=True)

    # Indicador de preparación
    st.subheader("Indicador de preparación del caso")
    metricas_hpn = (datos_metricas or {}).get("hpn", {})
    cob_prob = metricas_hpn.get("cobertura_probatoria", 0)
    cob_norm = metricas_hpn.get("cobertura_normativa", 0)
    traza    = metricas_hpn.get("trazabilidad", 0)
    score_preparacion = round((cob_prob + cob_norm + traza) / 3, 2)

    col_x, col_y = st.columns([1, 2])
    with col_x:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score_preparacion * 100,
            title={"text": "Score de preparación"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#4e79a7"},
                "steps": [
                    {"range": [0, 40],  "color": "#e15759"},
                    {"range": [40, 70], "color": "#f28e2b"},
                    {"range": [70, 100],"color": "#59a14f"},
                ],
                "threshold": {"line": {"color": "red", "width": 4}, "value": 70},
            },
        ))
        fig_gauge.update_layout(height=250)
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_y:
        st.markdown(f"""
| Indicador | Valor |
|-----------|-------|
| Cobertura probatoria | `{cob_prob:.0%}` |
| Cobertura normativa | `{cob_norm:.0%}` |
| Trazabilidad de fuentes | `{traza:.0%}` |
| Filas sin revisión humana | `{pendientes}` de `{total}` |
""")
        if score_preparacion < 0.5:
            st.error("⛔ Caso en estado CRÍTICO — muchos vacíos sin resolver.")
        elif score_preparacion < 0.7:
            st.warning("⚠️ Caso en estado PARCIAL — reforzar antes de audiencia.")
        else:
            st.success("✅ Caso en buen estado de preparación.")


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 2: MATRIZ HPN
# ══════════════════════════════════════════════════════════════════════════════
elif seccion == "📋 Matriz HPN":
    st.title("📋 Matriz HPN — Hecho · Prueba · Norma")
    st.caption("Filtra, revisa y exporta la matriz central de la teoría del caso.")

    if not matriz:
        st.warning("Matriz vacía.")
        st.stop()

    # Filtros
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        estados_disp = list({f.get("estado", "") for f in matriz})
        filtro_estado = st.multiselect("Estado", estados_disp, default=estados_disp)
    with col_f2:
        riesgos_disp = list({f.get("riesgo", "") for f in matriz})
        filtro_riesgo = st.multiselect("Riesgo", riesgos_disp, default=riesgos_disp)
    with col_f3:
        filtro_texto = st.text_input("Buscar en elemento jurídico o acción", "")

    # Aplicar filtros
    matriz_filtrada = [
        f for f in matriz
        if f.get("estado") in filtro_estado
        and f.get("riesgo") in filtro_riesgo
        and filtro_texto.lower() in (
            f.get("elemento_juridico", "") + f.get("accion_sugerida", "")
        ).lower()
    ]

    st.caption(f"Mostrando {len(matriz_filtrada)} de {len(matriz)} filas")

    # Tabla resumen
    filas_tabla = []
    for f in matriz_filtrada:
        hecho = f.get("hecho", {})
        filas_tabla.append({
            "ID":                  f.get("id", ""),
            "Elemento jurídico":   f.get("elemento_juridico", ""),
            "Hecho":               hecho.get("texto", "") if isinstance(hecho, dict) else str(hecho),
            "Pruebas":             len(f.get("pruebas", [])),
            "Normas":              len(f.get("normas", [])),
            "Estado":              f.get("estado", ""),
            "Riesgo":              f.get("riesgo", ""),
            "Revisión":            f.get("revision_humana", "sin_revisar"),
            "Acción sugerida":     f.get("accion_sugerida", ""),
        })

    df = pd.DataFrame(filas_tabla)
    st.dataframe(df, use_container_width=True, height=350)

    # Exportar CSV
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Descargar Matriz HPN (CSV)",
        data=csv,
        file_name="matriz_hpn.csv",
        mime="text/csv",
    )

    # Detalle de fila seleccionada
    st.divider()
    st.subheader("Detalle de fila HPN")
    ids_disponibles = [f.get("id", f"fila-{i}") for i, f in enumerate(matriz_filtrada)]
    if ids_disponibles:
        id_seleccionado = st.selectbox("Selecciona una fila para ver detalle", ids_disponibles)
        fila = next((f for f in matriz_filtrada if f.get("id") == id_seleccionado), None)

        if fila:
            hecho = fila.get("hecho", {})
            col_d1, col_d2 = st.columns(2)

            with col_d1:
                st.markdown(f"**Elemento jurídico:** {fila.get('elemento_juridico', '')}")
                st.markdown(f"**Hecho:** {hecho.get('texto', '') if isinstance(hecho, dict) else hecho}")
                fuente = fila.get("fuente_expediente", {})
                st.markdown(f"**Fuente:** página {fuente.get('pagina', '?')} | `{fuente.get('frag_id', '?')}`")
                st.markdown(f"**Estado:** {badge_estado(fila.get('estado', ''))}")
                st.markdown(f"**Riesgo:** {badge_riesgo(fila.get('riesgo', ''))}")
                st.markdown(f"**Revisión humana:** {fila.get('revision_humana', '')}")

            with col_d2:
                st.markdown("**Pruebas:**")
                for p in fila.get("pruebas", []):
                    icono = "✅" if p.get("relacion") == "soporta" else "❌"
                    st.markdown(
                        f"  {icono} `{p.get('id')}` — {p.get('tipo', '')} "
                        f"| fuerza: {p.get('fuerza', '?')} | {p.get('relacion', '')}"
                    )

                st.markdown("**Normas:**")
                for n in fila.get("normas", []):
                    st.markdown(f"  📜 `{n.get('id')}` — {n.get('texto', '')} ({n.get('fuente', '')})")

                if fila.get("contradicciones"):
                    st.markdown("**Contradicciones:**")
                    for c in fila["contradicciones"]:
                        st.markdown(f"  ⚡ {c}")

            st.info(f"💡 **Acción sugerida:** {fila.get('accion_sugerida', '')}")

            if fila.get("errores_validacion"):
                st.error("Advertencias de validación:\n" +
                         "\n".join(f"• {e}" for e in fila["errores_validacion"]))


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 3: RED MULTICAPA
# ══════════════════════════════════════════════════════════════════════════════
elif seccion == "🕸️ Red Multicapa":
    st.title("🕸️ Red Compleja Multicapa")

    red_html = Path(__file__).resolve().parent.parent / "output" / "red_multicapa.html"

    if red_html.exists():
        st.caption("Visualización interactiva generada con PyVis. Puedes arrastrar nodos y hacer zoom.")
        with open(red_html, encoding="utf-8") as f:
            html_content = f.read()
        st.components.v1.html(html_content, height=700, scrolling=True)
    else:
        st.warning("No se encontró el archivo `output/red_multicapa.html`. "
                   "Asegúrate de tener instalado PyVis (`pip install pyvis`) y vuelve a ejecutar el sistema.")

    # Estadísticas del grafo
    if datos_grafo:
        st.divider()
        st.subheader("Estadísticas de la red")
        nodos  = datos_grafo.get("nodes", [])
        aristas = datos_grafo.get("links", [])

        col1, col2, col3 = st.columns(3)
        col1.metric("Total nodos", len(nodos))
        col2.metric("Total aristas", len(aristas))

        capas = list({n.get("capa", "sin_capa") for n in nodos})
        col3.metric("Capas", len(capas))

        # Nodos por capa
        conteo_capas = {}
        for n in nodos:
            c = n.get("capa", "sin_capa")
            conteo_capas[c] = conteo_capas.get(c, 0) + 1

        df_capas = pd.DataFrame(
            list(conteo_capas.items()), columns=["Capa", "Nodos"]
        ).sort_values("Nodos", ascending=False)
        fig = px.bar(df_capas, x="Capa", y="Nodos",
                     title="Nodos por capa", color="Capa")
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)

        # Aristas por tipo
        conteo_tipos = {}
        for a in aristas:
            t = a.get("tipo", "desconocido")
            conteo_tipos[t] = conteo_tipos.get(t, 0) + 1
        if conteo_tipos:
            df_tipos = pd.DataFrame(
                list(conteo_tipos.items()), columns=["Tipo de relación", "Aristas"]
            )
            fig2 = px.pie(df_tipos, names="Tipo de relación", values="Aristas",
                          title="Aristas por tipo de relación", hole=0.3)
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)

        # Exportar grafo
        st.download_button(
            "⬇️ Descargar grafo (JSON)",
            data=json.dumps(datos_grafo, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="grafo_multicapa.json",
            mime="application/json",
        )


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 4: MÉTRICAS
# ══════════════════════════════════════════════════════════════════════════════
elif seccion == "📊 Métricas":
    st.title("📊 Panel de Métricas")
    st.caption("Indicadores de cobertura, fragilidad, centralidad y robustez adversarial.")

    if not datos_metricas:
        st.warning("No se encontraron métricas.")
        st.stop()

    metricas_hpn = datos_metricas.get("hpn", {})
    metricas_red = datos_metricas.get("red", {})

    # ── Métricas HPN ──────────────────────────────────────────────────────────
    st.subheader("📋 Métricas de la Matriz HPN")

    if metricas_hpn and "total_filas" in metricas_hpn:
        cols = st.columns(4)
        cols[0].metric("Cobertura probatoria",
                       f"{metricas_hpn.get('cobertura_probatoria', 0):.0%}")
        cols[1].metric("Cobertura normativa",
                       f"{metricas_hpn.get('cobertura_normativa', 0):.0%}")
        cols[2].metric("Cobertura elementos jurídicos",
                       f"{metricas_hpn.get('cobertura_elementos_juridicos', 0):.0%}")
        cols[3].metric("Trazabilidad",
                       f"{metricas_hpn.get('trazabilidad', 0):.0%}")

        cols2 = st.columns(4)
        cols2[0].metric("Vacíos críticos",
                        metricas_hpn.get("vacios_criticos", 0),
                        f"{metricas_hpn.get('pct_vacios_criticos', 0):.0%}")
        cols2[1].metric("Contradicciones",
                        metricas_hpn.get("indice_contradiccion", 0))
        cols2[2].metric("Filas débiles",
                        metricas_hpn.get("filas_debiles", 0))
        cols2[3].metric("Acciones pendientes",
                        metricas_hpn.get("acciones_pendientes", 0))

        # Gráfico radar de cobertura
        categorias = ["Probatoria", "Normativa", "Elem. jurídicos", "Trazabilidad"]
        valores = [
            metricas_hpn.get("cobertura_probatoria", 0),
            metricas_hpn.get("cobertura_normativa", 0),
            metricas_hpn.get("cobertura_elementos_juridicos", 0),
            metricas_hpn.get("trazabilidad", 0),
        ]
        fig_radar = go.Figure(go.Scatterpolar(
            r=valores + [valores[0]],
            theta=categorias + [categorias[0]],
            fill="toself",
            fillcolor="rgba(78, 121, 167, 0.3)",
            line=dict(color="#4e79a7"),
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            title="Radar de cobertura",
            height=350,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    # ── Métricas de Red ───────────────────────────────────────────────────────
    st.divider()
    st.subheader("🕸️ Métricas de la Red Multicapa")

    if metricas_red and "total_nodos" in metricas_red:
        cols3 = st.columns(4)
        cols3[0].metric("Nodos",   metricas_red.get("total_nodos", 0))
        cols3[1].metric("Aristas", metricas_red.get("total_aristas", 0))
        cols3[2].metric("Densidad", metricas_red.get("densidad", 0))
        cols3[3].metric("Puntos de falla",
                        len(metricas_red.get("puntos_unicos_de_falla", [])))

        # Tabla top 5 betweenness
        top5 = metricas_red.get("top5_betweenness", [])
        if top5:
            st.markdown("**Top 5 nodos por centralidad de intermediación (puentes críticos):**")
            df_top5 = pd.DataFrame(top5, columns=["Nodo", "Betweenness"])
            df_top5["Betweenness"] = df_top5["Betweenness"].round(3)
            st.dataframe(df_top5, use_container_width=True)

        # Puntos únicos de falla
        puntos_falla = metricas_red.get("puntos_unicos_de_falla", [])
        if puntos_falla:
            st.error(f"⚠️ Puntos únicos de falla detectados: `{', '.join(puntos_falla)}`  \n"
                     "Estos nodos son críticos — su eliminación colapsa rutas principales.")

        # Fragilidad por prueba
        fragilidad = metricas_red.get("fragilidad_por_prueba", {})
        if fragilidad:
            df_frag = pd.DataFrame(
                list(fragilidad.items()), columns=["Prueba", "Fragilidad"]
            ).sort_values("Fragilidad", ascending=False)
            fig_frag = px.bar(df_frag, x="Prueba", y="Fragilidad",
                              title="Fragilidad por prueba (impacto si se elimina)",
                              color="Fragilidad", color_continuous_scale="Reds")
            fig_frag.update_layout(height=300)
            st.plotly_chart(fig_frag, use_container_width=True)

        prueba_fragil = metricas_red.get("prueba_mas_fragil")
        if prueba_fragil:
            st.warning(f"🔍 Prueba más frágil: `{prueba_fragil}` — reforzar con prueba redundante.")

    # Exportar métricas
    st.download_button(
        "⬇️ Descargar métricas (JSON)",
        data=json.dumps(datos_metricas, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name="metricas.json",
        mime="application/json",
    )


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 5: SIMULADOR
# ══════════════════════════════════════════════════════════════════════════════
elif seccion == "🎭 Simulador":
    st.title("🎭 Simulador de Escenarios Procesales")
    st.caption(
        "Laboratorio estratégico: perturbaciones sobre la teoría del caso para "
        "identificar qué se rompe y qué debe reforzarse."
    )
    st.warning(
        "⚠️ Los escenarios NO predicen el resultado judicial. "
        "Analizan efectos estructurales sobre la teoría. Requieren revisión humana."
    )

    escenarios = (datos_escenarios or {}).get("escenarios", [])
    if not escenarios:
        st.warning("No se encontraron escenarios simulados.")
        st.stop()

    for esc in escenarios:
        analisis = esc.get("analisis", {})
        nivel    = analisis.get("nivel_impacto", "desconocido")

        icono = {"bajo": "🟢", "medio": "🟡", "alto": "🔴", "critico": "⛔"}.get(nivel, "❓")

        with st.expander(f"{icono} {esc['id']}: {esc['nombre']}", expanded=False):
            st.markdown(f"**Supuesto explícito:** {esc.get('supuesto_explicito', '')}")

            if esc.get("prueba_eliminada_s1"):
                st.info(f"Prueba eliminada en S1: `{esc['prueba_eliminada_s1']}`")

            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown("**Métricas ANTES de la perturbación:**")
                antes = esc.get("metricas_antes", {})
                if antes:
                    st.markdown(f"- Cobertura probatoria: `{antes.get('cobertura_probatoria', '?')}`")
                    st.markdown(f"- Vacíos críticos: `{antes.get('vacios_criticos', '?')}`")
                    st.markdown(f"- Trazabilidad: `{antes.get('trazabilidad', '?')}`")
                else:
                    st.markdown("_No disponible_")

            with col_b:
                st.markdown("**Métricas DESPUÉS de la perturbación:**")
                despues = esc.get("metricas_despues", {})
                if despues:
                    st.markdown(f"- Cobertura probatoria: `{despues.get('cobertura_probatoria', '?')}`")
                    st.markdown(f"- Vacíos críticos: `{despues.get('vacios_criticos', '?')}`")
                    st.markdown(f"- Trazabilidad: `{despues.get('trazabilidad', '?')}`")
                else:
                    st.markdown("_Solo disponible para S1_")

            st.markdown(f"**Nivel de impacto:** {icono} `{nivel}`")

            if analisis.get("hechos_afectados"):
                st.markdown(f"**Hechos afectados:** `{', '.join(analisis['hechos_afectados'])}`")

            if analisis.get("rutas_debilitadas"):
                st.markdown("**Rutas debilitadas:**")
                for r in analisis["rutas_debilitadas"]:
                    st.markdown(f"  - {r}")

            st.success(f"💡 **Acción sugerida:** {analisis.get('accion_sugerida', '')}")

            if analisis.get("incertidumbre"):
                st.caption(f"ℹ️ Incertidumbre: {analisis['incertidumbre']}")

            st.caption("⚠️ Requiere revisión humana antes de tomar decisiones.")


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 6: ALERTAS Y AUDITORÍA
# ══════════════════════════════════════════════════════════════════════════════
elif seccion == "🚨 Alertas y Auditoría":
    st.title("🚨 Alertas y Reporte de Auditoría")
    st.caption("El auditor opera de forma independiente al constructor de la matriz.")

    # Leer trazas
    trazas_path = Path(__file__).resolve().parent.parent / "output" / "trazas.jsonl"
    trazas = []
    if trazas_path.exists():
        with open(trazas_path, encoding="utf-8") as f:
            for linea in f:
                try:
                    trazas.append(json.loads(linea))
                except Exception:
                    pass

    # Buscar reporte del auditor
    reporte_auditoria = next(
        (t for t in reversed(trazas) if t.get("agente") == "auditor"), {}
    )

    # Score de calidad
    score = reporte_auditoria.get("score_calidad", None)
    if score is not None:
        col1, col2, col3 = st.columns(3)
        col1.metric("Score de calidad", f"{score:.2f} / 1.00")
        col2.metric("Alertas generadas",
                    reporte_auditoria.get("alertas_generadas", "?"))
        col3.metric("Revisión humana requerida",
                    "SÍ ⚠️" if reporte_auditoria.get("revision_requerida") else "No urgente ✅")

    # Leer el reporte completo del JSON de métricas si existe
    # (o leerlo del output/reporte_auditoria si lo guardáramos separado)
    # Aquí usamos las trazas como proxy
    st.divider()
    st.subheader("Log de trazas por agente")

    if trazas:
        df_trazas = pd.DataFrame([
            {
                "Agente":    t.get("agente", "?"),
                "Tipo":      t.get("tipo", "?"),
                "Timestamp": t.get("timestamp", "?")[:19] if t.get("timestamp") else "?",
                "Errores":   len(t.get("errores", [])),
            }
            for t in trazas
        ])
        st.dataframe(df_trazas, use_container_width=True)

        # Errores acumulados
        todos_errores = [
            f"[{t.get('agente', '?')}] {e}"
            for t in trazas
            for e in t.get("errores", [])
        ]
        if todos_errores:
            st.error(f"Se registraron {len(todos_errores)} error(es) durante la ejecución:")
            for e in todos_errores:
                st.markdown(f"  - {e}")
        else:
            st.success("✅ No se registraron errores en la ejecución.")
    else:
        st.info("No se encontraron trazas. Ejecuta el sistema para generar el log.")

    # Preguntas sugeridas para el abogado
    st.divider()
    st.subheader("💬 Preguntas sugeridas para preparación de audiencia")

    filas_criticas = [
        f for f in matriz
        if f.get("riesgo") in {"alto", "critico"} or f.get("estado") == "vacio_critico"
    ]

    if filas_criticas:
        for f in filas_criticas[:5]:
            hecho = f.get("hecho", {})
            texto_hecho = hecho.get("texto", "") if isinstance(hecho, dict) else str(hecho)
            with st.container():
                st.markdown(f"**{f.get('id')}** — {f.get('elemento_juridico', '')}")
                st.markdown(f"- ¿Puede probar que {texto_hecho[:100]}?")
                st.markdown(f"- Acción: _{f.get('accion_sugerida', '')}_")
                st.divider()
    else:
        st.info("No hay filas de riesgo alto o crítico detectadas.")
