"""
explanation_verifier.py
Función pura de verificación de explicabilidad (ExplanationVerifier).
Basada en: Capítulo 20 de deep_agents_harness_v3.pdf

Se ejecuta DENTRO de explanation_builder_node (ver explanation_builder.py)
inmediatamente después de generar las explicaciones, en el mismo paso
del grafo — no como un nodo de LangGraph separado. Esto evita depender
de que el framework propague correctamente el estado entre dos nodos
distintos para un mismo dato.

Propósito: verificar que cada explicación generada por el
ExplanationBuilder referencia una fuente real del expediente (o un ID
real de la matriz HPN) y rechazar las que no tengan soporte verificable.
"""

import datetime


def _fuente_es_verificable(
    fuente_citada: str,
    segmentos: list[dict],
    matriz: list[dict],
) -> bool:
    """
    Verifica que la fuente citada exista de verdad, ya sea como:
    - un frag_id real de los segmentos del expediente,
    - una referencia a página ("página 4", "pág. 4"),
    - o un ID real de hecho/prueba/norma de la matriz HPN
      (el prompt del builder permite citar "P002" como fuente).
    """
    if not fuente_citada or fuente_citada in ("?", "", "N/A", "ninguna"):
        return False

    frag_ids = {s.get("frag_id", "") for s in segmentos}
    if fuente_citada in frag_ids:
        return True

    if fuente_citada.lower().startswith(("página", "pág")):
        return True

    return _referencia_existe_en_matriz(fuente_citada, matriz)


def _referencia_existe_en_matriz(referencia: str, matriz: list[dict]) -> bool:
    """Verifica que el HPN-ID, P-ID, H-ID o N-ID citado existe en la matriz."""
    if not referencia:
        return False

    ids_hpn = {f.get("id", "") for f in matriz}
    ids_hechos = {
        f.get("hecho", {}).get("id", "")
        for f in matriz
        if isinstance(f.get("hecho"), dict)
    }
    ids_pruebas = {p.get("id", "") for f in matriz for p in f.get("pruebas", [])}
    ids_normas = {n.get("id", "") for f in matriz for n in f.get("normas", [])}

    return (
        referencia in ids_hpn
        or referencia in ids_hechos
        or referencia in ids_pruebas
        or referencia in ids_normas
    )


def verificar_explicaciones(
    explicaciones: list[dict],
    segmentos: list[dict],
    matriz: list[dict],
) -> dict:
    """
    Verifica cada explicación del ExplanationBuilder.

    Por cada explicación verifica:
    1. La fuente_citada existe de verdad (frag_id real, página, o ID
       real de la matriz) — antes solo se revisaba que no viniera vacía.
    2. La referencia (HPN-ID, P-ID, H-ID, N-ID) existe en la matriz.
    3. La decisión y la razón no están vacías.

    Retorna el reporte de explicabilidad.
    """
    explicaciones_aprobadas = []
    explicaciones_rechazadas = []

    for exp in explicaciones:
        razon_rechazo = None
        fuente = exp.get("fuente_citada", "")
        referencia = exp.get("referencia", "")
        decision = exp.get("decision", "")
        razon = exp.get("razon", "")

        if not _fuente_es_verificable(fuente, segmentos, matriz):
            razon_rechazo = (
                f"Fuente citada '{fuente}' no se pudo verificar contra el "
                "expediente ni contra la Matriz HPN"
            )
        elif referencia and not _referencia_existe_en_matriz(referencia, matriz):
            if any(referencia.startswith(p) for p in ("HPN-", "H0", "P0", "N0")):
                razon_rechazo = (
                    f"Referencia '{referencia}' no existe en la Matriz HPN actual"
                )
        elif not decision or not razon:
            razon_rechazo = "Explicación incompleta — falta 'decision' o 'razon'"

        if razon_rechazo:
            explicaciones_rechazadas.append({
                **exp,
                "razon_rechazo": razon_rechazo,
                "estado_verificacion": "rechazada",
            })
        else:
            explicaciones_aprobadas.append({
                **exp,
                "estado_verificacion": "aprobada",
            })

    total = len(explicaciones)
    aprobadas = len(explicaciones_aprobadas)
    rechazadas = len(explicaciones_rechazadas)
    score_explicabilidad = round(aprobadas / max(total, 1), 3)

    return {
        "total_explicaciones":      total,
        "explicaciones_aprobadas":  aprobadas,
        "explicaciones_rechazadas": rechazadas,
        "score_explicabilidad":     score_explicabilidad,
        "detalle_aprobadas":        explicaciones_aprobadas,
        "detalle_rechazadas":       explicaciones_rechazadas,
        "timestamp":                datetime.datetime.now().isoformat(),
    }