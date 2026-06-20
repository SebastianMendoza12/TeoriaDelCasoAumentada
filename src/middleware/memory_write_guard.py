"""
memory_write_guard.py
Valida qué puede escribirse en el estado antes de persistirlo.
Bloquea: datos sensibles, instrucciones de documentos no confiables,
conclusiones no verificadas por el auditor.
Se llama desde guardar_artefactos() en graph.py antes de escribir a disco.
"""

import re
import datetime

# Patrones que NO deben persistirse en artefactos finales
PATRONES_SENSIBLES = [
    r"(?i)(contraseña|password|token|secret|api[_\s]?key|Bearer\s+\w+)",
    r"\b\d{10,}\b",              # números largos tipo cédula, cuenta bancaria
    r"(?i)(ignore.*instructions|forget.*previous|act as|jailbreak)",
]


def _contiene_patron_sensible(texto: str) -> tuple[bool, str]:
    for patron in PATRONES_SENSIBLES:
        if re.search(patron, texto):
            return True, patron
    return False, ""


def verificar_escritura(estado: dict) -> dict:
    """
    Recorre los artefactos del estado y detecta contenido que no
    debería persistirse en disco.
    Retorna reporte: {"aprobado": bool, "alertas": [...]}
    """
    alertas = []

    # Verificar filas HPN
    for fila in estado.get("matriz_hpn", []):
        for campo in ["elemento_juridico", "accion_sugerida"]:
            texto = str(fila.get(campo, ""))
            encontrado, patron = _contiene_patron_sensible(texto)
            if encontrado:
                alertas.append({
                    "tipo": "dato_sensible",
                    "fila": fila.get("id", "?"),
                    "campo": campo,
                    "patron": patron,
                })

        # Conclusiones sin auditor no deben marcarse como aprobadas
        if (fila.get("revision_humana") == "aprobado" and
                estado.get("reporte_auditoria", {}).get("score_calidad", 0) < 0.5):
            alertas.append({
                "tipo": "conclusion_no_verificada",
                "fila": fila.get("id", "?"),
                "detalle": "Fila marcada 'aprobado' pero score del auditor < 0.5",
            })

    aprobado = len(alertas) == 0

    if aprobado:
        print("[MemoryWriteGuard]  ✓  Sin contenido sensible detectado.")
    else:
        print(f"[MemoryWriteGuard]  ⚠️  {len(alertas)} alerta(s) detectada(s).")
        for a in alertas:
            print(f"    - {a}")

    return {
        "aprobado": aprobado,
        "alertas": alertas,
        "timestamp": datetime.datetime.now().isoformat(),
    }