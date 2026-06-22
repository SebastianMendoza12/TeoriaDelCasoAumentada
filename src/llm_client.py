"""
Cliente LLM centralizado.

Orden de uso:
1. Groq, si existe GROQ_API_KEY.
2. Cerebras, si Groq falla por rate limit y existe CEREBRAS_API_KEY.
3. Cerebras directo, si no hay GROQ_API_KEY.

No hay llaves "gratis sin limite" garantizadas: cada proveedor puede aplicar
cuotas. Este cliente evita que un 429 de Groq rompa toda la corrida cuando
hay un proveedor de respaldo configurado por el usuario.
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

    if GROQ_API_KEY:
        return _crear_groq(temp)

    if CEREBRAS_API_KEY:
        return _crear_cerebras(temp)

    raise RuntimeError(
        "No hay API key configurada.\n"
        "Agrega GROQ_API_KEY o CEREBRAS_API_KEY en tu archivo .env\n"
        "  Groq:     https://console.groq.com\n"
        "  Cerebras: https://cloud.cerebras.ai"
    )


def invoke_llm(prompt, inputs: dict, temperature: float = None):
    """
    Ejecuta un prompt con fallback de proveedor.

    Retorna (respuesta, metadata), donde metadata incluye proveedor y modelo.
    """
    temp = temperature if temperature is not None else LLM_TEMP
    intentos = []

    if GROQ_API_KEY:
        intentos.append(("groq", LLM_MODEL, lambda: _crear_groq(temp)))
    if CEREBRAS_API_KEY:
        intentos.append(("cerebras", CEREBRAS_MODEL, lambda: _crear_cerebras(temp)))

    if not intentos:
        raise RuntimeError(
            "No hay API key configurada. Agrega GROQ_API_KEY o CEREBRAS_API_KEY "
            "en tu archivo .env"
        )

    ultimo_error = None
    for indice, (proveedor, modelo, crear_llm) in enumerate(intentos):
        try:
            if PAUSA_ENTRE_LLAMADAS:
                time.sleep(PAUSA_ENTRE_LLAMADAS if indice == 0 else 1)
            chain = prompt | crear_llm()
            respuesta = chain.invoke(inputs)
            return respuesta, {"proveedor": proveedor, "modelo": modelo}
        except Exception as exc:
            ultimo_error = exc
            hay_siguiente = indice + 1 < len(intentos)
            if proveedor == "groq" and hay_siguiente and _es_rate_limit(exc):
                print("  Rate limit en Groq; reintentando con Cerebras...")
                continue
            raise

    raise ultimo_error


def invoke_con_fallback(chain_groq, chain_cerebras, inputs: dict) -> object:
    """
    Compatibilidad con codigo anterior: intenta Groq y usa Cerebras si hay 429.
    """
    try:
        time.sleep(PAUSA_ENTRE_LLAMADAS)
        return chain_groq.invoke(inputs)
    except Exception as exc:
        if _es_rate_limit(exc) and CEREBRAS_API_KEY:
            print("  Rate limit en Groq; usando Cerebras como fallback...")
            time.sleep(5)
            return chain_cerebras.invoke(inputs)
        raise
