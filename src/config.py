"""
config.py
Configuración central del sistema: modelo LLM, rutas y umbrales.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Rutas ──────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent
DATA_DIR    = BASE_DIR / "data" / "input"
OUTPUT_DIR  = BASE_DIR / "output"

PDF_PATH    = DATA_DIR / "expediente.pdf"

OUTPUT_HPN       = OUTPUT_DIR / "matriz_hpn.json"
OUTPUT_GRAFO     = OUTPUT_DIR / "grafo.json"
OUTPUT_METRICAS  = OUTPUT_DIR / "metricas.json"
OUTPUT_ESCENARIOS= OUTPUT_DIR / "escenarios.json"
OUTPUT_TRAZAS    = OUTPUT_DIR / "trazas.jsonl"
OUTPUT_RED_HTML  = OUTPUT_DIR / "red_multicapa.html"

# Crear carpeta output si no existe
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── LLM ────────────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL    = "llama-3.3-70b-versatile"   # modelo gratuito en Groq
LLM_TEMP     = 0.0                          # determinístico: misma entrada = misma salida

# ── Umbrales ───────────────────────────────────────────────────────────────────
# Fragementos máximos que se envían al LLM por llamada (evita exceder contexto)
MAX_SEGMENTOS_POR_LLAMADA = 15

# Score mínimo del auditor para NO requerir revisión humana obligatoria
UMBRAL_CALIDAD_AUDITOR = 0.70

# Fuerza mínima de una prueba para considerarse "soporte real"
UMBRAL_FUERZA_PRUEBA = 0.40

# Umbral de betweenness para marcar un nodo como "punto único de falla"
UMBRAL_BETWEENNESS_FALLA = 0.25
