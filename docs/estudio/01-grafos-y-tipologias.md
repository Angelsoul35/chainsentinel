# 1. Grafos de transacciones y tipologías

## El lavado se ve en la forma del flujo

El dinero lavado deja una **forma** en el flujo de transacciones: muchos depósitos pequeños
que caen en una sola cuenta, un monto que pasa rápido por una cadena, dinero que vuelve a su
origen, una cuenta que reparte a muchas. Esas formas se ven en un **grafo**: cada cuenta es un
nodo y cada transferencia es una arista dirigida.

## Las tipologías (GAFI/FATF)

| Tipología | Cómo se ve |
|---|---|
| Estructuración (pitufeo) | Muchos depósitos justo bajo el umbral hacia un recolector |
| Fuente de estructuración (mula) | Una cuenta que envía muchos montos bajo el umbral a un solo destino |
| Layering (estratificación) | Un monto movido rápido por una cadena (entra ≈ sale, rápido) |
| Round-tripping | Dinero que vuelve a su origen (un ciclo A → B → C → A) |
| Fan-out | Una cuenta que reparte a muchas |
| Fan-in | Una cuenta que recolecta de muchas y reenvía |

## Las características (features) por cuenta

En `features.py`, para cada cuenta calculamos: cuánto entra y sale, la **razón de paso**
(entra ≈ sale), cuántas contrapartes únicas, qué fracción de depósitos cae **justo bajo el
umbral**, qué tan rápido sale el dinero, PageRank, clustering, y si la cuenta está en un
**ciclo** corto.

> **Concepto — PageRank.** El mismo algoritmo que usaba Google para rankear páginas, aplicado
> al grafo de dinero: mide la "importancia" de un nodo según quién le transfiere.

> **Concepto — ciclo.** Un camino que vuelve al punto de partida. En lavado, un ciclo es
> round-tripping. El fondo de pagos (pagadores → comercios) es **mayormente acíclico**, así
> que un ciclo *resalta*. Pero a propósito añadimos **bucles de reembolso** legítimos
> (A → B → A, un comercio que devuelve dinero a un cliente): crean ciclos **benignos**. Por
> eso `in_cycle` es una señal **ambigua**, no una etiqueta — y ahí está la dificultad
> realista: el detector no puede marcar todo ciclo como lavado. (Ver
> [ADR-0003](../adr/0003-graph-features-and-acyclic-background.md).)
