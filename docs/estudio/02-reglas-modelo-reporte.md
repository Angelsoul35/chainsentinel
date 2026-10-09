# 2. Reglas + modelo + reporte

## Por qué dos mitades

Un sistema AML serio tiene **dos mitades**:

* **Reglas (explicables):** en `typologies.py`. Cada regla reconoce una tipología GAFI y dice
  **por qué** (lenguaje que un analista entiende). Son fuertes pero frágiles: los lavadores
  cambian de comportamiento para esquivar reglas conocidas.
* **Modelo (aprendido):** en `model.py`, un random forest entrenado con las features de
  cuentas sospechosas y normales conocidas. Captura combinaciones que las reglas no ven, pero
  no se explica solo.

El **puntaje de alerta** combina las dos (`scoring.py`): cada alerta lleva las tipologías que
disparó (explicable) más el puntaje del modelo (aprendido). (Ver
[ADR-0002](../adr/0002-rules-plus-model.md).)

> **La lección.** Reglas solas = frágiles. Modelo solo = caja negra inservible para un
> analista. Juntos = fuertes y explicables. Esa es la forma real de un sistema AML.

## Cómo se combinan: noisy-OR, no promedio

Esto es un detalle de diseño que vale una pregunta de entrevista. ¿Cómo mezclas el puntaje del
modelo (`ml`, de 0 a 1) con el de las reglas (`rule`, de 0 a 1)?

* **Promedio ponderado (lo intuitivo, pero está mal aquí):** `0.5*ml + 0.5*rule`. Problema: si
  el modelo está **seguro** (`ml = 0.9`) pero **ninguna regla disparó** (`rule = 0.0`), el
  promedio da `0.45` y la cuenta **cae bajo el umbral**. Es decir: el promedio **diluye** una
  señal fuerte y el sistema **deja pasar lavado real** solo porque la capa explicable no coincidió.
  Eso no es prudencia, es perder poder de detección. En nuestras pruebas, volver al promedio
  hunde el recall a **0.17** (y hay un test que lo atrapa).
* **Noisy-OR (lo correcto):** `combinado = 1 - (1 - ml) * (1 - rule)`. Se lee como "la cuenta es
  sospechosa si **el modelo _o_ una regla** lo dicen". El resultado nunca es menor que el máximo
  de los dos, así que ninguna fuente puede **vetar** a la otra. El modelo aporta recall en los
  casos sutiles; las reglas aportan explicabilidad y atrapan las estructuras de manual.

> **La idea clave.** Dos fuentes de evidencia *independientes* que apuntan al mismo riesgo se
> **suman** (como probabilidades de que *al menos una* tenga razón), no se promedian. Promediar
> trata a una fuente silenciosa como si fuera evidencia *en contra*, y no lo es.

## Por qué los puntajes no son 1.0 (y por qué eso es bueno)

Un detector que reporta precisión y recall de **1.0** no es una buena noticia: casi siempre
significa que el dato es un juguete trivialmente separable (overfitting al escenario). Por eso el
grafo de `generate.py` incluye, a propósito, **cuentas legítimas que *parecen* sospechosas** (los
*confundidores*), con etiqueta 0:

| Confundidor | Por qué confunde | A qué regla se parece |
|---|---|---|
| Intermediario de pagos / escrow | Recibe y **reenvía** casi todo (pass-through alto) | Layering |
| Bucle de reembolso (A → B → A) | Crea un **ciclo** benigno | Round-tripping |
| Nómina | **Reparte** a muchos empleados | Fan-out |
| Comercio popular | **Recolecta** de muchos pagadores | Fan-in |
| Proveedor bajo umbral | Factura repetido **justo bajo** el umbral | Estructuración |
| **Negocio de servicios monetarios (MSB)** | Recibe bajo umbral **y** reenvía rápido | Estructuración **+** Layering |

Los MSB son los más difíciles: disparan **dos** firmas a la vez, igual que un recolector. Un
sistema AML real genera falsos positivos con MSB; el nuestro también, y por eso el falso positivo
que queda es casi siempre un MSB. Eso es lo esperado: el error del modelo cae donde el problema es de
verdad ambiguo, no al azar.

## Medir sin trampa (fuga de datos)

Aquí cada "ejemplo" no es una fila, es un **grafo entero**: features como PageRank, clustering y
pertenencia a un ciclo se calculan sobre **todo** el grafo, así que las features de un nodo dependen
de sus vecinos. Si partieras filas al azar en train/test, los nodos de test tendrían features
*moldeadas* por los de train → **fuga**. La única señal confiable de generalización es el
desempeño en **grafos que el modelo nunca vio**. Por eso `evaluate.py` hace:

1. **Entrena** en un grafo (semilla 42).
2. **Elige el umbral** en **cuatro** grafos de **validación** (semillas 123, 321, 456, 654), con la
   regla "máxima precisión mientras el recall se mantenga ≥ 0.98 en el *peor* grafo" — en AML, no
   dejar pasar lavado es la prioridad.
3. **Reporta** en **cinco** grafos de **prueba** con semillas nuevas (777, 888, 999, 1234, 2024),
   que **nunca** se tocan para ajustar nada.

La métrica que importa es la **brecha de generalización** = (F1 en train) − (F1 medio en prueba).
Aquí es ≈ **0** (incluso levemente negativa): el detector **generaliza**, no memorizó un grafo.
Corre `python -m chainsentinel.evaluate` y lo ves tú mismo (precisión ~0.95, recall ~0.99 en grafos
no vistos).

> **Para la entrevista.** "¿Cómo sabes que no estás sobreajustando?" → "No me fío de un split por
> filas porque las features son de grafo y hay fuga; entreno en un grafo, elijo el umbral en otros
> de validación, y mido en grafos de prueba con semillas nuevas. La brecha train→test es casi cero,
> y el recall se sostiene. Un 1.0 me haría *desconfiar*, no celebrar."

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
