"""
report_export.py
Generador del "Reporte exportable" exigido por el enunciado (8.2, E8):
un único archivo HTML autocontenido con resumen ejecutivo, matriz HPN,
red multicapa, métricas, escenarios y estado de revisión humana.

Se genera a partir de los artefactos ya guardados en output/ — no vuelve
a llamar al LLM. Pensado para correr al final de graph.py o desde un
botón del dashboard de Streamlit.

Uso:
    python -m src.tools.report_export
    # o, programáticamente:
    from src.tools.report_export import generar_reporte
    generar_reporte()
"""

import json
import datetime
from pathlib import Path
from src.config import OUTPUT_DIR

OUTPUT_REPORTE = OUTPUT_DIR / "reporte_final.html"


def _cargar(nombre: str) -> dict:
    ruta = OUTPUT_DIR / nombre
    if not ruta.exists():
        return {}
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def _tabla_hpn(filas: list[dict]) -> str:
    if not filas:
        return "<p><em>Matriz HPN vacía.</em></p>"
    filas_html = []
    for f in filas:
        hecho = f.get("hecho", {})
        texto_hecho = hecho.get("texto", "") if isinstance(hecho, dict) else str(hecho)
        filas_html.append(f"""
        <tr>
          <td>{f.get('id','')}</td>
          <td>{f.get('elemento_juridico','')}</td>
          <td>{texto_hecho}</td>
          <td>{len(f.get('pruebas', []))}</td>
          <td>{len(f.get('normas', []))}</td>
          <td class="estado-{f.get('estado','')}">{f.get('estado','')}</td>
          <td class="riesgo-{f.get('riesgo','')}">{f.get('riesgo','')}</td>
          <td>{f.get('revision_humana','')}</td>
          <td>{f.get('accion_sugerida','')}</td>
        </tr>""")
    return f"""
    <table>
      <thead>
        <tr><th>ID</th><th>Elemento jurídico</th><th>Hecho</th><th>Pruebas</th>
            <th>Normas</th><th>Estado</th><th>Riesgo</th><th>Revisión</th><th>Acción sugerida</th></tr>
      </thead>
      <tbody>{''.join(filas_html)}</tbody>
    </table>"""


def _tabla_metricas(metricas_hpn: dict, metricas_red: dict) -> str:
    filas_hpn = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in metricas_hpn.items()
    )
    filas_red = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>"
        for k, v in metricas_red.items()
        if not isinstance(v, (list, dict)) or len(str(v)) < 200
    )
    return f"""
    <h3>Métricas de la Matriz HPN</h3>
    <table><tbody>{filas_hpn}</tbody></table>
    <h3>Métricas de la Red Multicapa</h3>
    <table><tbody>{filas_red}</tbody></table>"""


def _bloque_escenarios(escenarios: list[dict]) -> str:
    if not escenarios:
        return "<p><em>No hay escenarios simulados.</em></p>"
    bloques = []
    for esc in escenarios:
        analisis = esc.get("analisis", {})
        bloques.append(f"""
        <div class="escenario">
          <h4>{esc.get('id','')}: {esc.get('nombre','')}</h4>
          <p><strong>Supuesto:</strong> {esc.get('supuesto_explicito','')}</p>
          <p><strong>Nivel de impacto:</strong> {analisis.get('nivel_impacto','?')}</p>
          <p><strong>Acción sugerida:</strong> {analisis.get('accion_sugerida','')}</p>
          <p class="incertidumbre"><strong>Incertidumbre:</strong> {analisis.get('incertidumbre','')}</p>
        </div>""")
    return "".join(bloques)


def generar_reporte() -> Path:
    datos_hpn = _cargar("matriz_hpn.json")
    datos_metricas = _cargar("metricas.json")
    datos_escenarios = _cargar("escenarios.json")
    datos_dashboard = _cargar("dashboard_data.json")

    matriz = datos_hpn.get("filas", [])
    metricas_hpn = datos_metricas.get("hpn", {})
    metricas_red = datos_metricas.get("red", {})
    escenarios = datos_escenarios.get("escenarios", [])
    resumen_ejecutivo = datos_dashboard.get(
        "resumen_ejecutivo", "No se generó resumen ejecutivo (corre primero el pipeline)."
    )
    semaforo = datos_dashboard.get("semaforo", "desconocido")
    color_semaforo = {"verde": "#2e7d32", "amarillo": "#f9a825", "rojo": "#c62828"}.get(
        semaforo, "#666"
    )

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Reporte — Teoría del Caso Aumentada</title>
<style>
  body {{ font-family: Arial, Helvetica, sans-serif; margin: 40px; color: #1a1a2e; }}
  h1 {{ border-bottom: 3px solid {color_semaforo}; padding-bottom: 8px; }}
  .semaforo {{ display: inline-block; padding: 6px 14px; border-radius: 6px;
               background: {color_semaforo}; color: white; font-weight: bold; }}
  table {{ border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 13px; }}
  th, td {{ border: 1px solid #ccc; padding: 6px 8px; text-align: left; }}
  th {{ background: #f0f0f5; }}
  .estado-completo {{ color: #2e7d32; font-weight: bold; }}
  .estado-vacio_critico {{ color: #c62828; font-weight: bold; }}
  .riesgo-alto, .riesgo-critico {{ color: #c62828; font-weight: bold; }}
  .escenario {{ border-left: 4px solid #4e79a7; padding: 8px 16px; margin: 12px 0; background: #f7f8fa; }}
  .incertidumbre {{ font-style: italic; color: #555; }}
  .disclaimer {{ margin-top: 40px; padding: 16px; background: #fff3cd; border: 1px solid #f9a825; border-radius: 6px; }}
  pre {{ background: #f5f5f5; padding: 12px; white-space: pre-wrap; }}
</style>
</head>
<body>
  <h1>Reporte — Teoría del Caso Aumentada</h1>
  <p>Generado: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
     &nbsp;|&nbsp; Case ID: {datos_hpn.get('case_id','sin ID')}
     &nbsp;|&nbsp; Estado general: <span class="semaforo">{semaforo.upper()}</span></p>

  <h2>1. Resumen ejecutivo</h2>
  <pre>{resumen_ejecutivo}</pre>

  <h2>2. Matriz HPN</h2>
  {_tabla_hpn(matriz)}

  <h2>3. Red multicapa</h2>
  <p>Ver visualización interactiva en <code>red_multicapa.html</code>
     (no incluida aquí para mantener este reporte liviano).</p>

  <h2>4. Métricas</h2>
  {_tabla_metricas(metricas_hpn, metricas_red)}

  <h2>5. Escenarios simulados</h2>
  {_bloque_escenarios(escenarios)}

  <h2>6. Revisión humana</h2>
  <p>Filas sin revisar: {sum(1 for f in matriz if f.get('revision_humana') == 'sin_revisar')}
     de {len(matriz)}.</p>

  <div class="disclaimer">
    <strong>Advertencia:</strong> Este reporte apoya la preparación del abogado
    litigante. No predice resultados judiciales ni sustituye la valoración
    probatoria profesional. La decisión jurídica final permanece en cabeza humana.
  </div>
</body>
</html>"""

    OUTPUT_REPORTE.write_text(html, encoding="utf-8")
    print(f"[report_export]  ✓  Reporte generado → {OUTPUT_REPORTE}")
    return OUTPUT_REPORTE


if __name__ == "__main__":
    generar_reporte()