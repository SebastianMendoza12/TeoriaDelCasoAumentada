"""
dashboard_node.py — Agente 11: Preparador del Dashboard
Tipo: Python puro (sin LLM)
Función: Consolida todos los artefactos generados por los agentes anteriores
         en una estructura lista para consumir desde el dashboard de Streamlit.
         Genera además un resumen ejecutivo en texto y un reporte exportable en JSON.
Entrada: matriz_hpn, grafo, metricas, escenarios, ataques, reporte_auditoria, trazas
Salida:  dashboard_data (guardado en output/dashboard_data.json)
"""

import json
import datetime
from pathlib import Path
from src.state import CaseState
from src.config import OUTPUT_DIR


OUTPUT_DASHBOARD = OUTPUT_DIR / "dashboard_data.json"


def _semaforo_caso(metricas_hpn: dict) -> str:
    """
    Calcula el semáforo general del caso basado en las métricas HPN.
    Verde: preparación buena. Amarillo: parcial. Rojo: crítico.
    """
    cob_prob = metricas_hpn.get("cobertura_probatoria", 0)
    cob_norm = metricas_hpn.get("cobertura_normativa", 0)
    vacios   = metricas_hpn.get("vacios_criticos", 0)
    total    = metricas_hpn.get("total_filas", 1)

    score = (cob_prob + cob_norm) / 2
    pct_vacios = vacios / max(total, 1)

    if score >= 0.70 and pct_vacios <= 0.20:
        return "verde"
    elif score >= 0.50 and pct_vacios <= 0.40:
        return "amarillo"
    else:
        return "rojo"


def _resumen_ejecutivo(state: CaseState, semaforo: str) -> str:
    """
    Genera un resumen ejecutivo en texto plano para el abogado.
    Sin tecnicismos innecesarios — orientado a decisión.
    """
    matriz   = state.get("matriz_hpn", [])
    metricas = state.get("metricas", {}).get("hpn", {})
    ataques  = state.get("ataques", [])
    vacios   = state.get("vacios", [])

    total       = len(matriz)
    completas   = sum(1 for f in matriz if f.get("estado") == "completo")
    criticas    = sum(1 for f in matriz if f.get("estado") == "vacio_critico")
    alto_riesgo = sum(1 for f in matriz if f.get("riesgo") in {"alto", "critico"})
    cob_prob    = metricas.get("cobertura_probatoria", 0)
    cob_norm    = metricas.get("cobertura_normativa", 0)
    n_ataques   = len(ataques)

    estado_label = {
        "verde":    "BUENO — el caso está bien preparado",
        "amarillo": "PARCIAL — hay vacíos que deben resolverse antes de la audiencia",
        "rojo":     "CRÍTICO — la teoría del caso tiene vacíos graves",
    }.get(semaforo, "DESCONOCIDO")

    resumen = f"""RESUMEN EJECUTIVO DEL CASO
Generado: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
Estado general: {estado_label}

TEORÍA DEL CASO
- Total de elementos jurídicos analizados: {total}
- Elementos con soporte completo: {completas} ({round(completas/max(total,1)*100)}%)
- Vacíos críticos sin prueba: {criticas}
- Elementos de alto riesgo: {alto_riesgo}

COBERTURA
- Cobertura probatoria: {cob_prob:.0%}
- Cobertura normativa: {cob_norm:.0%}

ATAQUES IDENTIFICADOS DE LA CONTRAPARTE
- Total de ataques detectados: {n_ataques}
- Ataques certeros: {sum(1 for a in ataques if a.get("certeza") == "certero")}
- Ataques hipotéticos: {sum(1 for a in ataques if a.get("certeza") == "hipotetico")}

VACÍOS PROBATORIOS PRIORITARIOS
"""
    for v in vacios[:3]:
        resumen += f"- {v.get('descripcion', '')} → {v.get('accion_sugerida', '')}\n"

    resumen += "\nADVERTENCIA: Este resumen es orientativo. La decisión jurídica final permanece en cabeza humana."
    return resumen


def _alertas_accionables(state: CaseState) -> list[dict]:
    """
    Genera alertas priorizadas y accionables para el abogado.
    Cada alerta tiene: tipo, descripcion, prioridad y accion.
    """
    alertas = []
    matriz  = state.get("matriz_hpn", [])
    metricas_red = state.get("metricas", {}).get("red", {})
    reporte_auditoria = state.get("reporte_auditoria", {})

    # Alerta por vacíos críticos
    vacios = [f for f in matriz if f.get("estado") == "vacio_critico"]
    if vacios:
        alertas.append({
            "tipo":        "vacio_critico",
            "prioridad":   "critica",
            "descripcion": f"{len(vacios)} elemento(s) jurídico(s) sin prueba de soporte.",
            "accion":      "Obtener documentos, testimonios o peritajes antes de la audiencia.",
            "filas":       [f.get("id") for f in vacios],
        })

    # Alerta por puntos únicos de falla
    puntos_falla = metricas_red.get("puntos_unicos_de_falla", [])
    if puntos_falla:
        alertas.append({
            "tipo":        "punto_unico_falla",
            "prioridad":   "alta",
            "descripcion": f"Nodo(s) crítico(s) detectado(s): {', '.join(puntos_falla[:3])}. "
                           "Su eliminación colapsa rutas argumentativas principales.",
            "accion":      "Buscar prueba redundante que soporte los mismos hechos.",
            "nodos":       puntos_falla,
        })

    # Alerta por prueba más frágil
    prueba_fragil = metricas_red.get("prueba_mas_fragil")
    if prueba_fragil:
        alertas.append({
            "tipo":        "fragilidad_probatoria",
            "prioridad":   "alta",
            "descripcion": f"La prueba '{prueba_fragil}' es la más frágil de la red. "
                           "Su exclusión tendría el mayor impacto negativo.",
            "accion":      "Proteger esta prueba y buscar al menos una prueba redundante.",
            "prueba":      prueba_fragil,
        })

    # Alertas del auditor
    for alerta_auditor in reporte_auditoria.get("alertas", []):
        if alerta_auditor.get("severidad") == "critico":
            alertas.append({
                "tipo":        "auditoria_" + alerta_auditor.get("tipo", "general"),
                "prioridad":   "critica",
                "descripcion": alerta_auditor.get("descripcion", ""),
                "accion":      "Revisar y corregir antes de usar en memorial o audiencia.",
                "fila":        alerta_auditor.get("fila_hpn", ""),
            })

    # Alerta por baja trazabilidad
    trazabilidad = state.get("metricas", {}).get("hpn", {}).get("trazabilidad", 1.0)
    if trazabilidad < 0.6:
        alertas.append({
            "tipo":        "baja_trazabilidad",
            "prioridad":   "media",
            "descripcion": f"Solo el {trazabilidad:.0%} de las filas HPN tienen fuente verificable.",
            "accion":      "Verificar y agregar referencias a páginas del expediente.",
        })

    # Ordenar por prioridad
    orden = {"critica": 0, "alta": 1, "media": 2, "baja": 3}
    alertas.sort(key=lambda a: orden.get(a.get("prioridad", "baja"), 3))
    return alertas


def _preguntas_sugeridas(state: CaseState) -> list[dict]:
    """
    Genera preguntas sugeridas para interrogatorio y contraexamen
    basadas en las filas de mayor riesgo y los ataques identificados.
    """
    preguntas = []
    matriz  = state.get("matriz_hpn", [])
    ataques = state.get("ataques", [])

    # Preguntas por filas de alto riesgo
    for fila in matriz:
        if fila.get("riesgo") in {"alto", "critico"}:
            hecho = fila.get("hecho", {})
            texto = hecho.get("texto", "") if isinstance(hecho, dict) else str(hecho)
            preguntas.append({
                "contexto":    fila.get("elemento_juridico", ""),
                "pregunta":    f"¿Puede demostrar con documentos que {texto[:120]}?",
                "tipo":        "interrogatorio",
                "fila_origen": fila.get("id"),
            })

    # Preguntas por contradicciones
    for fila in matriz:
        for contradiccion in fila.get("contradicciones", []):
            preguntas.append({
                "contexto":    fila.get("elemento_juridico", ""),
                "pregunta":    f"¿Cómo explica la contradicción: {contradiccion[:120]}?",
                "tipo":        "contraexamen",
                "fila_origen": fila.get("id"),
            })

    # Preguntas por ataques adversariales
    for ataque in ataques:
        if ataque.get("certeza") == "certero":
            preguntas.append({
                "contexto":    ataque.get("tipo", ""),
                "pregunta":    f"¿Tiene respuesta preparada para: {ataque.get('descripcion', '')[:120]}?",
                "tipo":        "preparacion_defensa",
                "contramedida": ataque.get("contramedida", ""),
            })

    return preguntas[:15]  # máximo 15 preguntas


def dashboard_node(state: CaseState) -> dict:
    """
    Agente 11: Consolida todos los resultados en dashboard_data.json
    listo para ser consumido por Streamlit.
    """
    print("[dashboard_node]  Consolidando artefactos para el dashboard...")

    errores = []
    metricas_hpn = state.get("metricas", {}).get("hpn", {})

    try:
        semaforo          = _semaforo_caso(metricas_hpn)
        resumen_ejecutivo = _resumen_ejecutivo(state, semaforo)
        alertas           = _alertas_accionables(state)
        preguntas         = _preguntas_sugeridas(state)

        dashboard_data = {
            # Metadatos
            "case_id":            state.get("case_id"),
            "timestamp":          datetime.datetime.now().isoformat(),
            "generado_por":       "dashboard_node v1.0",

            # Semáforo general
            "semaforo":           semaforo,
            "resumen_ejecutivo":  resumen_ejecutivo,

            # Artefactos consolidados
            "total_segmentos":    len(state.get("segmentos", [])),
            "total_hechos":       len(state.get("hechos", [])),
            "total_pruebas":      len(state.get("pruebas", [])),
            "total_normas":       len(state.get("normas", [])),
            "total_filas_hpn":    len(state.get("matriz_hpn", [])),
            "total_ataques":      len(state.get("ataques", [])),
            "total_escenarios":   len(state.get("escenarios", [])),

            # Métricas clave
            "metricas_resumen": {
                "cobertura_probatoria":          metricas_hpn.get("cobertura_probatoria", 0),
                "cobertura_normativa":           metricas_hpn.get("cobertura_normativa", 0),
                "cobertura_elementos_juridicos": metricas_hpn.get("cobertura_elementos_juridicos", 0),
                "vacios_criticos":               metricas_hpn.get("vacios_criticos", 0),
                "indice_contradiccion":          metricas_hpn.get("indice_contradiccion", 0),
                "trazabilidad":                  metricas_hpn.get("trazabilidad", 0),
                "acciones_pendientes":           metricas_hpn.get("acciones_pendientes", 0),
            },

            # Score del auditor
            "score_calidad_auditoria": state.get("reporte_auditoria", {}).get("score_calidad", 0),
            "revision_humana_requerida": state.get("revision_humana_requerida", True),

            # Alertas y preguntas
            "alertas_accionables":    alertas,
            "preguntas_sugeridas":    preguntas,

            # Cronología (para visualización)
            "cronologia":             state.get("cronologia", []),

            # Disclaimer obligatorio
            "disclaimer": (
                "Este sistema apoya la preparación del abogado litigante. "
                "No predice resultados judiciales ni sustituye la valoración "
                "probatoria profesional. La decisión jurídica final permanece "
                "en cabeza humana."
            ),
        }

        # Guardar en disco
        with open(OUTPUT_DASHBOARD, "w", encoding="utf-8") as f:
            json.dump(dashboard_data, f, ensure_ascii=False, indent=2)

        print(f"[dashboard_node]  ✓  semaforo={semaforo} | "
              f"alertas={len(alertas)} | preguntas={len(preguntas)}")
        print(f"[dashboard_node]  💾  {OUTPUT_DASHBOARD}")

    except Exception as e:
        msg = f"Error en dashboard_node: {e}"
        errores.append(msg)
        print(f"[dashboard_node]  ✗  {msg}")
        dashboard_data = {}

    traza = {
        "agente":    "dashboard_node",
        "tipo":      "python_puro",
        "timestamp": datetime.datetime.now().isoformat(),
        "alertas_generadas":   len(alertas) if not errores else 0,
        "preguntas_generadas": len(preguntas) if not errores else 0,
        "errores":   errores,
    }

    return {
        "trazas":  [traza],
        "errores": errores,
    }
