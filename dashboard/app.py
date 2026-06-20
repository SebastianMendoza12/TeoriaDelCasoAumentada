"""
app.py — Dashboard del Abogado
Streamlit con subida de PDF desde la interfaz y 6 secciones de análisis.

Uso:
    streamlit run dashboard/app.py
"""

import json
import shutil
import threading
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Configuración ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Teoría del Caso Aumentada",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR    = Path(__file__).resolve().parent.parent
OUTPUT_DIR  = BASE_DIR / "output"
INPUT_DIR   = BASE_DIR / "data" / "input"
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def cargar_json(nombre: str):
    ruta = OUTPUT_DIR / nombre
    if not ruta.exists():
        return None
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)

def badge_estado(estado: str) -> str:
    icons = {
        "completo": "🟢", "parcial": "🟡", "controvertido": "🟠",
        "debil": "🔴", "vacio_critico": "⛔", "riesgo_adversarial": "🔴",
        "bloqueado": "⬛", "pendiente": "⚪",
    }
    return f"{icons.get(estado, '❓')} {estado}"

def badge_riesgo(riesgo: str) -> str:
    return {"bajo": "🟢 bajo", "medio": "🟡 medio",
            "alto": "🔴 alto", "critico": "⛔ crítico"}.get(riesgo, riesgo)


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("⚖️ Teoría del Caso Aumentada")
st.sidebar.caption("Sistema multiagente — Universidad de Pamplona 2026-1")
st.sidebar.divider()

seccion = st.sidebar.radio("Sección", [
    "📥 Cargar Expediente",
    "🏠 Vista General",
    "📋 Matriz HPN",
    "🕸️ Red Multicapa",
    "📊 Métricas",
    "🎭 Simulador",
    "🚨 Alertas y Auditoría",
    "💡 Explicaciones",
])

st.sidebar.divider()
st.sidebar.warning(
    "⚠️ La decisión jurídica final permanece en cabeza humana. "
    "Este sistema apoya la preparación, no sustituye el criterio profesional."
)


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 0: CARGAR EXPEDIENTE (nueva — punto de entrada principal)
# ══════════════════════════════════════════════════════════════════════════════
if seccion == "📥 Cargar Expediente":
    st.title("📥 Cargar Expediente Judicial")
    st.caption("Sube el PDF del expediente y ejecuta el sistema de análisis.")

    st.info(
        "El sistema acepta cualquier PDF de texto con el expediente del caso. "
        "No importa el nombre del archivo — el sistema lo procesará automáticamente."
    )

    # ── Subida del PDF ────────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Selecciona el PDF del expediente",
        type=["pdf"],
        help="Cualquier nombre de archivo es válido. Debe ser PDF de texto (no escaneado).",
    )

    if uploaded is not None:
        # Guardar con nombre estándar — no importa el nombre original
        destino = INPUT_DIR / "expediente.pdf"
        with open(destino, "wb") as f:
            f.write(uploaded.read())

        st.success(f"✅ PDF cargado: **{uploaded.name}** → guardado como `expediente.pdf`")
        st.caption(f"Tamaño: {uploaded.size / 1024:.1f} KB")

        st.divider()
        st.subheader("Ejecutar el sistema")
        st.code("python -m src.graph", language="bash")
        st.caption(
            "Abre una terminal en la carpeta del proyecto y ejecuta el comando anterior. "
            "Cuando termine, recarga esta página y ve a 🏠 Vista General."
        )

        # Botón de ejecución directa (si están en local con Python disponible)
        if st.button("▶️ Ejecutar análisis ahora", type="primary"):
            with st.spinner("Ejecutando los 13 agentes... esto puede tardar 1-3 minutos"):
                try:
                    import sys
                    sys.path.insert(0, str(BASE_DIR))
                    from src.graph import ejecutar
                    ejecutar(str(destino))
                    st.success("✅ Análisis completado. Ve a 🏠 Vista General.")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Error durante la ejecución: {e}")
                    st.info("Intenta ejecutar desde terminal: `python -m src.graph`")

    # Mostrar PDF cargado actualmente
    pdf_actual = INPUT_DIR / "expediente.pdf"
    if pdf_actual.exists():
        st.divider()
        size_kb = pdf_actual.stat().st_size / 1024
        st.info(f"📄 PDF actual en el sistema: `expediente.pdf` ({size_kb:.1f} KB)")
        if st.button("🗑️ Eliminar PDF actual"):
            pdf_actual.unlink()
            st.warning("PDF eliminado. Sube uno nuevo para continuar.")


# ── Cargar datos para las demás secciones ─────────────────────────────────────
datos_hpn        = cargar_json("matriz_hpn.json")
datos_grafo      = cargar_json("grafo.json")
datos_metricas   = cargar_json("metricas.json")
datos_escenarios = cargar_json("escenarios.json")
datos_expl       = cargar_json("explicaciones.json")

hay_datos = datos_hpn is not None
matriz    = datos_hpn.get("filas", []) if hay_datos else []
case_id   = datos_hpn.get("case_id", "sin ID") if hay_datos else ""

if seccion != "📥 Cargar Expediente" and not hay_datos:
    st.title("⚖️ Teoría del Caso Aumentada")
    st.error("No hay resultados disponibles todavía.")
    st.info(
        "**Paso 1:** Ve a 📥 **Cargar Expediente** y sube el PDF.\n\n"
        "**Paso 2:** Ejecuta el análisis.\n\n"
        "**Paso 3:** Regresa aquí."
    )
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 1: VISTA GENERAL
# ══════════════════════════════════════════════════════════════════════════════
elif seccion == "🏠 Vista General":
    st.title("🏠 Vista General del Caso")
    st.caption(f"Case ID: `{case_id}` | {datos_hpn.get('timestamp', '')[:19]}")

    total = len(matriz)
    if total == 0:
        st.warning("La Matriz HPN está vacía.")
        st.stop()

    completas  = sum(1 for f in matriz if f.get("estado") == "completo")
    parciales  = sum(1 for f in matriz if f.get("estado") in {"parcial","controvertido"})
    debiles    = sum(1 for f in matriz if f.get("estado") in {"debil","riesgo_adversarial"})
    criticas   = sum(1 for f in matriz if f.get("estado") == "vacio_critico")
    pendientes = sum(1 for f in matriz if f.get("revision_humana") == "sin_revisar")

    col1,col2,col3,col4,col5 = st.columns(5)
    col1.metric("Total filas HPN", total)
    col2.metric("Completas ✅", completas, f"{round(completas/total*100)}%")
    col3.metric("Parciales 🟡", parciales)
    col4.metric("Débiles 🔴", debiles)
    col5.metric("Vacíos críticos ⛔", criticas)

    st.divider()
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Distribución de estados")
        conteo = {}
        for f in matriz:
            e = f.get("estado","?"); conteo[e] = conteo.get(e,0)+1
        df_e = pd.DataFrame(list(conteo.items()), columns=["Estado","Filas"])
        fig = px.bar(df_e, x="Estado", y="Filas", color="Estado",
                     color_discrete_map={"completo":"#59a14f","parcial":"#f28e2b",
                                         "controvertido":"#e15759","debil":"#9c755f",
                                         "vacio_critico":"#bab0ac","pendiente":"#76b7b2"})
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Distribución de riesgo")
        conteo_r = {}
        for f in matriz:
            r = f.get("riesgo","?"); conteo_r[r] = conteo_r.get(r,0)+1
        df_r = pd.DataFrame(list(conteo_r.items()), columns=["Riesgo","Filas"])
        fig_r = px.pie(df_r, names="Riesgo", values="Filas", hole=0.4,
                       color="Riesgo",
                       color_discrete_map={"bajo":"#59a14f","medio":"#f28e2b",
                                           "alto":"#e15759","critico":"#b07aa1"})
        fig_r.update_layout(height=300)
        st.plotly_chart(fig_r, use_container_width=True)

    st.subheader("Indicador de preparación")
    m = (datos_metricas or {}).get("hpn", {})
    cob_prob = m.get("cobertura_probatoria", 0)
    cob_norm = m.get("cobertura_normativa", 0)
    traza    = m.get("trazabilidad", 0)
    score_p  = round((cob_prob + cob_norm + traza) / 3, 2)

    col_x, col_y = st.columns([1, 2])
    with col_x:
        fig_g = go.Figure(go.Indicator(
            mode="gauge+number", value=score_p*100,
            title={"text": "Score de preparación"},
            gauge={"axis":{"range":[0,100]}, "bar":{"color":"#4e79a7"},
                   "steps":[{"range":[0,40],"color":"#e15759"},
                             {"range":[40,70],"color":"#f28e2b"},
                             {"range":[70,100],"color":"#59a14f"}],
                   "threshold":{"line":{"color":"red","width":4},"value":70}}))
        fig_g.update_layout(height=250)
        st.plotly_chart(fig_g, use_container_width=True)
    with col_y:
        st.markdown(f"""
| Indicador | Valor |
|-----------|-------|
| Cobertura probatoria | `{cob_prob:.0%}` |
| Cobertura normativa | `{cob_norm:.0%}` |
| Trazabilidad | `{traza:.0%}` |
| Sin revisión humana | `{pendientes}` de `{total}` |
""")
        if score_p < 0.5:   st.error("⛔ Caso CRÍTICO — vacíos graves.")
        elif score_p < 0.7: st.warning("⚠️ Caso PARCIAL — reforzar antes de audiencia.")
        else:               st.success("✅ Buen estado de preparación.")


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 2: MATRIZ HPN
# ══════════════════════════════════════════════════════════════════════════════
elif seccion == "📋 Matriz HPN":
    st.title("📋 Matriz HPN — Hecho · Prueba · Norma")

    if not matriz:
        st.warning("Matriz vacía."); st.stop()

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        est_disp = list({f.get("estado","") for f in matriz})
        filtro_e = st.multiselect("Estado", est_disp, default=est_disp)
    with col_f2:
        rie_disp = list({f.get("riesgo","") for f in matriz})
        filtro_r = st.multiselect("Riesgo", rie_disp, default=rie_disp)
    with col_f3:
        filtro_t = st.text_input("Buscar texto", "")

    mf = [f for f in matriz
          if f.get("estado") in filtro_e
          and f.get("riesgo") in filtro_r
          and filtro_t.lower() in (
              f.get("elemento_juridico","") + f.get("accion_sugerida","")
          ).lower()]

    st.caption(f"Mostrando {len(mf)} de {len(matriz)} filas")

    rows = []
    for f in mf:
        h = f.get("hecho", {})
        rows.append({
            "ID": f.get("id",""), "Elemento jurídico": f.get("elemento_juridico",""),
            "Hecho": h.get("texto","") if isinstance(h,dict) else str(h),
            "Pruebas": len(f.get("pruebas",[])), "Normas": len(f.get("normas",[])),
            "Estado": f.get("estado",""), "Riesgo": f.get("riesgo",""),
            "Revisión": f.get("revision_humana",""), "Acción": f.get("accion_sugerida",""),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, height=350)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Descargar CSV", csv, "matriz_hpn.csv", "text/csv")

    st.divider()
    st.subheader("Detalle de fila")
    ids = [f.get("id",f"f{i}") for i,f in enumerate(mf)]
    if ids:
        sel = st.selectbox("Selecciona fila", ids)
        fila = next((f for f in mf if f.get("id")==sel), None)
        if fila:
            h = fila.get("hecho",{})
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Elemento:** {fila.get('elemento_juridico','')}")
                st.markdown(f"**Hecho:** {h.get('texto','') if isinstance(h,dict) else h}")
                src = fila.get("fuente_expediente",{})
                st.markdown(f"**Fuente:** p.{src.get('pagina','?')} | `{src.get('frag_id','?')}`")
                st.markdown(f"**Estado:** {badge_estado(fila.get('estado',''))}")
                st.markdown(f"**Riesgo:** {badge_riesgo(fila.get('riesgo',''))}")
            with c2:
                st.markdown("**Pruebas:**")
                for p in fila.get("pruebas",[]):
                    ic = "✅" if p.get("relacion")=="soporta" else "❌"
                    st.markdown(f"  {ic} `{p.get('id')}` {p.get('tipo','')} fuerza:{p.get('fuerza','?')}")
                st.markdown("**Normas:**")
                for n in fila.get("normas",[]):
                    st.markdown(f"  📜 `{n.get('id')}` {n.get('texto','')} ({n.get('fuente','')})")
                for c in fila.get("contradicciones",[]):
                    st.markdown(f"  ⚡ {c}")
            st.info(f"💡 **Acción:** {fila.get('accion_sugerida','')}")


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 3: RED MULTICAPA
# ══════════════════════════════════════════════════════════════════════════════
elif seccion == "🕸️ Red Multicapa":
    st.title("🕸️ Red Compleja Multicapa")

    red_html = OUTPUT_DIR / "red_multicapa.html"
    if red_html.exists():
        st.caption("Visualización interactiva — arrastra nodos, haz zoom.")
        with open(red_html, encoding="utf-8") as f:
            st.iframe(f.read(), height=700)
    else:
        st.warning("No se encontró `red_multicapa.html`. Ejecuta el sistema primero.")

    if datos_grafo:
        st.divider()
        nodos   = datos_grafo.get("nodes",[])
        aristas = datos_grafo.get("links",[])
        c1,c2,c3 = st.columns(3)
        c1.metric("Nodos", len(nodos))
        c2.metric("Aristas", len(aristas))
        capas = list({n.get("capa","?") for n in nodos})
        c3.metric("Capas", len(capas))

        conteo_c = {}
        for n in nodos:
            c = n.get("capa","?"); conteo_c[c] = conteo_c.get(c,0)+1
        df_c = pd.DataFrame(list(conteo_c.items()), columns=["Capa","Nodos"])
        fig_c = px.bar(df_c, x="Capa", y="Nodos", color="Capa", title="Nodos por capa")
        fig_c.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig_c, use_container_width=True)

        conteo_t = {}
        for a in aristas:
            t = a.get("tipo","?"); conteo_t[t] = conteo_t.get(t,0)+1
        if conteo_t:
            df_t = pd.DataFrame(list(conteo_t.items()), columns=["Tipo","Aristas"])
            fig_t = px.pie(df_t, names="Tipo", values="Aristas",
                           title="Aristas por tipo de relación", hole=0.3)
            fig_t.update_layout(height=300)
            st.plotly_chart(fig_t, use_container_width=True)

        st.download_button("⬇️ Descargar grafo (JSON)",
            json.dumps(datos_grafo, ensure_ascii=False, indent=2).encode(),
            "grafo_multicapa.json", "application/json")


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 4: MÉTRICAS
# ══════════════════════════════════════════════════════════════════════════════
elif seccion == "📊 Métricas":
    st.title("📊 Panel de Métricas")

    if not datos_metricas:
        st.warning("No hay métricas."); st.stop()

    mhpn = datos_metricas.get("hpn", {})
    mred = datos_metricas.get("red", {})
    mexpl= datos_metricas.get("explicabilidad", {})

    st.subheader("📋 Métricas HPN")
    if mhpn and "total_filas" in mhpn:
        c = st.columns(4)
        c[0].metric("Cob. probatoria",      f"{mhpn.get('cobertura_probatoria',0):.0%}")
        c[1].metric("Cob. normativa",        f"{mhpn.get('cobertura_normativa',0):.0%}")
        c[2].metric("Cob. elem. jurídicos",  f"{mhpn.get('cobertura_elementos_juridicos',0):.0%}")
        c[3].metric("Trazabilidad",          f"{mhpn.get('trazabilidad',0):.0%}")

        c2 = st.columns(4)
        c2[0].metric("Vacíos críticos",      mhpn.get("vacios_criticos",0))
        c2[1].metric("Contradicciones",      mhpn.get("indice_contradiccion",0))
        c2[2].metric("Filas débiles",        mhpn.get("filas_debiles",0))
        c2[3].metric("Acciones pendientes",  mhpn.get("acciones_pendientes",0))

        cats = ["Probatoria","Normativa","Elem. jurídicos","Trazabilidad"]
        vals = [mhpn.get("cobertura_probatoria",0), mhpn.get("cobertura_normativa",0),
                mhpn.get("cobertura_elementos_juridicos",0), mhpn.get("trazabilidad",0)]
        fig_r = go.Figure(go.Scatterpolar(
            r=vals+[vals[0]], theta=cats+[cats[0]], fill="toself",
            fillcolor="rgba(78,121,167,0.3)", line=dict(color="#4e79a7")))
        fig_r.update_layout(
            polar=dict(radialaxis=dict(visible=True,range=[0,1])),
            title="Radar de cobertura", height=350)
        st.plotly_chart(fig_r, use_container_width=True)

    st.divider()
    st.subheader("🕸️ Métricas de Red")
    if mred and "total_nodos" in mred:
        c3 = st.columns(4)
        c3[0].metric("Nodos",   mred.get("total_nodos",0))
        c3[1].metric("Aristas", mred.get("total_aristas",0))
        c3[2].metric("Densidad",mred.get("densidad",0))
        c3[3].metric("Puntos de falla", len(mred.get("puntos_unicos_de_falla",[])))

        top5 = mred.get("top5_betweenness",[])
        if top5:
            st.markdown("**Top 5 nodos — centralidad de intermediación:**")
            df5 = pd.DataFrame(top5, columns=["Nodo","Betweenness"])
            df5["Betweenness"] = df5["Betweenness"].round(3)
            st.dataframe(df5, use_container_width=True)

        pf = mred.get("puntos_unicos_de_falla",[])
        if pf:
            st.error(f"⚠️ Puntos únicos de falla: `{', '.join(pf)}`")

        frag = mred.get("fragilidad_por_prueba",{})
        if frag:
            df_f = pd.DataFrame(list(frag.items()),columns=["Prueba","Fragilidad"]).sort_values("Fragilidad",ascending=False)
            fig_f = px.bar(df_f, x="Prueba", y="Fragilidad",
                           title="Fragilidad por prueba", color="Fragilidad",
                           color_continuous_scale="Reds")
            fig_f.update_layout(height=300)
            st.plotly_chart(fig_f, use_container_width=True)

    if mexpl:
        st.divider()
        st.subheader("💡 Métricas de Explicabilidad")
        ce = st.columns(3)
        ce[0].metric("Explicaciones totales",   mexpl.get("total_explicaciones",0))
        ce[1].metric("Aprobadas ✅",            mexpl.get("explicaciones_aprobadas",0))
        ce[2].metric("Score explicabilidad",    mexpl.get("score_explicabilidad",0))

    st.download_button("⬇️ Descargar métricas (JSON)",
        json.dumps(datos_metricas, ensure_ascii=False, indent=2).encode(),
        "metricas.json","application/json")


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 5: SIMULADOR
# ══════════════════════════════════════════════════════════════════════════════
elif seccion == "🎭 Simulador":
    st.title("🎭 Simulador de Escenarios Procesales")
    st.warning("⚠️ Los escenarios NO predicen el fallo. Son laboratorio estratégico.")

    escenarios = (datos_escenarios or {}).get("escenarios",[])
    if not escenarios:
        st.warning("No hay escenarios."); st.stop()

    for esc in escenarios:
        analisis = esc.get("analisis",{})
        nivel    = analisis.get("nivel_impacto","?")
        icono    = {"bajo":"🟢","medio":"🟡","alto":"🔴","critico":"⛔"}.get(nivel,"❓")

        with st.expander(f"{icono} {esc['id']}: {esc['nombre']}"):
            st.markdown(f"**Supuesto:** {esc.get('supuesto_explicito','')}")
            if esc.get("prueba_eliminada_s1"):
                st.info(f"Prueba eliminada en S1: `{esc['prueba_eliminada_s1']}`")

            ca, cb = st.columns(2)
            with ca:
                st.markdown("**Métricas ANTES:**")
                antes = esc.get("metricas_antes",{})
                st.markdown(f"- Cob. probatoria: `{antes.get('cobertura_probatoria','?')}`")
                st.markdown(f"- Vacíos críticos: `{antes.get('vacios_criticos','?')}`")
            with cb:
                st.markdown("**Métricas DESPUÉS:**")
                desp = esc.get("metricas_despues",{})
                if desp:
                    st.markdown(f"- Cob. probatoria: `{desp.get('cobertura_probatoria','?')}`")
                    st.markdown(f"- Vacíos críticos: `{desp.get('vacios_criticos','?')}`")
                else:
                    st.markdown("_Solo disponible para S1_")

            if analisis.get("hechos_afectados"):
                st.markdown(f"**Hechos afectados:** `{', '.join(analisis['hechos_afectados'])}`")
            st.success(f"💡 **Acción:** {analisis.get('accion_sugerida','')}")
            if analisis.get("incertidumbre"):
                st.caption(f"ℹ️ {analisis['incertidumbre']}")
            st.caption("⚠️ Requiere revisión humana.")


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 6: ALERTAS Y AUDITORÍA
# ══════════════════════════════════════════════════════════════════════════════
elif seccion == "🚨 Alertas y Auditoría":
    st.title("🚨 Alertas y Auditoría")

    trazas_path = OUTPUT_DIR / "trazas.jsonl"
    trazas = []
    if trazas_path.exists():
        with open(trazas_path, encoding="utf-8") as f:
            for linea in f:
                try: trazas.append(json.loads(linea))
                except: pass

    reporte_aud = next((t for t in reversed(trazas) if t.get("agente")=="auditor"), {})
    score = reporte_aud.get("score_calidad")
    if score is not None:
        c1,c2,c3 = st.columns(3)
        c1.metric("Score calidad", f"{score:.2f}")
        c2.metric("Alertas", reporte_aud.get("alertas_generadas","?"))
        c3.metric("Rev. humana", "SÍ ⚠️" if reporte_aud.get("revision_requerida") else "No urgente ✅")

    # Checklist
    checklist_data = cargar_json("checklist.json")
    if checklist_data:
        st.divider()
        st.subheader("✅ PreCompletion Checklist")
        if checklist_data.get("aprobado"):
            st.success("Checklist APROBADO — todos los artefactos mínimos generados.")
        else:
            st.error(f"Checklist BLOQUEADO: {checklist_data.get('razon_bloqueo','')}")
        for item in checklist_data.get("items_aprobados",[]):
            st.markdown(f"  ✅ {item}")
        for item in checklist_data.get("items_fallidos",[]):
            st.markdown(f"  ❌ {item}")

    # Loop detection
    loop_data = cargar_json("loop_detection.json")
    if loop_data:
        st.divider()
        st.subheader("🔄 Loop Detection")
        if loop_data.get("loop_detectado"):
            st.error(f"Loop detectado: {loop_data.get('descripcion','')}")
        else:
            st.success(f"Sin loops: {loop_data.get('descripcion','')}")

    st.divider()
    st.subheader("Log de trazas")
    if trazas:
        df_t = pd.DataFrame([{
            "Agente": t.get("agente","?"), "Tipo": t.get("tipo","?"),
            "Timestamp": t.get("timestamp","")[:19],
            "Errores": len(t.get("errores",[])),
        } for t in trazas])
        st.dataframe(df_t, use_container_width=True)

        todos_err = [f"[{t.get('agente','?')}] {e}"
                     for t in trazas for e in t.get("errores",[])]
        if todos_err:
            st.error(f"{len(todos_err)} error(es):")
            for e in todos_err: st.markdown(f"  - {e}")
        else:
            st.success("✅ Sin errores en la ejecución.")

    st.divider()
    st.subheader("💬 Preguntas sugeridas para audiencia")
    filas_c = [f for f in matriz if f.get("riesgo") in {"alto","critico"}
               or f.get("estado")=="vacio_critico"]
    if filas_c:
        for f in filas_c[:5]:
            h = f.get("hecho",{})
            t = h.get("texto","") if isinstance(h,dict) else str(h)
            st.markdown(f"**{f.get('id')}** — {f.get('elemento_juridico','')}")
            st.markdown(f"- ¿Puede probar que {t[:100]}?")
            st.markdown(f"- Acción: _{f.get('accion_sugerida','')}_")
            st.divider()
    else:
        st.info("No hay filas de riesgo alto/crítico.")


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 7: EXPLICACIONES
# ══════════════════════════════════════════════════════════════════════════════
elif seccion == "💡 Explicaciones":
    st.title("💡 Explicaciones de Decisiones")
    st.caption(
        "El sistema explica POR QUÉ tomó cada decisión, citando la fuente "
        "del expediente que la motivó. Basado en ExplanationBuilder + "
        "ExplanationVerifier (Capítulos 19-20 del documento del profesor)."
    )

    if not datos_expl:
        st.warning("No hay explicaciones generadas todavía.")
        st.stop()

    explicaciones = datos_expl.get("explicaciones", [])
    if not explicaciones:
        st.info("El sistema no generó explicaciones en esta ejecución.")
        st.stop()

    # Métricas de explicabilidad
    mexpl = (datos_metricas or {}).get("explicabilidad", {})
    if mexpl:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total explicaciones", mexpl.get("total_explicaciones", 0))
        c2.metric("Aprobadas por verificador ✅", mexpl.get("explicaciones_aprobadas", 0))
        c3.metric("Score explicabilidad", f"{mexpl.get('score_explicabilidad', 0):.0%}")

        if mexpl.get("score_explicabilidad", 0) < 0.6:
            st.warning("⚠️ Score de explicabilidad bajo — algunas explicaciones sin fuente verificable.")
        else:
            st.success("✅ Explicaciones verificadas correctamente.")

    st.divider()

    # Filtro por tipo
    tipos_disp = list({e.get("tipo","?") for e in explicaciones})
    filtro_tipo = st.multiselect("Filtrar por tipo", tipos_disp, default=tipos_disp)
    expl_f = [e for e in explicaciones if e.get("tipo") in filtro_tipo]

    for exp in expl_f:
        estado_v = exp.get("estado_verificacion", "sin_verificar")
        icono_v  = "✅" if estado_v == "aprobada" else "⚠️" if estado_v == "sin_verificar" else "❌"

        with st.expander(
            f"{icono_v} [{exp.get('tipo','?')}] Ref: `{exp.get('referencia','?')}`"
        ):
            st.markdown(f"**Decisión:** {exp.get('decision','')}")
            st.markdown(f"**Razón:** {exp.get('razon','')}")
            st.markdown(f"**Fuente citada:** `{exp.get('fuente_citada','?')}`")
            st.caption(f"Estado de verificación: {estado_v}")
            if exp.get("razon_rechazo"):
                st.error(f"Rechazada: {exp['razon_rechazo']}")

    st.divider()
    st.download_button(
        "⬇️ Descargar explicaciones (JSON)",
        json.dumps(datos_expl, ensure_ascii=False, indent=2).encode(),
        "explicaciones.json", "application/json",
    )