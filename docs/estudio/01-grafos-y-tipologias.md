# 1. Grafos de transacciones y tipologías

## El lavado se ve en la forma del flujo

El dinero lavado deja una **forma** en el flujo de transacciones: muchos depósitos pequeños
que caen en una sola cuenta, un monto que pasa rápido por una cadena, dinero que vuelve a su
origen, una cuenta que reparte a muchas. Esas formas se ven en un **grafo**: cada cuenta es un
nodo y cada transferencia es una arista dirigida con un monto y un tiempo.

El pipeline es: `transacciones -> grafo -> features por cuenta -> reglas + modelo -> alerta`.
Este documento cubre las dos primeras flechas (el grafo y las features); el modelo y la fusión
van en [02](02-reglas-modelo-reporte.md).

## Las tipologías (GAFI/FATF) y su firma medible

Cada tipología no es solo una idea: es una **firma** en las features, con un umbral concreto en
`typologies.py`. Esta es la tabla que conviene memorizar para la entrevista:

| Tipología | Idea | Regla (feature ≥ umbral) | Severidad |
|---|---|---|---|
| Estructuración | Muchos depósitos justo bajo el umbral a un recolector | `pct_in_under_threshold ≥ 0.6` **y** `in_count ≥ 5` | 0.9 |
| Fuente de estructuración (mula) | Envía muchos montos bajo umbral a pocos destinos | `pct_out_under_threshold ≥ 0.6` **y** `out_count ≥ 3` **y** `unique_out ≤ 2` | 0.7 |
| Layering | Monto que entra y sale casi igual, rápido | `passthrough_ratio ≥ 0.8` **y** `total_in > 10 000` | 0.8 |
| Round-tripping | El dinero vuelve a su origen (ciclo) | `in_cycle == 1` | 0.7 |
| Fan-out | Una cuenta reparte a muchas | `unique_out ≥ 10` **y** `unique_in ≤ 2` | 0.7 |
| Fan-in | Una cuenta recolecta de muchas y reenvía | `unique_in ≥ 8` **y** `unique_out ≤ 2` **y** `total_out > 0` | 0.6 |

> **Por qué esos umbrales.** `in_count ≥ 5` evita marcar a cualquiera con dos depósitos bajo el
> umbral; `unique_out ≤ 2` distingue una mula (reenvía a un recolector) de una nómina (reparte a
> muchos); `passthrough ≥ 0.8` exige que **casi todo** lo que entra salga (un comercio se queda el
> dinero, un eslabón de layering no). La severidad pondera cuán específica es la firma: la
> estructuración (0.9) es más delatora que un fan-in (0.6), que un comercio popular también exhibe.

## Las features por cuenta (con fórmulas)

En `features.py`, cada cuenta `v` se resume en 16 números. Los que mueven la detección:

* **`passthrough_ratio`** `= min(total_in, total_out) / max(total_in, total_out)` (0 si no hay
  flujo). Cercano a 1 ⇒ la cuenta es un **tubo**: casi todo lo que entra, sale. Es la firma de
  layering.
* **`pct_in_under_threshold`** `= ` fracción de depósitos entrantes con monto en `[0.8·T, T)`,
  donde `T` es el umbral de reporte (10 000). Alto ⇒ estructuración. Nótese que **excluye** montos
  por encima de `T`: estructurar es quedarse *justo debajo*.
* **`turnover_gap`** `= media(tiempos de salida) − media(tiempos de entrada)`. Pequeño o negativo
  ⇒ el dinero sale casi tan rápido como entra (layering veloz).
* **`unique_in` / `unique_out`**: número de contrapartes distintas. Separan fan-in (muchas
  fuentes) de fan-out (muchos destinos).
* **`pagerank`**, **`clustering`**, **`in_cycle`**: la posición en el grafo (abajo).

> **Concepto — PageRank.** El puntaje que usaba Google, sobre el grafo de dinero: la importancia
> de un nodo es la suma de las importancias de quienes le transfieren, repartidas por su grado de
> salida. Formalmente `PR(v) = (1−d)/N + d · Σ_{u→v} PR(u)/outdeg(u)`, con `d≈0.85`. Un recolector
> o un eslabón central acumulan PageRank porque reciben de nodos que a su vez reciben.

> **Concepto — coeficiente de clustering.** Qué tan "cerrado" es el vecindario de un nodo: de todos
> los pares de vecinos que *podrían* estar conectados entre sí, cuántos lo están. Una red de mulas
> coordinadas forma triángulos; un pagador aislado, no.

> **Concepto — ciclo.** Un camino que vuelve al punto de partida (round-tripping). Se detecta con
> `nx.simple_cycles` acotado a longitud ≤ 5 (los ciclos largos son caros de enumerar y raros en
> lavado). El fondo de pagos (pagadores → comercios) es **mayormente acíclico**, así que un ciclo
> *resalta*. Pero a propósito añadimos **bucles de reembolso** legítimos (A → B → A, un comercio que
> devuelve a un cliente): crean ciclos **benignos**. Por eso `in_cycle` es una señal **ambigua**, no
> una etiqueta — y ahí está la dificultad realista. (Ver [ADR-0003](../adr/0003-graph-features-and-acyclic-background.md).)

## Un ejemplo trabajado (números reales del grafo semilla 42)

Mira tres cuentas y cómo el sistema decide (umbral de alerta = 0.81):

| Cuenta | ¿Lavado? | Señales clave | Reglas disparadas | `rule_score` | `ml` | **fusión** | ¿Alerta? |
|---|---|---|---|---|---|---|---|
| `laund_collector` | **Sí** | `pct_in_under=1.00`, `in_count=34`, `unique_in=12` | estructuración (0.9) + fan-in (0.6) | 0.75 | 0.88 | **0.97** | ✅ sí |
| `layer_02` | **Sí** | `passthrough=0.97`, entra ≈ sale | layering (0.8) | 0.40 | 0.92 | **0.95** | ✅ sí |
| `acct_msb_00` | **No** (MSB legítimo) | `passthrough=0.90`, `pct_in_under=0.57` | layering (0.8) | 0.40 | **0.17** | **0.50** | ❌ no |

La fila del MSB es la lección completa en una línea. La **regla** de layering **sí** se dispara
(el MSB reenvía casi todo, como un eslabón). Pero el **modelo** aprendió que un MSB —muchas
entradas de clientes distintos, montos variados, patrón recurrente— **no** es lavado, y le da
`ml = 0.17`. La fusión noisy-OR `1 − (1 − 0.17)(1 − 0.40) = 0.50` queda **bajo** el umbral 0.81, así
que **no** se genera la alerta. Regla y modelo se complementan: la regla aporta explicabilidad, el
modelo aporta el juicio que evita el falso positivo. (El cómo de la fusión y del umbral, en [02](02-reglas-modelo-reporte.md).)

> **`rule_score`** `= min(1.0, Σ severidades / 2)`. Para el recolector: `(0.9 + 0.6)/2 = 0.75`.
> Dividir entre 2 hace que **dos** firmas fuertes basten para saturar la señal de reglas, sin que
> una sola lo haga.
