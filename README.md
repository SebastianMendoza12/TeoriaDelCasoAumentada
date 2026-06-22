# Sistema Multiagente para Teoría del Caso Aumentada

> Proyecto tercer corte — Ciencia de Datos 2026-1  
> Programa Ingeniería de Sistemas — Universidad de Pamplona  

**La decisión jurídica final siempre permanece en cabeza humana.**

---

## ¿Qué hace este sistema?

Recibe un expediente judicial en PDF y lo transforma en artefactos computacionales que apoyan la preparación estratégica del abogado litigante:

```
expediente.pdf
      │
      ▼
  [Ingesta]  →  texto segmentado con página y hash
      │
      ▼
  [Extractor] →  hechos, actores, cronología
      │
      ▼
  [Probatorio + Normativo]  →  catálogo de pruebas y normas
      │
      ▼
  [Constructor HPN]  →  Matriz Hecho · Prueba · Norma
      │
      ▼
  [Red Multicapa]  →  grafo de dependencias jurídicas
      │
      ▼
  [Métricas]  →  cobertura, fragilidad, puntos de falla
      │
      ▼
  [Adversarial + Simulador]  →  ataques y escenarios
      │
      ▼
  [Auditor]  →  reporte de calidad y trazabilidad
      │
      ▼
  [Dashboard]  →  interfaz accionable para el abogado
```

---

## Arquitectura multiagente

El sistema usa **LangGraph** para orquestar **13 agentes** con roles definidos y estado compartido. Cada agente tiene una responsabilidad única, salida auditable y registro de traza.

| Agente | Tipo | Función |
|--------|------|---------|
| `intake` | Python puro | Lee el PDF, segmenta por página, asigna hash |
| `extractor` | LLM (Groq) | Extrae hechos, actores y cronología |
| `probatorio` | LLM (Groq) | Cataloga pruebas, detecta vacíos y contradicciones |
| `normativo` | LLM (Groq) | Identifica normas y requisitos jurídicos aplicables |
| `hpn_builder` | LLM (Groq) | Construye y valida la Matriz HPN fila por fila |
| `network_builder` | Python puro | Construye la red multicapa con NetworkX |
| `metrics` | Python puro | Calcula cobertura, fragilidad y centralidad |
| `adversarial` | LLM (Groq) | Simula ataques de la contraparte y excepciones |
| `simulator` | LLM (Groq) | Ejecuta escenarios de perturbación S1–S4 |
| `auditor` | LLM (Groq) | Verifica fuentes, trazabilidad y coherencia |
| `dashboard_node` | Python puro | Consolida artefactos, genera alertas y semáforo |
| `explanation_builder` | LLM (Groq) | Explica POR QUÉ el sistema tomó cada decisión, citando fuente |
| `explanation_verifier` | Python puro | Verifica que cada explicación tenga fuente real (árbitro de explicabilidad) |

Los agentes `intake`, `network_builder`, `metrics` y `dashboard_node` son **determinísticos** (sin LLM). El resto usa **llama-3.3-70b** vía Groq (gratuito).


---

## Artefactos generados

Todos se guardan en la carpeta `output/` al ejecutar el sistema:

| Archivo | Entregable | Descripción |
|---------|-----------|-------------|
| `output/matriz_hpn.json` | E4 | Matriz HPN completa con estado, riesgo y acción |
| `output/grafo.json` | E5 | Red multicapa exportable (nodos, capas, aristas) |
| `output/metricas.json` | E6 | Indicadores de cobertura, fragilidad y centralidad |
| `output/escenarios.json` | E7 | 4 escenarios procesales con efectos antes/después |
| `output/trazas.jsonl` | E3 | Log completo: agente, entrada, salida, timestamp |
| `output/dashboard_data.json` | E8 | Resumen ejecutivo, alertas y preguntas sugeridas |
| `output/red_multicapa.html` | E5 | Visualización interactiva de la red (PyVis) |
| `output/matriz_hpn.csv` | E4 | Matriz HPN en formato CSV |
| `output/explicaciones.json` | — | Explicaciones de decisiones + verificación |
| `output/checklist.json` | — | Veredicto del PreCompletionChecklist |
| `output/loop_detection.json` | — | Diagnóstico de loops en la ejecución |
| `output/reporte_final.html` | E8 | Reporte exportable consolidado (resumen, matriz, métricas, escenarios) |

---

## Requisitos

- Python 3.11 o superior
- Cuenta gratuita en [Groq](https://console.groq.com) (API Key gratis, sin tarjeta)
- El expediente judicial en PDF (archivo de texto, no escaneado)

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/SebastianMendoza12/TeoriaDelCasoAumentada.git
cd TeoriaDelCasoAumentada
```

### 2. Crear entorno virtual

```bash
python -m venv .venv

# Linux / Mac
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Copia el archivo de ejemplo y agrega tus API keys. Groq se usa como proveedor principal; Cerebras es opcional y funciona como respaldo si Groq responde con rate limit.

```bash
cp .env.example .env
```

Edita `.env`:

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
CEREBRAS_API_KEY=csk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Para obtener tu API key gratuita: [console.groq.com](https://console.groq.com) → Create API Key.

---

## Uso

### Paso 1 — Agregar el expediente

Copia el PDF del caso en la carpeta `data/input/`:

```bash
cp /ruta/al/expediente.pdf data/input/expediente.pdf
```

El PDF debe ser de texto (no escaneado). Si el profesor entrega el PDF en clase, simplemente copiarlo aquí y ejecutar el sistema.

### Paso 2 — Ejecutar el sistema multiagente

```bash
python src/graph.py
```

El sistema procesa el expediente y genera todos los artefactos en `output/`. El proceso tarda entre 1 y 3 minutos dependiendo del tamaño del PDF.

Verás en consola el avance de cada agente:

```
[intake]           ✓  47 segmentos extraídos
[extractor]        ✓  12 hechos | 5 actores | 8 eventos
[probatorio]       ✓  9 pruebas | 2 vacíos críticos
[normativo]        ✓  6 normas identificadas
[hpn_builder]      ✓  11 filas HPN generadas (9 válidas, 2 pendientes)
[network_builder]  ✓  28 nodos | 34 aristas | 4 capas
[metrics]          ✓  cobertura: 0.82 | fragilidad calculada
[adversarial]      ✓  4 ataques identificados
[simulator]        ✓  4 escenarios simulados
[auditor]          ✓  score de calidad: 0.79 | 2 alertas
[dashboard_node]   ✓  semaforo=amarillo | 3 alertas | 8 preguntas
```

### Paso 3 — Abrir el dashboard

```bash
streamlit run dashboard/app.py
```

Se abre automáticamente en el navegador en `http://localhost:8501`.

---

## Estructura del proyecto

```
teoria-del-caso-aumentada/
│
├── .gitignore
├── .env.example
├── README.md
├── requirements.txt
│
├── data/
│   └── input/
│       └── expediente.pdf          ← PDF del caso (agregar antes de ejecutar)
│
├── src/
│   ├── state.py                    ← Estado compartido entre agentes
│   ├── graph.py                    ← Grafo LangGraph + punto de entrada principal
│   ├── config.py                   ← Modelo LLM, rutas, umbrales
│   │
│   ├── agents/
│   │   ├── intake.py               ← Extracción PDF (Python puro)
│   │   ├── extractor.py            ← Hechos, actores, cronología
│   │   ├── probatorio.py           ← Pruebas y vacíos
│   │   ├── normativo.py            ← Normas aplicables
│   │   ├── hpn_builder.py          ← Matriz HPN
│   │   ├── network_builder.py      ← Red multicapa (Python puro)
│   │   ├── metrics.py              ← Métricas de red y HPN (Python puro)
│   │   ├── adversarial.py          ← Ataques y excepciones
│   │   ├── simulator.py            ← Escenarios S1–S4
│   │   ├── auditor.py              ← Verificación de calidad
│   │   └── dashboard_node.py       ← Alertas, semáforo, preguntas
│   │
│   └── tools/
│       ├── pdf_tools.py            ← PyMuPDF: segmentación y hash
│       ├── hpn_tools.py            ← Validación de filas HPN
│       └── graph_tools.py          ← NetworkX: construcción y métricas
│
├── output/                         ← Generado al ejecutar (ignorado en git)
│   ├── matriz_hpn.json
│   ├── grafo.json
│   ├── metricas.json
│   ├── escenarios.json
│   ├── trazas.jsonl
│   ├── dashboard_data.json
│   └── red_multicapa.html
│
└── dashboard/
    └── app.py                      ← Dashboard Streamlit del abogado
```

---

## Stack tecnológico

| Componente | Tecnología | Por qué |
|-----------|-----------|---------|
| Orquestación multiagente | LangGraph | Grafo de agentes con estado compartido y flujo controlado |
| LLM (gratis) | Groq — llama-3.3-70b | API gratuita, rápida, sin necesidad de tarjeta |
| Extracción de PDF | PyMuPDF (fitz) | Extrae texto con número de página, ligero y confiable |
| Red compleja / métricas | NetworkX | Centralidad, fragilidad, puntos de falla, grafo dirigido tipado |
| Validación de datos | Pydantic v2 | Verifica esquemas HPN antes de guardar |
| Dashboard | Streamlit | Despliegue local rápido, filtros interactivos |
| Visualización de red | PyVis | Grafo interactivo en el navegador |
| Exportación | pandas + json | CSV y JSON para todos los artefactos |

---

## Métricas implementadas

### De la Matriz HPN

| Métrica | Fórmula / criterio |
|--------|-------------------|
| Cobertura de elementos jurídicos | % de filas con hecho + prueba + norma |
| Cobertura probatoria | % de hechos esenciales con prueba admisible |
| Cobertura normativa | % de hechos vinculados a norma o precedente |
| Índice de vacíos críticos | N.º de filas sin prueba sobre total |
| Índice de contradicción | N.º de filas con pruebas incompatibles |
| Trazabilidad | % de filas con fuente del expediente verificable |
| Acciones pendientes | N.º de filas que exigen diligencia adicional |

### De la Red Multicapa

| Métrica | Utilidad jurídica |
|--------|------------------|
| Grado del nodo | Detecta pruebas aisladas o hiperconectadas |
| Centralidad de intermediación | Identifica puentes críticos de la argumentación |
| Punto único de falla | Nodo cuya eliminación colapsa la ruta principal |
| Fragilidad probatoria | Caída del score si se elimina una prueba |
| Redundancia probatoria | Pruebas independientes que soportan el mismo hecho |

---

## Escenarios simulados

| ID | Nombre | Qué perturba |
|----|--------|-------------|
| S1 | Exclusión de prueba crítica | Elimina la prueba de mayor fuerza |
| S2 | Excepción probada | Activa prescripción, caducidad u otra excepción |
| S3 | Testigo contradictorio | Agrega prueba que contradice el hecho principal |
| S4 | Precedente distinguido | Debilita el soporte jurisprudencial principal |

Cada escenario muestra: supuestos explícitos, hechos afectados, rutas debilitadas, métricas antes/después y acción sugerida al abogado.

---

## Limitaciones y revisión humana

- El sistema **no predice resultados judiciales**.
- Las normas identificadas provienen exclusivamente del expediente. Si el expediente no las menciona, la fila queda en estado `vacio_critico`.
- Toda afirmación marcada como `sin_revisar` en la columna `revision_humana` **debe ser verificada por el abogado** antes de usarse.
- El score de calidad del auditor es orientativo, no definitivo.
- Los escenarios son laboratorio estratégico, no pronóstico del fallo.

---
