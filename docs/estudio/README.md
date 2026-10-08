# Guía de estudio — ChainSentinel

Esta guía está en español y explica el proyecto para que lo estudies y lo sustentes en una
entrevista. El código y la documentación técnica están en inglés; aquí va el *por qué*.

## Orden de lectura

1. [Grafos de transacciones y tipologías](01-grafos-y-tipologias.md) — cómo se ve el lavado
   en la forma del flujo de dinero.
2. [Reglas + modelo + reporte](02-reglas-modelo-reporte.md) — por qué se combinan reglas
   explicables y un modelo, y cómo se arma el reporte.
3. [Preguntas de entrevista](03-preguntas-de-entrevista.md) — preguntas típicas con
   respuestas.

## Cómo correrlo mientras estudias

```bash
make install
make demo     # entrena, analiza un grafo, muestra alertas y un reporte SAR
make test     # 12 pruebas
```

El concepto central: **detectar lavado de dinero mirando las transacciones como un grafo**,
combinando tipologías GAFI (explicables), un modelo de ML (aprendido) y un reporte escrito por
un LLM, con un humano que revisa.
