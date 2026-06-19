# src/tools/hpn_tools.py


CAMPOS_OBLIGATORIOS = [
    "id", "elemento_juridico", "hecho",
    "pruebas", "normas", "fuente_expediente",
    "estado", "riesgo", "accion_sugerida",
]

ESTADOS_VALIDOS = {
    "completo", "parcial", "controvertido",
    "debil", "vacio_critico", "bloqueado", "pendiente",
}

RIESGOS_VALIDOS = {"bajo", "medio", "alto", "critico"}


def validar_fila(fila: dict) -> dict:
    """
    Verifica que una fila HPN tenga los campos mínimos y valores coherentes.
    Devuelve {"valida": bool, "errores": [str]}.
    """
    errores = []

    for campo in CAMPOS_OBLIGATORIOS:
        if not fila.get(campo):
            errores.append(f"Falta campo obligatorio: '{campo}'")

    if fila.get("estado") and fila["estado"] not in ESTADOS_VALIDOS:
        errores.append(f"Estado inválido: '{fila['estado']}'")

    if fila.get("riesgo") and fila["riesgo"] not in RIESGOS_VALIDOS:
        errores.append(f"Riesgo inválido: '{fila['riesgo']}'")

    # Fila "completo" sin pruebas reales → incoherente
    if fila.get("estado") == "completo" and not fila.get("pruebas"):
        errores.append("Estado 'completo' pero sin pruebas asociadas")

    return {"valida": len(errores) == 0, "errores": errores}


def calcular_metricas_hpn(matriz: list[dict]) -> dict:
    """
    Calcula las métricas de la sección 5.4 del enunciado.
    No usa LLM — es aritmética pura sobre la matriz.
    """
    total = len(matriz)
    if total == 0:
        return {"total_filas": 0, "advertencia": "Matriz vacía"}

    completas        = sum(1 for f in matriz if f.get("estado") == "completo")
    con_prueba       = sum(1 for f in matriz if f.get("pruebas"))
    con_norma        = sum(1 for f in matriz if f.get("normas"))
    vacios           = sum(1 for f in matriz if f.get("estado") == "vacio_critico")
    contradictorias  = sum(1 for f in matriz if f.get("contradicciones"))
    debiles          = sum(1 for f in matriz if f.get("estado") in ("debil", "parcial"))
    riesgo_alto      = sum(1 for f in matriz if f.get("riesgo") in ("alto", "critico"))
    pendientes       = sum(1 for f in matriz if f.get("revision_humana") == "sin_revisar")

    return {
        "total_filas":              total,
        "cobertura_probatoria":     round(con_prueba / total, 3),
        "cobertura_normativa":      round(con_norma / total, 3),
        "pct_completas":            round(completas / total, 3),
        "vacios_criticos":          vacios,
        "filas_contradictorias":    contradictorias,
        "debilidad_argumentativa":  debiles,
        "riesgo_adversarial_alto":  riesgo_alto,
        "acciones_pendientes":      pendientes,
        "indice_contradiccion":     round(contradictorias / total, 3),
    }