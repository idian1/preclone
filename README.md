# Detector Preclone

Este repositorio contiene el detector local del proyecto. El detector recibe texto Markdown, lo divide en fragmentos que conservan sus líneas, consulta un modelo binario ya entrenado y emite una clasificación con el fragmento de mayor puntaje cuando corresponde.

El [material del profesor](datos/profesor/) contiene 1.200 textos de 50 escenarios y su registro de procedencia. Las [fuentes adicionales](datos/adicionales/) reúnen los registros de CloneGuard, ClawHub, MaliciousSkillBench y los README de GitHub identificados para ampliar el corpus. Las copias locales de los archivos externos se guardan en `datos/adicionales/descargas/`.

El [catálogo maestro](datos/catalogo.csv) reúne 3.191 entradas con su origen, formato, etiqueta de fuente, estado de revisión y ubicación del texto. La [clasificación de las fuentes adicionales](datos/adicionales/clasificacion/README.md) conserva el detalle por fuente. Para regenerar el catálogo desde esos registros, ejecuta `python datos/generar_catalogo.py`.

La [metodología](docs/metodologia.md) define las etiquetas, la separación por grupos y la evaluación sobre documentos completos.

## Ejecutar el detector

Instala el proyecto con Python 3.11 o posterior.

```sh
python -m pip install -e .
python -m preclone README.md --modelo artefactos/v3/modelo.joblib
```

El repositorio incluye el modelo entrenado `markdown-mixto-v3`. La segunda orden devuelve un JSON con estado, versión del modelo, puntaje y, cuando corresponde, fragmento y líneas de origen. La versión obtuvo un 78,0 % de exactitud balanceada en 388 muestras externas reservadas para prueba. [Evaluación](artefactos/v3/evaluacion.json) · [Particiones](artefactos/v3/particiones.csv)

El artefacto joblib contiene un diccionario con `formato` igual a 1, `version`, `modelo`, `umbral_inferior` y `umbral_superior`. El objeto `modelo` contiene la transformación de texto y el clasificador. Debe exponer `predict_proba` y `classes_` con las clases `[0, 1]`. Carga únicamente artefactos que tú hayas generado o cuyo origen sea confiable, porque joblib deserializa objetos de Python.

## Usar Preclone desde un agente

La [guía de instalación del MCP y la skill](docs/mcp.md) cubre Windows y Linux. El servidor analiza con el modelo v3 y pide autorización antes del checkout.

## Entrenar la línea base

```sh
python -m pip install -e .
python -m preclone.entrenar
```

El entrenamiento escribe el modelo, el informe de evaluación y la lista de particiones en `artefactos/`. Para añadir las pruebas externas, instala con `python -m pip install -e ".[evaluacion]"`, coloca `primary.parquet` y `skills.jsonl` en `datos/adicionales/descargas/` y ejecuta `python -m preclone.entrenar --evaluar-adicionales`.

Para reproducir los modelos mixtos con las tres fuentes descargadas, incluidas las muestras de `train.jsonl`, ejecuta:

```sh
python -m pip install -e ".[evaluacion]"
python -m preclone.entrenar_mixto
python -m preclone.entrenar_mixto --ampliar
python -m preclone ejemplo.md --modelo artefactos/v3/modelo.joblib
```

Las versiones mixtas guardan el modelo, las métricas y las particiones en `artefactos/v2/` y `artefactos/v3/`.

## Verificar sin entrenar

```sh
python -m unittest discover -s pruebas -v
```

Las pruebas usan un modelo simulado para comprobar umbrales, líneas, carga del artefacto y ejecución por terminal.
