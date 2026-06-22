# Documento de Arquitectura
## Sistema Multiagente para Teoría del Caso Aumentada
Ciencia de Datos 2026-1 — Ingeniería de Sistemas — Universidad de Pamplona

> Entregable E3 del enunciado del proyecto: "diagrama de agentes, flujo,
> memoria, herramientas, permisos, formatos y criterios de parada".

---

## 1. Flujo general (grafo de LangGraph)

```
START
  │
  ▼
intake ──────────────► extractor ──────► probatorio ──────► normativo
(Python, sin LLM)       (LLM Groq)        (LLM Groq)         (LLM Groq)
  │ segmenta PDF         │ hechos,         │ pruebas,          │ normas,
  │ con frag_id/hash     │ actores,        │ vacíos             vacíos
  │                      │ cronología                          normativos
  ▼
hpn_builder ─────► network_builder ─────► metrics ─────► adversarial
(LLM + valida-     (Python/NetworkX)      (Python,         (LLM Groq)
 dor determinís-    construye grafo        sin LLM)         ataques de
 tico)              multicapa              cobertura,       contraparte
                                            fragilidad,
                                            centralidad
  │
  ▼
simulator ──────► auditor ──────► dashboard_node ──────► explanation_builder
(LLM + cálculo     (LLM Groq,      (Python, sin LLM)       (LLM Groq)
 determinista       INDEPENDIENTE   consolida artefactos,   explica POR QUÉ
 antes/después)      del generador)  semáforo, alertas        cada decisión
  │
  ▼
explanation_verifier ──────► END
(Python, sin LLM — árbitro
 final de explicabilidad)
```

Middleware aplicado **después** de que el grafo termina (no intercepta
nodos intermedios, dado el flujo secuencial elegido):

- `loop_detection.py`: analiza `trazas` acumuladas, detecta agente
  repetido, salidas idénticas consecutivas o exceso de trazas.
- `pre_completion_checklist.py`: verifica artefactos mínimos
  (`matriz_hpn`, `grafo`, `metricas`, `escenarios`), score del auditor
  contra `UMBRAL_CALIDAD_AUDITOR`, mínimo de 4 escenarios y ausencia de
  errores acumulados. Produce `checklist.json` (aprobado/bloqueado).

## 2. Tabla de agentes: objetivo, entrada, salida, herramientas, límites

| Agente | Tipo | Entrada | Salida | Herramientas | Límite / condición de parada |
|---|---|---|---|---|---|
| intake | Python puro | `pdf_path` | `segmentos` (frag_id, página, texto, hash) | PyMuPDF | Termina al recorrer todas las páginas; no reintenta |
| extractor | LLM (Groq llama-3.3-70b + Cerebras gpt-oss-120b fallback) | `segmentos` | `hechos`, `actores`, `cronologia` | `texto_resumido` (recorta a `MAX_SEGMENTOS_POR_LLAMADA`) | Una sola llamada; si el JSON no parsea, devuelve listas vacías y registra error |
| probatorio | LLM (Groq) | `hechos`, `segmentos` | `pruebas`, `vacios` | igual que extractor | Una sola llamada por ejecución |
| normativo | LLM (Groq) | `hechos`, `segmentos` | `normas`, `vacios_normativos` | igual que extractor | Una sola llamada; nunca inventa artículos no citados en el expediente |
| hpn_builder | LLM (Groq) + validador determinístico | `hechos`, `pruebas`, `normas`, `vacios` | `matriz_hpn` | `validar_fila()` en `hpn_tools.py` | Fila inválida se degrada a `pendiente`, no se descarta |
| network_builder | Python + NetworkX | `matriz_hpn`, `actores` | `grafo` (node_link_data) + `red_multicapa.html` | NetworkX, PyVis | Determinístico; un solo paso |
| metrics | Python puro | `matriz_hpn`, `grafo` | `metricas` (hpn + red) | NetworkX (centralidad, densidad) | Determinístico |
| adversarial | LLM (Groq) | `matriz_hpn` (resumen), `metricas` | `ataques` | — | Una llamada; marca cada ataque como `certero` o `hipotetico` |
| simulator | LLM (Groq) + cálculo determinista | `matriz_hpn`, `metricas` | `escenarios` (S1–S4) | `calcular_metricas_hpn` para antes/después | 4 escenarios fijos; S1 perturba matriz real, S2–S4 deben perturbar igual (ver nota de mejora abajo) |
| auditor | LLM (Groq), **independiente** del generador | `matriz_hpn`, `segmentos`, `trazas` | `reporte_auditoria`, `revision_humana_requerida` | — | Score < `UMBRAL_CALIDAD_AUDITOR` (0.70) fuerza revisión humana |
| dashboard_node | Python puro | todo el estado | `dashboard_data.json` (semáforo, alertas, preguntas, resumen) | — | Determinístico |
| explanation_builder | LLM (Groq) | `matriz_hpn`, `reporte_auditoria` | `explicaciones` | — | Máximo 2 oraciones por explicación; siempre cita fuente |
| explanation_verifier | Python puro | `explicaciones`, `segmentos`, `matriz_hpn` | reporte de explicabilidad (score, aprobadas/rechazadas) | — | Rechaza toda explicación sin `fuente_citada` verificable |

## 3. Memoria

Este sistema **no usa memoria persistente entre ejecuciones** (no hay
`BaseStore`/checkpointer de LangGraph). Cada ejecución parte de un
`estado_inicial` limpio (`graph.py:ejecutar`). La "memoria" del sistema
son los artefactos en `output/*.json` y `output/trazas.jsonl`, que se
sobrescriben en cada corrida. Esto es intencional: evita que un
expediente contamine el análisis de otro caso (riesgo de memory
poisoning descrito en el harness).

Si en el futuro se quisiera comparar evolución entre versiones del mismo
caso, habría que: (a) versionar `output/` por `case_id` en lugar de
sobrescribir, y (b) agregar un `memory_write_guard` que valide qué se
persiste y evite guardar conclusiones no verificadas por el auditor.

## 4. Herramientas y permisos

| Herramienta | Quién la usa | Acceso |
|---|---|---|
| PyMuPDF | intake | Lectura del PDF en `data/input/`. Sin escritura. |
| NetworkX / PyVis | network_builder, metrics | Sin acceso a red ni disco fuera de `output/`. |
| Groq API (llama-3.3-70b) + Cerebras API (gpt-oss-120b fallback) | extractor, probatorio, normativo, hpn_builder, adversarial, simulator, auditor, explanation_builder | Requiere `GROQ_API_KEY` y `CEREBRAS_API_KEY`. Sin acceso a herramientas externas (no hace tool-calling, solo genera JSON). |
| Streamlit | dashboard/app.py | Lectura de `output/*.json`, escritura solo de `data/input/expediente.pdf` al subir archivo. |

Ningún agente tiene acceso a shell, red arbitraria ni puede escribir
fuera de `output/` y `data/input/`. No hay ejecución de código generado
por LLM (los agentes solo producen JSON estructurado, nunca código).

## 5. Formatos de artefactos

Ver tabla completa en `README.md`. Resumen: JSON para todos los
artefactos intermedios; `matriz_hpn` se exporta también a CSV (ver nota
de mejora); grafo en formato `node_link_data` de NetworkX; visualización
de red en HTML (PyVis); trazas en JSONL (una línea por evento de agente).

## 6. Criterios de parada

- Cada agente LLM hace **una sola llamada** por ejecución (no hay loops
  de auto-corrección dentro de un agente).
- El grafo de LangGraph es **secuencial sin ciclos** (no hay edges de
  retorno), por lo que no puede entrar en loop infinito por diseño.
- `loop_detection.py` es una salvaguarda adicional para detectar si, en
  ejecuciones repetidas del usuario (re-correr el pipeline varias veces
  sobre el mismo estado acumulado), las trazas se vuelven repetitivas.
- `pre_completion_checklist.py` no detiene la ejecución (el grafo ya
  terminó) pero marca la corrida como `bloqueado` si faltan artefactos o
  el score de calidad es insuficiente, forzando revisión humana antes de
  usar los resultados en audiencia.

## 7. Regla de frontera profesional

Ningún agente puede declarar un resultado judicial. El disclaimer fijo
del sistema ("La decisión jurídica final permanece en cabeza humana")
se repite en: `dashboard_node._resumen_ejecutivo`, en cada escenario
simulado (`revision_humana_requerida=True`), y en el sidebar de
`dashboard/app.py`.