"""
Cliente LLM centralizado.

Orden de uso:
1. Cerebras (gratuito, límites más altos), si existe CEREBRAS_API_KEY.
2. Groq (fallback), si Cerebras falla y existe GROQ_API_KEY.
3. Groq directo, si no hay CEREBRAS_API_KEY.

No hay llaves "gratis sin limite" garantizadas: cada proveedor puede aplicar
cuotas. Cerebras es el principal por tener límites más altos; Groq actúa
como respaldo.
"""

import time

from src.config import (
    CEREBRAS_API_KEY,
    CEREBRAS_BASE_URL,
    CEREBRAS_MODEL,
    GROQ_API_KEY,
    LLM_MODEL,
    LLM_TEMP,
    PAUSA_ENTRE_LLAMADAS,
)


def _crear_groq(temperature: float):
    from langchain_groq import ChatGroq

    return ChatGroq(api_key=GROQ_API_KEY, model=LLM_MODEL, temperature=temperature)


def _crear_cerebras(temperature: float):
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise RuntimeError(
            "CEREBRAS_API_KEY esta configurada, pero falta instalar "
            "langchain-openai. Ejecuta: pip install -r requirements.txt"
        ) from exc

    return ChatOpenAI(
        api_key=CEREBRAS_API_KEY,
        base_url=CEREBRAS_BASE_URL,
        model=CEREBRAS_MODEL,
        temperature=temperature,
    )


def _es_rate_limit(error: Exception) -> bool:
    msg = str(error).lower()
    claves = ("rate limit", "429", "quota", "tokens per minute", "tpm")
    return any(clave in msg for clave in claves)


def get_llm(temperature: float = None):
    """Devuelve el primer LLM disponible segun las llaves configuradas."""
    temp = temperature if temperature is not None else LLM_TEMP

    if CEREBRAS_API_KEY:
        return _crear_cerebras(temp)

    if GROQ_API_KEY:
        return _crear_groq(temp)

    raise RuntimeError(
        "No hay API key configurada.\n"
        "Agrega CEREBRAS_API_KEY o GROQ_API_KEY en tu archivo .env\n"
        "  Cerebras: https://cloud.cerebras.ai\n"
        "  Groq:     https://console.groq.com"
    )


def invoke_llm(prompt, inputs: dict, temperature: float = None):
    """
    Ejecuta un prompt con fallback de proveedor.

    Retorna (respuesta, metadata), donde metadata incluye proveedor y modelo.
    """
    temp = temperature if temperature is not None else LLM_TEMP
    intentos = []

    if CEREBRAS_API_KEY:
        intentos.append(("cerebras", CEREBRAS_MODEL, lambda: _crear_cerebras(temp)))
    if GROQ_API_KEY:
        intentos.append(("groq", LLM_MODEL, lambda: _crear_groq(temp)))

    if not intentos:
        raise RuntimeError(
            "No hay API key configurada. Agrega GROQ_API_KEY o CEREBRAS_API_KEY "
            "en tu archivo .env"
        )

    ultimo_error = None
    for indice, (proveedor, modelo, crear_llm) in enumerate(intentos):
        reintentos_locales = 2 if proveedor == "cerebras" else 1
        for reintento in range(reintentos_locales):
            try:
                espera = (PAUSA_ENTRE_LLAMADAS if indice == 0 else 1) * (1 + reintento)
                if PAUSA_ENTRE_LLAMADAS:
                    time.sleep(espera)
                chain = prompt | crear_llm()
                respuesta = chain.invoke(inputs)
                return respuesta, {"proveedor": proveedor, "modelo": modelo}
            except Exception as exc:
                ultimo_error = exc
                es_rate_limit = _es_rate_limit(exc)
                # Cerebras con rate limit → reintentar
                if proveedor == "cerebras" and es_rate_limit and reintento < 2:
                    print(f"  Cerebras ocupado; reintento {reintento + 1}/3...")
                    continue
                # Cerebras falló (cualquier error) → pasar a Groq
                if proveedor == "cerebras" and indice + 1 < len(intentos):
                    print("  Cerebras falló; usando Groq como respaldo...")
                    break
                # Groq falló → no hay más respaldo
                raise
        else:
            continue
        break

    raise ultimo_error


def invoke_con_fallback(chain_cerebras, chain_groq, inputs: dict) -> object:
    """
    Compatibilidad con codigo anterior: intenta Cerebras y usa Groq si falla.
    """
    try:
        time.sleep(PAUSA_ENTRE_LLAMADAS)
        return chain_cerebras.invoke(inputs)
    except Exception as exc:
        if _es_rate_limit(exc) and GROQ_API_KEY:
            print("  Cerebras falló; usando Groq como respaldo...")
            time.sleep(5)
            return chain_groq.invoke(inputs)
        raise
