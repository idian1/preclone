# Detector Preclone

Este repositorio contiene el detector local de la tesis. El detector recibe texto Markdown, lo divide en fragmentos que conservan sus líneas, consulta un modelo binario ya entrenado y emite una clasificación con el fragmento de mayor puntaje cuando corresponde.

El corpus de escenarios entregado por el profesor está en `datos/originales/` junto con su registro de procedencia. La especificación de etiquetas, particiones y evaluación está en [metodología](docs/metodologia.md).

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
