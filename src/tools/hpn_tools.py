"""
hpn_tools.py
Validación de filas HPN y cálculo de métricas de la matriz.
Sin LLM — lógica determinística pura.
"""

from src.config import UMBRAL_FUERZA_PRUEBA

# Columnas obligatorias según el enunciado del proyecto
CAMPOS_OBLIGATORIOS = [
    "id",
    "elemento_juridico",
    "hecho",
    "pruebas",
    "normas",
    "fuente_expediente",
    "estado",
    "riesgo",
    "accion_sugerida",
    "agente_responsable",
    "revision_humana",
]

ESTADOS_VALIDOS = {
    "completo", "parcial", "controvertido", "debil",
    "vacio_critico", "riesgo_adversarial", "bloqueado", "pendiente",
}

RIESGOS_VALIDOS = {"bajo", "medio", "alto", "critico"}


def validar_fila(fila: dict) -> dict:
    """
    Verifica que una fila HPN tenga todos los campos mínimos
    y que los valores estén dentro de los rangos esperados.
    Devuelve {"valida": bool, "errores": [str]}.
    """
    errores = []

    # Campos obligatorios presentes
    for campo in CAMPOS_OBLIGATORIOS:
        if campo not in fila or fila[campo] is None or fila[campo] == "":
            errores.append(f"Falta campo obligatorio: '{campo}'")

    # Estado válido
    estado = fila.get("estado", "")
    if estado and estado not in ESTADOS_VALIDOS:
        errores.append(f"Estado inválido: '{estado}'. Debe ser uno de {ESTADOS_VALIDOS}")

    # Riesgo válido
    riesgo = fila.get("riesgo", "")
    if riesgo and riesgo not in RIESGOS_VALIDOS:
        errores.append(f"Riesgo inválido: '{riesgo}'. Debe ser uno de {RIESGOS_VALIDOS}")

    # Hecho debe tener fuente
    hecho = fila.get("hecho", {})
    if isinstance(hecho, dict):
        if not hecho.get("frag_id") and not hecho.get("pagina"):
            errores.append("El hecho debe incluir 'frag_id' o 'pagina' como fuente")

    # Si estado es "completo" debe haber al menos una prueba con fuerza >= umbral
    if estado == "completo":
        pruebas = fila.get("pruebas", [])
        if not pruebas:
            errores.append("Estado 'completo' pero no hay pruebas registradas")
        else:
            fuerzas = [p.get("fuerza", 0) for p in pruebas
                       if p.get("relacion") == "soporta"]
            if not any(f >= UMBRAL_FUERZA_PRUEBA for f in fuerzas):
                errores.append(
                    f"Estado 'completo' pero ninguna prueba de soporte "
                    f"supera el umbral de fuerza ({UMBRAL_FUERZA_PRUEBA})"
                )

    return {"valida": len(errores) == 0, "errores": errores}


def calcular_metricas_hpn(matriz: list[dict]) -> dict:
    """
    Calcula todas las métricas derivadas de la matriz HPN
    definidas en la Tabla 3 del enunciado del proyecto.
    """
    total = len(matriz)
    if total == 0:
        return {"total_filas": 0, "advertencia": "Matriz vacía"}

    # Cobertura de elementos jurídicos
    # (fila con hecho + al menos una prueba + al menos una norma)
    completas_juridico = sum(
        1 for f in matriz
        if f.get("hecho") and f.get("pruebas") and f.get("normas")
    )

    # Cobertura probatoria
    con_prueba = sum(1 for f in matriz if f.get("pruebas"))

    # Cobertura normativa
    con_norma = sum(1 for f in matriz if f.get("normas"))

    # Vacíos críticos
    vacios_criticos = sum(
        1 for f in matriz if f.get("estado") == "vacio_critico"
    )

    # Índice de contradicción
    contradictorias = sum(
        1 for f in matriz
        if any(p.get("relacion") == "contradice" for p in f.get("pruebas", []))
    )

    # Debilidad argumentativa
    estados_debiles = {"debil", "parcial", "riesgo_adversarial"}
    debiles = sum(1 for f in matriz if f.get("estado") in estados_debiles)

    # Filas con riesgo alto o crítico
    alto_riesgo = sum(
        1 for f in matriz if f.get("riesgo") in {"alto", "critico"}
    )

    # Acciones pendientes (filas que requieren diligencia adicional)
    pendientes = sum(
        1 for f in matriz if f.get("revision_humana") == "sin_revisar"
    )

    # Trazabilidad
    con_fuente = sum(1 for f in matriz if f.get("fuente_expediente"))

    return {
        "total_filas":                   total,
        "cobertura_elementos_juridicos": round(completas_juridico / total, 3),
        "cobertura_probatoria":          round(con_prueba / total, 3),
        "cobertura_normativa":           round(con_norma / total, 3),
        "vacios_criticos":               vacios_criticos,
        "pct_vacios_criticos":           round(vacios_criticos / total, 3),
        "indice_contradiccion":          contradictorias,
        "pct_contradiccion":             round(contradictorias / total, 3),
        "filas_debiles":                 debiles,
        "pct_debilidad":                 round(debiles / total, 3),
        "filas_alto_riesgo":             alto_riesgo,
        "pct_alto_riesgo":               round(alto_riesgo / total, 3),
        "acciones_pendientes":           pendientes,
        "trazabilidad":                  round(con_fuente / total, 3),
    }
