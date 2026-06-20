---
name: hnp-matrix
description: Construye, valida y corrige filas de la Matriz Hecho-Prueba-Norma (HPN) para expedientes jurídicos. Úsala cuando la tarea requiera analizar teoría del caso, vincular hechos con pruebas y normas, o detectar vacíos probatorios/normativos.
---

# HNP Matrix

Esta skill encapsula el procedimiento del proyecto "Teoría del Caso Aumentada"
(Ciencia de Datos 2026-1, Universidad de Pamplona) para construir la Matriz
Hecho-Prueba-Norma (HPN). En este sistema se usa preferentemente la sigla
**HPN**, no HNP, por consistencia con el enunciado del proyecto.

## Cuándo usar esta skill

- Cuando se reciben hechos, pruebas y normas extraídos del expediente y hay
  que organizarlos en filas jurídico-probatorias.
- Cuando hay que decidir el estado epistémico de una afirmación (completo,
  parcial, controvertido, débil, vacío crítico, riesgo adversarial,
  bloqueado, pendiente).
- Cuando hay que auditar una matriz HPN ya construida.

## Procedimiento

1. **Listar elementos jurídicos.** Cada requisito, pretensión, defensa o
   excepción relevante del caso es candidato a una fila.
2. **Asociar el hecho.** Cada fila debe tener un hecho con `frag_id` y
   `pagina` de origen. Si no hay fuente, la fila no puede declararse
   "completo".
3. **Asociar prueba(s) explícitas.** Marcar la relación (`soporta` o
   `contradice`) y la fuerza (0.0–1.0). Nunca inventar pruebas que no
   aparezcan en el expediente.
4. **Asociar norma(s).** Marcar si la norma viene del `expediente` o es
   `inferida`. Ser conservador: ante la duda, vacío normativo.
5. **Marcar inferencias y vacíos.** Si no hay prueba o norma real, el
   estado debe degradarse a `vacio_critico`, nunca a `completo`.
6. **Calcular riesgo.** bajo/medio/alto/crítico, justificado por
   contradicciones o ausencia de soporte.
7. **Ejecutar el validador determinístico** (`src/tools/hpn_tools.py:
   validar_fila`) antes de entregar. Una fila con estado `completo` sin
   ninguna prueba de soporte con fuerza ≥ `UMBRAL_FUERZA_PRUEBA` debe ser
   rechazada por el validador, no por el LLM.

## Reglas duras

- Nunca asignar estado `completo` sin prueba real de soporte.
- Nunca inventar normas, artículos o pruebas.
- La columna `contradicciones` es obligatoria (lista vacía si no aplica).
- `revision_humana` siempre inicia en `sin_revisar`.

## Salida esperada

JSON con la estructura definida en la Sección 9.2 del enunciado del
proyecto (ver `src/agents/hpn_builder.py` para el schema exacto).