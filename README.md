# Detector Preclone

Este repositorio contiene el detector local del proyecto. El detector recibe texto Markdown, lo divide en fragmentos que conservan sus líneas, consulta un modelo binario ya entrenado y emite una clasificación con el fragmento de mayor puntaje cuando corresponde.

El [material del profesor](datos/profesor/) contiene 1.200 textos de 50 escenarios y su registro de procedencia. Las [fuentes adicionales](datos/adicionales/) reúnen los registros de CloneGuard, ClawHub, MaliciousSkillBench y los README de GitHub identificados para ampliar el corpus. Las copias locales de los archivos externos se guardan en `datos/adicionales/descargas/`.

El [catálogo maestro](datos/catalogo.csv) reúne 3.191 entradas con su origen, formato, etiqueta de fuente, estado de revisión y ubicación del texto. La [clasificación de las fuentes adicionales](datos/adicionales/clasificacion/README.md) conserva el detalle por fuente. Para regenerar el catálogo desde esos registros, ejecuta `python datos/generar_catalogo.py`.

La [metodología](docs/metodologia.md) define las etiquetas, la separación por grupos y la evaluación sobre documentos completos.

## Ejecutar el detector

Instala el proyecto con Python 3.11 o posterior.

```sh
python -m pip install -e .
python -m preclone ejemplo.md --modelo artefactos/modelo.joblib
```

La segunda orden requiere el artefacto de un entrenamiento posterior. El resultado es JSON con estado, versión del modelo, puntaje y, cuando corresponde, fragmento y líneas de origen.

El artefacto joblib contiene un diccionario con `formato` igual a 1, `version`, `modelo`, `umbral_inferior` y `umbral_superior`. El objeto `modelo` contiene la transformación de texto y el clasificador. Debe exponer `predict_proba` y `classes_` con las clases `[0, 1]`. Carga únicamente artefactos que tú hayas generado o cuyo origen sea confiable, porque joblib deserializa objetos de Python.

## Verificar sin entrenar

```sh
python -m unittest discover -s pruebas -v
```

Las pruebas usan un modelo simulado para comprobar umbrales, líneas, carga del artefacto y ejecución por terminal.
