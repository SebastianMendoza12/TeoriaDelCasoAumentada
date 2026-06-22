"""
config.py
Configuración central del sistema: modelo LLM, rutas y umbrales.

Estrategia de LLM (gratuitos, sin tarjeta):
  1. Groq  — llama-3.3-70b-versatile  → rápido pero con límite de TPM
  2. Cerebras — llama-3.3-70b          → fallback, sin límite de TPM
  Los dos usan la misma interfaz OpenAI-compatible vía langchain-groq / openai.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Rutas ──────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
DATA_DIR   = BASE_DIR / "data" / "input"
OUTPUT_DIR = BASE_DIR / "output"

PDF_PATH = DATA_DIR / "expediente.pdf"

OUTPUT_HPN        = OUTPUT_DIR / "matriz_hpn.json"
OUTPUT_GRAFO      = OUTPUT_DIR / "grafo.json"
OUTPUT_METRICAS   = OUTPUT_DIR / "metricas.json"
OUTPUT_ESCENARIOS = OUTPUT_DIR / "escenarios.json"
OUTPUT_TRAZAS     = OUTPUT_DIR / "trazas.jsonl"
OUTPUT_RED_HTML   = OUTPUT_DIR / "red_multicapa.html"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── LLM principal: Groq (gratuito) ────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL    = "llama-3.3-70b-versatile"
LLM_TEMP     = 0.0

# ── LLM fallback: Cerebras (gratuito, sin límite de TPM restrictivo) ──────────
# Obtén tu key gratis en: https://cloud.cerebras.ai → API Keys
# Usa la misma interfaz de OpenAI via langchain-openai
CEREBRAS_API_KEY  = os.getenv("CEREBRAS_API_KEY", "")
CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"
CEREBRAS_MODEL    = "llama-3.3-70b"

# ── Umbrales ───────────────────────────────────────────────────────────────────
MAX_SEGMENTOS_POR_LLAMADA = 15
UMBRAL_CALIDAD_AUDITOR    = 0.70
UMBRAL_FUERZA_PRUEBA      = 0.40
UMBRAL_BETWEENNESS_FALLA  = 0.25

# ── Pausa entre llamadas al LLM (segundos) ────────────────────────────────────
# Reduce el riesgo de rate limit en Groq sin necesitar fallback
PAUSA_ENTRE_LLAMADAS = 3