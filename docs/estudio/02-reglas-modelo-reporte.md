# 2. Reglas + modelo + reporte

## Por qué dos mitades

Un sistema AML serio tiene **dos mitades**:

* **Reglas (explicables):** en `typologies.py`. Cada regla reconoce una tipología GAFI y dice
  **por qué** (lenguaje que un analista entiende). Son fuertes pero frágiles: los lavadores
  cambian de comportamiento para esquivar reglas conocidas.
* **Modelo (aprendido):** en `model.py`, un random forest entrenado con las features de
  cuentas sospechosas y normales conocidas. Captura combinaciones que las reglas no ven, pero
  no se explica solo.

El **puntaje de alerta** mezcla las dos (`scoring.py`): cada alerta lleva las tipologías que
disparó (explicable) más el puntaje del modelo (aprendido). (Ver
[ADR-0002](../adr/0002-rules-plus-model.md).)

> **La lección.** Reglas solas = frágiles. Modelo solo = caja negra inservible para un
> analista. Juntos = fuertes y explicables. Esa es la forma real de un sistema AML.

## El reto de las mulas

Las mulas (cuentas que envían montos pequeños al recolector) parecen normales una por una. Por
eso agregamos una regla de **fuente de estructuración** (envía muchos montos bajo el umbral a
pocos destinos). Con ella, el recall sube: el sistema detecta también a las mulas, no solo al
recolector.

## El reporte (SAR) y el humano

Para las alertas principales, el sistema **redacta** un borrador de Reporte de Actividad
Sospechosa (SAR): con plantilla o con el LLM (cascada de proveedores). Pero **no lo presenta**:
cada borrador termina con que un analista humano debe revisarlo. El LLM solo escribe la prosa;
la detección y el puntaje vienen de las reglas y el modelo. (Ver
[ADR-0004](../adr/0004-human-in-the-loop-reports.md).)

> **Por qué.** Presentar un SAR tiene peso legal. El sistema prepara el trabajo; la decisión es
> de una persona.
