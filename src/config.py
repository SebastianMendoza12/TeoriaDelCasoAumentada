# src/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Rutas ──────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent.parent
INPUT_DIR   = BASE_DIR / "data" / "input"
OUTPUT_DIR  = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

PDF_PATH    = INPUT_DIR / "expediente.pdf"

# Salidas
HPN_PATH        = OUTPUT_DIR / "matriz_hpn.json"
GRAFO_PATH      = OUTPUT_DIR / "grafo.json"
METRICAS_PATH   = OUTPUT_DIR / "metricas.json"
ESCENARIOS_PATH = OUTPUT_DIR / "escenarios.json"
TRAZAS_PATH     = OUTPUT_DIR / "trazas.jsonl"
ESTADO_PATH     = OUTPUT_DIR / "estado_final.json"

# ── LLM ────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL    = "llama-3.3-70b-versatile"   # gratis en Groq
TEMPERATURE  = 0

# ── Umbrales ───────────────────────────────────────────────────────
MAX_SEGMENTOS_POR_LLAMADA = 12   # fragmentos de PDF por llamada al LLM
UMBRAL_FRAGILIDAD         = 0.3  # betweenness > esto = punto único de falla
UMBRAL_CALIDAD_AUDITORIA  = 0.65 # score < esto → revisión humana obligatoria