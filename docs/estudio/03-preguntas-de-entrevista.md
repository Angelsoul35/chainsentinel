# 3. Preguntas de entrevista

## Nivel junior / media

**¿Qué hace ChainSentinel en una frase?**
Detecta lavado de dinero mirando las transacciones como un grafo, con tipologías GAFI y un
modelo de ML, y redacta un borrador de reporte que revisa un humano.

**¿Por qué un grafo?**
Porque el lavado deja una forma en el flujo (ciclos, embudos, cadenas) que solo se ve tratando
las cuentas y transferencias como nodos y aristas.

**¿Qué es la estructuración (pitufeo)?**
Partir el dinero en muchos depósitos pequeños justo bajo el umbral de reporte para no activar
alertas. Lo detectamos por la fracción de depósitos bajo el umbral hacia un recolector.

## Nivel media / senior

**¿Por qué combinas reglas y modelo?**
Las reglas son explicables pero frágiles; el modelo captura más pero es caja negra. Juntos:
alertas fuertes y explicables. Es la forma real de un sistema AML.

**¿Por qué el fondo de pagos es mayormente acíclico, y por qué igual añades ciclos benignos?**
Un grafo aleatorio está lleno de ciclos cortos y la señal de ciclo marcaría a todos; con un
fondo de pagos (pagadores → comercios) un ciclo *resalta*. Pero añadimos a propósito bucles de
reembolso legítimos (A → B → A), así que hay ciclos benignos: `in_cycle` queda como señal
**ambigua**, no como etiqueta. Es la dificultad realista — el detector no puede marcar todo
ciclo como lavado.

**¿Cómo evitas confundir un comercio legítimo con un recolector?**
Un comercio recibe de muchos, pero con montos variados y sin reenviar. El recolector recibe
montos **bajo el umbral** y **reenvía** un monto grande. La fracción bajo umbral y el flujo de
salida los separan.

**¿Por qué el LLM no decide?**
Porque presentar un SAR tiene peso legal y debe ser explicable y reproducible. El LLM solo
redacta; la detección viene de reglas y modelo, y un humano revisa.

## Nivel senior / diseño

**¿Qué le falta para producción?**
Escala (millones de cuentas, grafos enormes), manejo de mixers y exchanges, etiquetas reales
para entrenar, umbrales calibrados contra falsos positivos, y trazabilidad/auditoría de cada
alerta. Las métricas de aquí (precisión ~0.95, recall ~0.99 en grafos no vistos) **no son 1.0**
precisamente porque el dato tiene confundidores realistas; aun así, en datos reales serían más
bajas, porque un grafo generado sigue siendo más separable que una cadena real con millones de
cuentas.

**¿Cómo medirías el sistema en producción?**
Precisión (de las alertas, cuántas eran reales) y recall (de lo real, cuánto detecté), pero
sobre todo la **carga de falsos positivos** sobre los analistas, que es el costo real.

## Reto para ti

* Agrega detección de "mixing" (una cuenta que mezcla fondos de muchos y los redistribuye).
* Agrega características temporales (ráfagas de actividad en ventanas cortas).
* Cambia el random forest por un Graph Neural Network y compara precisión/recall.
