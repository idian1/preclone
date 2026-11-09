# Metodología del detector

La unidad de evaluación será el documento Markdown. La clase `1` representa una instrucción que intenta desviar al agente de la tarea autorizada. La clase `0` representa documentación legítima, incluidas instrucciones de instalación y citas que describen un ataque. Para las inyecciones controladas, el manifiesto registrará las líneas añadidas, el documento de origen y el grupo.

El CSV heredado contiene 1.200 textos derivados de 50 escenarios. Su procedencia y huella SHA-256 acompañan al archivo. Servirá como fuente inicial para el entrenamiento y como antecedente del corpus. Los resultados sobre esos escenarios se reportarán por separado de los resultados sobre documentos Markdown completos.

Las particiones de entrenamiento, validación y prueba se fijarán antes de fragmentar. Todos los documentos y variantes de un mismo repositorio quedarán en la misma partición. Para el CSV heredado, se agrupará por escenario. La transformación TF-IDF y los pesos de la regresión logística se aprenderán solo con entrenamiento. La validación servirá para elegir los umbrales sobre documentos completos. Después se medirá el modelo fijado en la prueba final.

El detector puntúa fragmentos solapados y toma el mayor puntaje del documento. En o por encima del umbral superior devuelve **No seguro**. En o por debajo del inferior devuelve **Sin indicios detectados**. Entre ambos, o si el texto es insuficiente, devuelve **No identificado**. El fragmento mostrado permite localizar el puntaje más alto. La evaluación futura registrará por separado alertas, falsas alarmas, abstenciones e inyecciones que quedaron bajo el umbral inferior.
