---
name: legal-network
description: Construye y analiza la red compleja multicapa que conecta hechos, pruebas, normas, precedentes, argumentos, riesgos, tiempo, actores y pretensiones de un caso. Úsala cuando la tarea requiera transformar la Matriz HPN en un grafo tipado o calcular métricas estructurales (centralidad, fragilidad, puntos de falla).
---

# Legal Network (red compleja multicapa)

## Cuándo usar esta skill

- Al convertir filas HPN en nodos y aristas.
- Al calcular métricas de red (Cuadro 4 del enunciado del proyecto).
- Al decidir si una estructura merece llamarse "red compleja multicapa" o
  solo "grafo plano".

## Distinción obligatoria

Si el sistema solo guarda nodos y flechas, es un **grafo**. Para llamarlo
**red compleja multicapa** debe cumplir tres condiciones:

1. Existen capas heterogéneas y diferenciadas: hechos, pruebas, normas,
   precedentes, argumentos, riesgos, tiempo, actores, pretensiones/defensas.
2. Existen tipos de relación distintos: `soporta`, `contradice`, `activa`,
   `fundamenta`, `derrota`, `precede`, `distingue`, `riesgo`.
3. Se calculan métricas estructurales (no solo grado): centralidad de
   intermediación, puntos únicos de falla, fragilidad probatoria,
   robustez adversarial, cobertura de rutas jurídicas.

## Procedimiento

1. Por cada fila HPN: crear/actualizar nodo `hecho`, nodos `prueba` (con
   arista `soporta`/`contradice` hacia el hecho), nodos `norma` (con
   arista `activa` desde el hecho).
2. Si la fila referencia un precedente o línea jurisprudencial: crear nodo
   capa `precedentes` y arista `fundamenta` o `distingue` según el caso.
3. Si la fila resuelve en una conclusión jurídica explícita: crear nodo
   capa `argumentos` que conecte hecho + prueba + norma → conclusión, con
   arista `fundamenta`.
4. Si hay una excepción o defensa que anula una conclusión: arista
   `derrota` desde el nodo `riesgo`/excepción hacia el `argumento`.
5. Usar la cronología (`state["cronologia"]`) para crear nodos capa
   `tiempo` y aristas `precede` entre hechos consecutivos.
6. Crear nodos capa `pretensiones` por cada pretensión/defensa del caso y
   conectarlos a los argumentos que los sostienen.
7. Calcular métricas con NetworkX: grado, betweenness, puntos únicos de
   falla, fragilidad por prueba, redundancia, y — si las capas anteriores
   existen — cobertura de rutas jurídicas y proximidad a la pretensión.

## Reglas duras

- Cada arista debe tener `tipo`, `peso`, `capa_origen`, `capa_destino` y,
  si aplica, `fila_hpn` de origen para trazabilidad.
- No crear nodos sin al menos una fuente (frag_id, fila HPN o ID de
  prueba/norma) que los respalde.