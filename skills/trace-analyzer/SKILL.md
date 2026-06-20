---
name: trace-analyzer
description: Analiza las trazas acumuladas (trazas.jsonl) de la ejecución multiagente para detectar loops, agentes que fallan repetidamente, baja trazabilidad o cuellos de botella, y proponer mejoras concretas al harness. Úsala al revisar por qué una ejecución dio resultados pobres o al preparar el informe final.
---

# Trace Analyzer Skill

Basada en el Capítulo 8.6 / 17.12 de deep_agents_harness_v3.pdf
("Trace Analyzer Skill: skill para analizar trazas de ejecuciones y
proponer mejoras al harness").

## Cuándo usar esta skill

- Cuando `loop_detection.py` marcó `loop_detectado=true` y hay que
  diagnosticar la causa raíz.
- Cuando el score del auditor es bajo y hay que ubicar en qué agente se
  originó el problema.
- Al preparar la sección de "limitaciones y errores" del informe final
  (E9).

## Procedimiento

1. Cargar `output/trazas.jsonl` y agrupar por `agente`.
2. Por cada agente, contar: número de ejecuciones, errores reportados,
   y si el LLM falló al parsear JSON (`json.JSONDecodeError`).
3. Cruzar con `output/checklist.json`: si `aprobado=false`, ubicar qué
   `items_fallidos` corresponden a qué agente.
4. Cruzar con `output/loop_detection.json`: si hay loop, identificar el
   `agente_problema` y revisar sus últimas 2-3 trazas para ver si la
   salida es idéntica (señal de prompt mal condicionado o temperatura
   inadecuada).
5. Producir un resumen de causa raíz y una recomendación de harness:
   ¿cambiar el prompt?, ¿bajar `MAX_SEGMENTOS_POR_LLAMADA`?, ¿agregar un
   paso de validación determinística antes del LLM?

## Señales típicas a buscar

- Mismo agente con `errores` no vacíos en más de una ejecución seguida.
- `score_calidad` del auditor estable y bajo en varias corridas (indica
  problema estructural, no ruido del LLM).
- Filas HPN con `errores_validacion` repetidos en el mismo campo.

## Salida esperada

Un breve reporte (3-5 puntos) con: agente(s) problemático(s), tipo de
falla, evidencia (cita de la traza) y recomendación de ajuste al harness.