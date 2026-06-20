---
name: scenario-simulation
description: Ejecuta simulaciones de perturbación sobre la Matriz HPN y la red multicapa (exclusión de prueba, excepción probada, testigo contradictorio, precedente distinguido, etc.) y recalcula métricas antes/después. Úsala cuando la tarea requiera laboratorio estratégico, no predicción de fallo.
---

# Scenario Simulation

## Cuándo usar esta skill

- Al ejecutar cualquiera de los escenarios S1–S8 del Cuadro 5 del
  enunciado del proyecto.
- Al construir el informe comparativo antes/después que ve el abogado.

## Flujo mínimo obligatorio (Sección 7.1 del enunciado)

Para **cada** escenario, sin excepción:

1. Declarar el supuesto explícito (qué se perturba y por qué).
2. **Modificar una copia de la matriz HPN y de la red** bajo ese supuesto
   (no solo describir el efecto en texto — ejecutar la perturbación).
3. **Recalcular las métricas** (`calcular_metricas_hpn`, métricas de red)
   sobre la versión perturbada.
4. Comparar métricas antes/después y listar hechos afectados, filas HPN
   impactadas y rutas debilitadas.
5. Generar una acción sugerida concreta y declarar incertidumbre.

## Error frecuente a evitar

No basta con que el LLM "opine" sobre el impacto de un escenario. Si el
paso 2 (perturbación real de la matriz/red) y el paso 3 (recálculo de
métricas) no se ejecutan en código, el escenario no cumple el flujo
mínimo exigido — es una narración, no una simulación.

## Escenarios mínimos exigidos (E7: al menos 4)

| ID | Perturbación | Recalcular con |
|----|---------------|-----------------|
| S1 | Eliminar la prueba de mayor fuerza | `calcular_metricas_hpn` sobre matriz sin esa prueba |
| S2 | Activar excepción (prescripción/caducidad/fuerza mayor) | Degradar a `bloqueado`/`riesgo_adversarial` las filas que dependen del elemento prescrito; recalcular |
| S3 | Agregar prueba contradictoria a un hecho principal | Cambiar estado de la fila afectada a `controvertido`/`debil`; recalcular |
| S4 | Debilitar el soporte jurisprudencial principal | Reducir `fuerza` o remover el nodo `precedente`; recalcular cobertura/dependencia jurisprudencial |

## Reglas duras

- Nunca predecir el resultado del fallo. Siempre "incertidumbre" +
  "revisión humana requerida" = true.
- Las métricas "antes" deben ser las reales del estado actual, no
  inventadas.