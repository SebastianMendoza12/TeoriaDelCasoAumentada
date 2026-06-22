"""
dashboard/app.py — Dashboard del Abogado
Teoría del Caso Aumentada — Universidad de Pamplona 2026-1

Flujo de uso:
  1. Sube el PDF del expediente aquí
  2. Ejecuta el análisis desde terminal:  python -m src.graph
  3. Recarga la página para ver los resultados
"""

import json
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components

# ── Configuración de página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Teoría del Caso Aumentada",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR   = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
INPUT_DIR  = BASE_DIR / "data" / "input"
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── CSS personalizado ─────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Tarjetas de métricas más compactas */
  [data-testid="metric-container"] {
      background: #f8f9fa;
      border-radius: 8px;
      padding: 12px;
      border-left: 4px solid #4e79a7;
  }
  /* Semáforo */
  .semaforo-verde  { background:#e8f5e9; color:#2e7d32; padding:6px 16px;
                     border-radius:20px; font-weight:bold; display:inline-block; }
  .semaforo-amarillo { background:#fff8e1; color:#f57f17; padding:6px 16px;
                       border-radius:20px; font-weight:bold; display:inline-block; }
  .semaforo-rojo   { background:#ffebee; color:#c62828; padding:6px 16px;
                     border-radius:20px; font-weight:bold; display:inline-block; }
  /* Secciones */
  .seccion-titulo { font-size:1.1rem; font-weight:600; color:#1a1a2e;
                    border-bottom:2px solid #4e79a7; padding-bottom:4px; margin-bottom:12px; }
  /* Alerta accionable */
  .alerta-critica { background:#ffebee; border-left:4px solid #c62828;
                    padding:10px 14px; border-radius:4px; margin:6px 0; }
  .alerta-alta    { background:#fff3e0; border-left:4px solid #f57c00;
                    padding:10px 14px; border-radius:4px; margin:6px 0; }
  .alerta-media   { background:#e3f2fd; border-left:4px solid #1976d2;
                    padding:10px 14px; border-radius:4px; margin:6px 0; }
  /* Disclaimer */
  .disclaimer { background:#fff9c4; border:1px solid #f9a825; border-radius:6px;
                padding:10px 14px; font-size:0.85rem; color:#555; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
  :root {
      --tc-surface: #f8f9fa;
      --tc-text: #1f2937;
      --tc-heading: #111827;
      --tc-primary: #4e79a7;
      --tc-green-bg: #e8f5e9;
      --tc-green-text: #1b5e20;
      --tc-yellow-bg: #fff8e1;
      --tc-yellow-text: #8a5a00;
      --tc-red-bg: #ffebee;
      --tc-red-text: #9f1239;
      --tc-blue-bg: #e3f2fd;
      --tc-blue-text: #0f4c81;
      --tc-orange-bg: #fff3e0;
      --tc-orange-text: #9a3412;
      --tc-disclaimer-bg: #fff9c4;
      --tc-disclaimer-text: #3f3f46;
  }
  @media (prefers-color-scheme: dark) {
      :root {
          --tc-surface: #111827;
          --tc-text: #f3f4f6;
          --tc-heading: #f9fafb;
          --tc-primary: #93c5fd;
          --tc-green-bg: #052e1a;
          --tc-green-text: #86efac;
          --tc-yellow-bg: #422006;
          --tc-yellow-text: #fde68a;
          --tc-red-bg: #450a0a;
          --tc-red-text: #fecaca;
          --tc-blue-bg: #082f49;
          --tc-blue-text: #bae6fd;
          --tc-orange-bg: #431407;
          --tc-orange-text: #fed7aa;
          --tc-disclaimer-bg: #422006;
          --tc-disclaimer-text: #fef3c7;
      }
  }
  [data-testid="metric-container"] {
      background: var(--tc-surface) !important;
      color: var(--tc-text) !important;
      border-left: 4px solid var(--tc-primary) !important;
  }
  [data-testid="metric-container"] * { color: inherit !important; }
  .semaforo-verde {
      background: var(--tc-green-bg) !important;
      color: var(--tc-green-text) !important;
  }
  .semaforo-amarillo {
      background: var(--tc-yellow-bg) !important;
      color: var(--tc-yellow-text) !important;
  }
  .semaforo-rojo {
      background: var(--tc-red-bg) !important;
      color: var(--tc-red-text) !important;
  }
  .seccion-titulo {
      color: var(--tc-heading) !important;
      border-bottom-color: var(--tc-primary) !important;
  }
  .alerta-critica {
      background: var(--tc-red-bg) !important;
      color: var(--tc-red-text) !important;
      border-left-color: var(--tc-red-text) !important;
  }
  .alerta-alta {
      background: var(--tc-orange-bg) !important;
      color: var(--tc-orange-text) !important;
      border-left-color: var(--tc-orange-text) !important;
  }
  .alerta-media {
      background: var(--tc-blue-bg) !important;
      color: var(--tc-blue-text) !important;
      border-left-color: var(--tc-blue-text) !important;
  }
  .alerta-critica small, .alerta-alta small, .alerta-media small {
      color: inherit !important;
      opacity: 0.92;
  }
  .disclaimer {
      background: var(--tc-disclaimer-bg) !important;
      color: var(--tc-disclaimer-text) !important;
      border-color: var(--tc-yellow-text) !important;
  }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def cargar(nombre: str):
    ruta = OUTPUT_DIR / nombre
    if not ruta.exists():
        return None
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)

def semaforo_html(valor: str) -> str:
    labels = {"verde": "🟢 BUENO", "amarillo": "🟡 PARCIAL", "rojo": "🔴 CRÍTICO"}
    return f'<span class="semaforo-{valor}">{labels.get(valor, valor.upper())}</span>'

def color_estado(estado: str) -> str:
    return {"completo": "🟢", "parcial": "🟡", "controvertido": "🟠",
            "debil": "🔴", "vacio_critico": "⛔", "bloqueado": "⬛",
            "pendiente": "⚪", "riesgo_adversarial": "🔴"}.get(estado, "❓")

def color_riesgo(riesgo: str) -> str:
    return {"bajo": "🟢", "medio": "🟡", "alto": "🔴", "critico": "⛔"}.get(riesgo, "❓")


# ── Cargar todos los datos ────────────────────────────────────────────────────
d_hpn        = cargar("matriz_hpn.json")
d_metricas   = cargar("metricas.json")
d_escenarios = cargar("escenarios.json")
d_grafo      = cargar("grafo.json")
d_expl       = cargar("explicaciones.json")
d_dash       = cargar("dashboard_data.json")
d_checklist  = cargar("checklist.json")
d_loop       = cargar("loop_detection.json")

hay_resultados = d_hpn is not None
matriz = d_hpn.get("filas", []) if hay_resultados else []


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚖️ Teoría del Caso")
    st.caption("Sistema multiagente — U. de Pamplona 2026-1")
    st.divider()

    pagina = st.radio("", [
        "📥  Expediente",
        "🏠  Resumen del caso",
        "📋  Matriz HPN",
        "🕸️  Red multicapa",
        "📊  Métricas",
        "🎭  Escenarios",
        "🚨  Auditoría",
        "💡  Explicaciones",
    ], label_visibility="collapsed")

    st.divider()

    # Estado rápido del sistema
    if hay_resultados:
        semaforo = d_dash.get("semaforo", "rojo") if d_dash else "rojo"
        st.markdown(f"**Estado:** {semaforo_html(semaforo)}", unsafe_allow_html=True)
        st.caption(f"{len(matriz)} filas HPN · "
                   f"Case: `{d_hpn.get('case_id','?')[:16]}`")
    else:
        st.info("Sin resultados todavía")

    st.divider()
    # Descarga del reporte final
    reporte = OUTPUT_DIR / "reporte_final.html"
    if reporte.exists():
        st.download_button(
            "⬇️ Reporte HTML",
            reporte.read_bytes(),
            "reporte_final.html",
            "text/html",
            use_container_width=True,
        )

    st.markdown(
        '<div class="disclaimer">⚠️ La decisión jurídica final permanece '
        'en cabeza humana.</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 0 — EXPEDIENTE
# ══════════════════════════════════════════════════════════════════════════════
if pagina == "📥  Expediente":
    st.title("📥 Cargar expediente")

    col_a, col_b = st.columns([3, 2])

    with col_a:
        st.markdown("#### Sube el PDF del caso")
        st.caption("Cualquier nombre de archivo es válido. "
                   "Se guarda automáticamente como `expediente.pdf`.")
        subido = st.file_uploader("", type=["pdf"], label_visibility="collapsed")

        if subido:
            destino = INPUT_DIR / "expediente.pdf"
            destino.write_bytes(subido.read())
            st.success(f"✅ **{subido.name}** cargado ({subido.size/1024:.0f} KB)")

        # PDF actual
        pdf_actual = INPUT_DIR / "expediente.pdf"
        if pdf_actual.exists():
            kb = pdf_actual.stat().st_size / 1024
            st.info(f"📄 PDF actual: `expediente.pdf` — {kb:.0f} KB")
            if st.button("🗑️ Eliminar PDF"):
                pdf_actual.unlink()
                st.rerun()

    with col_b:
        st.markdown("#### Ejecutar el análisis")
        st.markdown("""
Después de subir el PDF, ejecuta en la terminal:

```bash
python -m src.graph
```

El proceso tarda **1 a 3 minutos**. Cuando termine, recarga esta página.
""")
        st.markdown("#### Flujo completo")
        st.markdown("""
```
1. Sube el PDF aquí  ← estás aquí
2. python -m src.graph  (terminal)
3. Ve a 🏠 Resumen del caso
```
""")
        if st.button("🔄 Recargar resultados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()


# ── Guardia: sin resultados en las páginas de análisis ───────────────────────
if pagina != "📥  Expediente" and not hay_resultados:
    st.title("⚖️ Sin resultados")
    st.warning("Primero ve a **📥 Expediente**, sube el PDF y ejecuta el sistema.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 1 — RESUMEN DEL CASO
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🏠  Resumen del caso":
    semaforo = d_dash.get("semaforo", "rojo") if d_dash else "rojo"

    # Encabezado con semáforo
    col_t, col_s = st.columns([4, 1])
    with col_t:
        st.title("🏠 Resumen del caso")
        st.caption(f"Case ID: `{d_hpn.get('case_id','')}` | "
                   f"Generado: {d_hpn.get('timestamp','')[:19]}")
    with col_s:
        st.markdown(f"<br>{semaforo_html(semaforo)}", unsafe_allow_html=True)

    # Resumen ejecutivo
    if d_dash and d_dash.get("resumen_ejecutivo"):
        with st.expander("📄 Resumen ejecutivo", expanded=True):
            st.text(d_dash["resumen_ejecutivo"])

    st.divider()

    # KPIs principales — fila 1
    total = len(matriz)
    completas = sum(1 for f in matriz if f.get("estado") == "completo")
    vacios    = sum(1 for f in matriz if f.get("estado") == "vacio_critico")
    alto_riesgo = sum(1 for f in matriz if f.get("riesgo") in {"alto","critico"})
    pendientes  = sum(1 for f in matriz if f.get("revision_humana") == "sin_revisar")

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Filas HPN",     total)
    c2.metric("Completas ✅",  completas,  f"{round(completas/max(total,1)*100)}%")
    c3.metric("Vacíos ⛔",     vacios)
    c4.metric("Alto riesgo 🔴", alto_riesgo)
    c5.metric("Sin revisar ⚪", pendientes)

    st.divider()

    # Gráficos lado a lado
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown('<p class="seccion-titulo">Estado de filas HPN</p>',
                    unsafe_allow_html=True)
        cnt = {}
        for f in matriz:
            e = f.get("estado","?"); cnt[e] = cnt.get(e,0)+1
        df_e = pd.DataFrame(cnt.items(), columns=["Estado","N"])
        colores = {"completo":"#59a14f","parcial":"#f28e2b","controvertido":"#e15759",
                   "debil":"#9c755f","vacio_critico":"#bab0ac","pendiente":"#76b7b2",
                   "bloqueado":"#4e79a7","riesgo_adversarial":"#ff9da7"}
        fig = px.bar(df_e, x="Estado", y="N", color="Estado",
                     color_discrete_map=colores, height=260)
        fig.update_layout(showlegend=False, margin=dict(t=10,b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_g2:
        st.markdown('<p class="seccion-titulo">Distribución de riesgo</p>',
                    unsafe_allow_html=True)
        cnt_r = {}
        for f in matriz:
            r = f.get("riesgo","?"); cnt_r[r] = cnt_r.get(r,0)+1
        df_r = pd.DataFrame(cnt_r.items(), columns=["Riesgo","N"])
        fig_r = px.pie(df_r, names="Riesgo", values="N", hole=0.5,
                       color="Riesgo",
                       color_discrete_map={"bajo":"#59a14f","medio":"#f28e2b",
                                           "alto":"#e15759","critico":"#b07aa1"},
                       height=260)
        fig_r.update_layout(margin=dict(t=10,b=10))
        st.plotly_chart(fig_r, use_container_width=True)

    # Gauge de preparación
    mhpn = (d_metricas or {}).get("hpn", {})
    cob_p = mhpn.get("cobertura_probatoria", 0)
    cob_n = mhpn.get("cobertura_normativa", 0)
    traz  = mhpn.get("trazabilidad", 0)
    score = round((cob_p + cob_n + traz) / 3 * 100)

    col_g, col_t2 = st.columns([1, 2])
    with col_g:
        fig_g = go.Figure(go.Indicator(
            mode="gauge+number", value=score,
            number={"suffix": "%"},
            gauge={"axis":{"range":[0,100]},
                   "bar":{"color":"#4e79a7"},
                   "steps":[{"range":[0,40],"color":"#ffebee"},
                             {"range":[40,70],"color":"#fff8e1"},
                             {"range":[70,100],"color":"#e8f5e9"}],
                   "threshold":{"line":{"color":"#c62828","width":3},"value":70}},
        ))
        fig_g.update_layout(height=220, margin=dict(t=20,b=0))
        st.plotly_chart(fig_g, use_container_width=True)
        st.caption("Score de preparación del caso")

    with col_t2:
        st.markdown('<p class="seccion-titulo">Cobertura detallada</p>',
                    unsafe_allow_html=True)
        data_cob = {
            "Indicador": ["Probatoria","Normativa","Trazabilidad"],
            "Valor":     [f"{cob_p:.0%}", f"{cob_n:.0%}", f"{traz:.0%}"],
        }
        st.dataframe(pd.DataFrame(data_cob), hide_index=True,
                     use_container_width=True)

        if score < 40:   st.error("⛔ Caso CRÍTICO — actuar antes de la audiencia.")
        elif score < 70: st.warning("⚠️ Reforzar vacíos antes de la audiencia.")
        else:            st.success("✅ Caso bien preparado.")

    # Alertas accionables
    if d_dash and d_dash.get("alertas_accionables"):
        st.divider()
        st.markdown('<p class="seccion-titulo">🚨 Alertas accionables</p>',
                    unsafe_allow_html=True)
        for alerta in d_dash["alertas_accionables"][:5]:
            prioridad = alerta.get("prioridad","media")
            cls = f"alerta-{prioridad}" if prioridad in ("critica","alta","media") else "alerta-media"
            icono = {"critica":"⛔","alta":"🔴","media":"🟡"}.get(prioridad,"🔵")
            st.markdown(
                f'<div class="{cls}"><strong>{icono} {alerta.get("descripcion","")}'
                f'</strong><br><small>💡 {alerta.get("accion","")}</small></div>',
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 2 — MATRIZ HPN
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "📋  Matriz HPN":
    st.title("📋 Matriz HPN")
    st.caption("Hecho · Prueba · Norma — tabla central de la teoría del caso")

    if not matriz:
        st.warning("Matriz vacía."); st.stop()

    # Filtros en una línea
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        est_opts = sorted({f.get("estado","") for f in matriz})
        filtro_e = st.multiselect("Estado", est_opts, default=est_opts,
                                  label_visibility="visible")
    with col_f2:
        rie_opts = sorted({f.get("riesgo","") for f in matriz})
        filtro_r = st.multiselect("Riesgo", rie_opts, default=rie_opts)
    with col_f3:
        busqueda = st.text_input("🔍 Buscar", placeholder="elemento jurídico o acción…")

    mf = [
        f for f in matriz
        if f.get("estado","") in filtro_e
        and f.get("riesgo","") in filtro_r
        and busqueda.lower() in (
            f.get("elemento_juridico","") + f.get("accion_sugerida","")
        ).lower()
    ]
    st.caption(f"Mostrando **{len(mf)}** de {len(matriz)} filas")

    # Tabla
    rows = []
    for f in mf:
        h = f.get("hecho",{})
        rows.append({
            "ID":         f.get("id",""),
            "Elemento":   f.get("elemento_juridico",""),
            "Hecho":      (h.get("texto","") if isinstance(h,dict) else str(h))[:80],
            "Pruebas":    len(f.get("pruebas",[])),
            "Normas":     len(f.get("normas",[])),
            "Estado":     f"{color_estado(f.get('estado',''))} {f.get('estado','')}",
            "Riesgo":     f"{color_riesgo(f.get('riesgo',''))} {f.get('riesgo','')}",
            "Revisión":   f.get("revision_humana",""),
            "Acción":     f.get("accion_sugerida","")[:60],
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, height=340, hide_index=True)

    col_dl1, col_dl2 = st.columns(2)
    csv = pd.DataFrame(rows).to_csv(index=False).encode()
    col_dl1.download_button("⬇️ Descargar CSV", csv, "matriz_hpn.csv", "text/csv")
    col_dl2.download_button(
        "⬇️ Descargar JSON",
        json.dumps({"filas": matriz}, ensure_ascii=False, indent=2).encode(),
        "matriz_hpn.json", "application/json",
    )

    # Detalle de una fila
    st.divider()
    st.markdown('<p class="seccion-titulo">Detalle de fila</p>',
                unsafe_allow_html=True)
    ids = [f.get("id","") for f in mf]
    if ids:
        sel = st.selectbox("Selecciona una fila", ids, label_visibility="collapsed")
        fila = next((f for f in mf if f.get("id")==sel), None)
        if fila:
            h = fila.get("hecho",{})
            src = fila.get("fuente_expediente",{})
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.markdown(f"**Elemento jurídico:** {fila.get('elemento_juridico','')}")
                st.markdown(f"**Hecho:** {h.get('texto','') if isinstance(h,dict) else h}")
                st.markdown(f"**Fuente:** página {src.get('pagina','?')} · `{src.get('frag_id','?')}`")
                st.markdown(f"**Estado:** {color_estado(fila.get('estado',''))} `{fila.get('estado','')}`")
                st.markdown(f"**Riesgo:** {color_riesgo(fila.get('riesgo',''))} `{fila.get('riesgo','')}`")
                st.markdown(f"**Revisión:** `{fila.get('revision_humana','')}`")
            with col_d2:
                st.markdown("**Pruebas:**")
                for p in fila.get("pruebas",[]):
                    ic = "✅" if p.get("relacion")=="soporta" else "❌"
                    st.markdown(f"  {ic} `{p.get('id','')}` {p.get('tipo','')} "
                                f"— fuerza **{p.get('fuerza','?')}**")
                st.markdown("**Normas:**")
                for n in fila.get("normas",[]):
                    st.markdown(f"  📜 `{n.get('id','')}` {n.get('texto','')[:60]}")
                if fila.get("contradicciones"):
                    st.markdown("**Contradicciones:**")
                    for c in fila["contradicciones"]:
                        st.markdown(f"  ⚡ {c}")
            st.info(f"💡 **Acción sugerida:** {fila.get('accion_sugerida','')}")
            if fila.get("errores_validacion"):
                st.warning("Advertencias: " + " · ".join(fila["errores_validacion"]))


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 3 — RED MULTICAPA
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🕸️  Red multicapa":
    st.title("🕸️ Red Compleja Multicapa")

    # Visualización interactiva
    red_html = OUTPUT_DIR / "red_multicapa.html"
    if red_html.exists():
        st.caption("Arrastra nodos · Rueda del ratón para zoom · Hover para detalles")
        with open(red_html, encoding="utf-8") as f:
            components.html(f.read(), height=650, scrolling=False)
    else:
        st.warning("No hay visualización todavía. Ejecuta `python -m src.graph`.")

    # Estadísticas de la red
    if d_grafo:
        st.divider()
        nodos   = d_grafo.get("nodes",[])
        aristas = d_grafo.get("links",[])
        capas   = list({n.get("capa","?") for n in nodos})

        col1,col2,col3 = st.columns(3)
        col1.metric("Nodos",   len(nodos))
        col2.metric("Aristas", len(aristas))
        col3.metric("Capas",   len(capas))

        col_ga, col_gb = st.columns(2)
        with col_ga:
            cnt_c = {}
            for n in nodos:
                c = n.get("capa","?"); cnt_c[c] = cnt_c.get(c,0)+1
            df_c = pd.DataFrame(cnt_c.items(), columns=["Capa","Nodos"])
            fig_c = px.bar(df_c.sort_values("Nodos",ascending=True),
                           x="Nodos", y="Capa", orientation="h",
                           color="Capa", title="Nodos por capa", height=280)
            fig_c.update_layout(showlegend=False, margin=dict(t=30,b=10))
            st.plotly_chart(fig_c, use_container_width=True)

        with col_gb:
            cnt_t = {}
            for a in aristas:
                t = a.get("tipo","?"); cnt_t[t] = cnt_t.get(t,0)+1
            if cnt_t:
                df_t = pd.DataFrame(cnt_t.items(), columns=["Tipo","Aristas"])
                fig_t = px.pie(df_t, names="Tipo", values="Aristas",
                               title="Aristas por tipo", hole=0.4, height=280)
                fig_t.update_layout(margin=dict(t=30,b=10))
                st.plotly_chart(fig_t, use_container_width=True)

        st.download_button(
            "⬇️ Descargar grafo JSON",
            json.dumps(d_grafo, ensure_ascii=False, indent=2).encode(),
            "grafo_multicapa.json", "application/json",
        )


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 4 — MÉTRICAS
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "📊  Métricas":
    st.title("📊 Panel de Métricas")

    if not d_metricas:
        st.warning("Sin métricas."); st.stop()

    mhpn  = d_metricas.get("hpn", {})
    mred  = d_metricas.get("red", {})
    mexpl = d_metricas.get("explicabilidad", {})

    # ── Métricas HPN ─────────────────────────────────────────────────────────
    st.markdown('<p class="seccion-titulo">📋 Cobertura de la Matriz HPN</p>',
                unsafe_allow_html=True)
    if mhpn:
        c = st.columns(4)
        c[0].metric("Cob. probatoria",       f"{mhpn.get('cobertura_probatoria',0):.0%}")
        c[1].metric("Cob. normativa",         f"{mhpn.get('cobertura_normativa',0):.0%}")
        c[2].metric("Cob. elem. jurídicos",   f"{mhpn.get('cobertura_elementos_juridicos',0):.0%}")
        c[3].metric("Trazabilidad",           f"{mhpn.get('trazabilidad',0):.0%}")

        c2 = st.columns(4)
        c2[0].metric("Vacíos críticos",       mhpn.get("vacios_criticos",0))
        c2[1].metric("Contradicciones",       mhpn.get("indice_contradiccion",0))
        c2[2].metric("Filas débiles",         mhpn.get("filas_debiles",0))
        c2[3].metric("Acciones pendientes",   mhpn.get("acciones_pendientes",0))

        # Radar
        cats = ["Probatoria","Normativa","Elem. jurídicos","Trazabilidad"]
        vals = [mhpn.get("cobertura_probatoria",0), mhpn.get("cobertura_normativa",0),
                mhpn.get("cobertura_elementos_juridicos",0), mhpn.get("trazabilidad",0)]
        fig_rad = go.Figure(go.Scatterpolar(
            r=vals+[vals[0]], theta=cats+[cats[0]], fill="toself",
            fillcolor="rgba(78,121,167,0.25)", line=dict(color="#4e79a7",width=2)))
        fig_rad.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0,1])),
            height=320, margin=dict(t=20,b=20))
        st.plotly_chart(fig_rad, use_container_width=True)

    # ── Métricas de Red ───────────────────────────────────────────────────────
    st.divider()
    st.markdown('<p class="seccion-titulo">🕸️ Métricas de la red multicapa</p>',
                unsafe_allow_html=True)
    if mred and "total_nodos" in mred:
        c3 = st.columns(4)
        c3[0].metric("Nodos",         mred.get("total_nodos",0))
        c3[1].metric("Aristas",       mred.get("total_aristas",0))
        c3[2].metric("Densidad",      mred.get("densidad",0))
        c3[3].metric("Puntos de falla", len(mred.get("puntos_unicos_de_falla",[])))

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            top5 = mred.get("top5_betweenness",[])
            if top5:
                st.markdown("**Top 5 — centralidad de intermediación:**")
                df5 = pd.DataFrame(top5, columns=["Nodo","Betweenness"])
                df5["Betweenness"] = df5["Betweenness"].round(3)
                st.dataframe(df5, hide_index=True, use_container_width=True)

        with col_m2:
            frag = mred.get("fragilidad_por_prueba",{})
            if frag:
                df_f = pd.DataFrame(frag.items(), columns=["Prueba","Fragilidad"])
                df_f = df_f.sort_values("Fragilidad", ascending=False)
                fig_f = px.bar(df_f, x="Prueba", y="Fragilidad",
                               color="Fragilidad", color_continuous_scale="Reds",
                               title="Fragilidad por prueba", height=260)
                fig_f.update_layout(margin=dict(t=30,b=10))
                st.plotly_chart(fig_f, use_container_width=True)

        pf = mred.get("puntos_unicos_de_falla",[])
        if pf:
            st.error(f"⚠️ Puntos únicos de falla: `{', '.join(pf)}`  "
                     "— su eliminación colapsa la ruta principal.")

        # Métricas adicionales del Cuadro 4
        extras = {
            "Cob. rutas jurídicas":    mred.get("cobertura_rutas_juridicas"),
            "Robustez adversarial":    mred.get("robustez_adversarial"),
            "Riesgo derrotabilidad":   mred.get("riesgo_de_derrotabilidad"),
            "Consistencia temporal":   mred.get("consistencia_temporal"),
            "Dep. jurisprudencial":    mred.get("dependencia_jurisprudencial"),
            "Trazabilidad de ruta":    mred.get("trazabilidad_de_ruta"),
            "Proximidad pretensión":   mred.get("proximidad_a_pretension"),
        }
        extras_filtrado = {k: v for k, v in extras.items() if v is not None}
        if extras_filtrado:
            st.markdown("**Métricas avanzadas (Cuadro 4 del enunciado):**")
            df_ext = pd.DataFrame(extras_filtrado.items(), columns=["Métrica","Valor"])
            st.dataframe(df_ext, hide_index=True, use_container_width=True)

    # ── Explicabilidad ────────────────────────────────────────────────────────
    if mexpl:
        st.divider()
        st.markdown('<p class="seccion-titulo">💡 Score de explicabilidad</p>',
                    unsafe_allow_html=True)
        ce = st.columns(3)
        ce[0].metric("Explicaciones", mexpl.get("total_explicaciones",0))
        ce[1].metric("Aprobadas ✅",  mexpl.get("explicaciones_aprobadas",0))
        ce[2].metric("Score",         f"{mexpl.get('score_explicabilidad',0):.0%}")

    st.divider()
    st.download_button(
        "⬇️ Descargar métricas JSON",
        json.dumps(d_metricas, ensure_ascii=False, indent=2).encode(),
        "metricas.json","application/json",
    )


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 5 — ESCENARIOS
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🎭  Escenarios":
    st.title("🎭 Simulador de escenarios")
    st.caption("Laboratorio estratégico — perturbaciones sobre la teoría del caso. "
               "**No predicen el fallo judicial.**")

    escenarios = (d_escenarios or {}).get("escenarios",[])
    if not escenarios:
        st.warning("Sin escenarios. Ejecuta el sistema primero."); st.stop()

    # Selector de escenario (tabs)
    tabs = st.tabs([f"{e['id']}: {e['nombre']}" for e in escenarios])

    for tab, esc in zip(tabs, escenarios):
        with tab:
            analisis = esc.get("analisis",{})
            nivel    = analisis.get("nivel_impacto","?")
            icono    = {"bajo":"🟢","medio":"🟡","alto":"🔴","critico":"⛔"}.get(nivel,"❓")

            st.markdown(f"**Supuesto:** {esc.get('supuesto_explicito','')}")
            if esc.get("elemento_perturbado"):
                st.info(f"Elemento perturbado: `{esc['elemento_perturbado']}`")

            # Antes / Después
            antes   = esc.get("metricas_antes",{})
            despues = esc.get("metricas_despues",{})

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Métricas ANTES de la perturbación:**")
                if antes:
                    st.markdown(f"- Cobertura probatoria: `{antes.get('cobertura_probatoria','?')}`")
                    st.markdown(f"- Vacíos críticos: `{antes.get('vacios_criticos','?')}`")
                    st.markdown(f"- Trazabilidad: `{antes.get('trazabilidad','?')}`")
            with col_b:
                st.markdown("**Métricas DESPUÉS de la perturbación:**")
                if despues:
                    delta_cp = (despues.get("cobertura_probatoria",0)
                                - antes.get("cobertura_probatoria",0))
                    st.markdown(f"- Cobertura probatoria: `{despues.get('cobertura_probatoria','?')}` "
                                f"({'▼' if delta_cp < 0 else '▲'} {abs(delta_cp):.2f})")
                    st.markdown(f"- Vacíos críticos: `{despues.get('vacios_criticos','?')}`")
                    st.markdown(f"- Trazabilidad: `{despues.get('trazabilidad','?')}`")
                else:
                    st.caption("Solo disponible para S1 (perturbación real)")

            st.markdown(f"**Impacto:** {icono} `{nivel}`")

            if analisis.get("hechos_afectados"):
                st.markdown(f"**Hechos afectados:** `{', '.join(analisis['hechos_afectados'])}`")
            if analisis.get("rutas_debilitadas"):
                st.markdown("**Rutas debilitadas:**")
                for r in analisis["rutas_debilitadas"]:
                    st.markdown(f"  — {r}")

            st.success(f"💡 **Acción sugerida:** {analisis.get('accion_sugerida','')}")
            st.caption(f"ℹ️ {analisis.get('incertidumbre','')}  ·  Requiere revisión humana.")


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 6 — AUDITORÍA
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🚨  Auditoría":
    st.title("🚨 Auditoría y trazabilidad")

    # Cargar trazas
    trazas_path = OUTPUT_DIR / "trazas.jsonl"
    trazas = []
    if trazas_path.exists():
        with open(trazas_path, encoding="utf-8") as f:
            for linea in f:
                try: trazas.append(json.loads(linea))
                except: pass

    rep_aud = next((t for t in reversed(trazas) if t.get("agente")=="auditor"), {})

    # Score + checklist + loop en una fila
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown('<p class="seccion-titulo">Score del auditor</p>',
                    unsafe_allow_html=True)
        score = rep_aud.get("score_calidad")
        if score is not None:
            color = "#2e7d32" if score>=0.7 else "#f57f17" if score>=0.5 else "#c62828"
            st.markdown(f"<h2 style='color:{color}'>{score:.2f} / 1.00</h2>",
                        unsafe_allow_html=True)
            st.caption(f"Alertas: {rep_aud.get('alertas_generadas','?')} · "
                       f"Rev. humana: {'SÍ ⚠️' if rep_aud.get('revision_requerida') else 'No urgente'}")

    with col_b:
        st.markdown('<p class="seccion-titulo">PreCompletion Checklist</p>',
                    unsafe_allow_html=True)
        if d_checklist:
            if d_checklist.get("aprobado"):
                st.success("✅ APROBADO")
            else:
                st.error(f"❌ BLOQUEADO")
                st.caption(d_checklist.get("razon_bloqueo","")[:120])
        else:
            st.info("Sin datos")

    with col_c:
        st.markdown('<p class="seccion-titulo">Loop Detection</p>',
                    unsafe_allow_html=True)
        if d_loop:
            if d_loop.get("loop_detectado"):
                st.error(f"⚠️ Loop: {d_loop.get('tipo','?')}")
                st.caption(d_loop.get("agente_problema",""))
            else:
                st.success("✅ Sin loops")
                st.caption(f"{len(trazas)} trazas analizadas")
        else:
            st.info("Sin datos")

    # Detalle del checklist
    if d_checklist:
        st.divider()
        col_ok, col_no = st.columns(2)
        with col_ok:
            st.markdown("**Ítems aprobados:**")
            for i in d_checklist.get("items_aprobados",[]):
                st.markdown(f"  ✅ {i}")
        with col_no:
            st.markdown("**Ítems fallidos:**")
            for i in d_checklist.get("items_fallidos",[]):
                st.markdown(f"  ❌ {i}")

    # Log de trazas
    st.divider()
    st.markdown('<p class="seccion-titulo">Log de ejecución (trazas)</p>',
                unsafe_allow_html=True)
    if trazas:
        df_t = pd.DataFrame([{
            "Agente":    t.get("agente","?"),
            "Tipo":      t.get("tipo","?"),
            "Timestamp": t.get("timestamp","")[:19],
            "Errores":   len(t.get("errores",[])),
        } for t in trazas])
        st.dataframe(df_t, hide_index=True, use_container_width=True)

        errores = [f"[{t.get('agente','?')}] {e}"
                   for t in trazas for e in t.get("errores",[])]
        if errores:
            st.error(f"{len(errores)} error(es) registrados:")
            for e in errores: st.markdown(f"  - {e}")
        else:
            st.success("✅ Sin errores en la ejecución.")

    # Preguntas sugeridas
    if d_dash and d_dash.get("preguntas_sugeridas"):
        st.divider()
        st.markdown('<p class="seccion-titulo">💬 Preguntas para audiencia</p>',
                    unsafe_allow_html=True)
        preguntas = d_dash["preguntas_sugeridas"]
        tipos = sorted({p.get("tipo","?") for p in preguntas})
        filtro_tipo = st.selectbox("Tipo", ["Todos"]+tipos)
        pf = preguntas if filtro_tipo=="Todos" else [
            p for p in preguntas if p.get("tipo")==filtro_tipo
        ]
        for p in pf[:8]:
            with st.container():
                st.markdown(f"**{p.get('pregunta','')}**")
                st.caption(f"Tipo: {p.get('tipo','')} · {p.get('contexto','')[:60]}")
                if p.get("contramedida"):
                    st.markdown(f"  💡 Contramedida: {p['contramedida'][:100]}")
                st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 7 — EXPLICACIONES
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "💡  Explicaciones":
    st.title("💡 Explicaciones de decisiones")
    st.caption("Por qué el sistema tomó cada decisión — con fuente citada del expediente.")

    if not d_expl:
        st.warning("Sin explicaciones. Ejecuta el sistema primero."); st.stop()

    explicaciones = d_expl.get("explicaciones",[])
    if not explicaciones:
        st.info("El sistema no generó explicaciones en esta ejecución."); st.stop()

    # Score de explicabilidad
    mexpl = (d_metricas or {}).get("explicabilidad",{})
    if mexpl:
        c1,c2,c3 = st.columns(3)
        c1.metric("Total",      mexpl.get("total_explicaciones",0))
        c2.metric("Aprobadas",  mexpl.get("explicaciones_aprobadas",0))
        c3.metric("Score",      f"{mexpl.get('score_explicabilidad',0):.0%}")

    st.divider()

    tipos = sorted({e.get("tipo","?") for e in explicaciones})
    filtro = st.multiselect("Filtrar por tipo", tipos, default=tipos)
    ef = [e for e in explicaciones if e.get("tipo") in filtro]

    for exp in ef:
        estado_v = exp.get("estado_verificacion","sin_verificar")
        icono_v  = "✅" if estado_v=="aprobada" else "⚠️" if estado_v=="sin_verificar" else "❌"
        with st.expander(
            f"{icono_v} **{exp.get('tipo','?')}** — Ref: `{exp.get('referencia','?')}`"
        ):
            st.markdown(f"**Decisión:** {exp.get('decision','')}")
            st.markdown(f"**Razón:** {exp.get('razon','')}")
            st.caption(f"Fuente: `{exp.get('fuente_citada','?')}` · "
                       f"Verificación: {estado_v}")
            if exp.get("razon_rechazo"):
                st.warning(f"Rechazada: {exp['razon_rechazo']}")

    st.divider()
    st.download_button(
        "⬇️ Descargar explicaciones JSON",
        json.dumps(d_expl, ensure_ascii=False, indent=2).encode(),
        "explicaciones.json","application/json",
    )
