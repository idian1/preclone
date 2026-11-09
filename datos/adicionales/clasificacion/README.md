# Clasificación de las fuentes adicionales

Cada fila identifica una muestra por la línea del JSONL original, por su identificador en Parquet o por su archivo en GitHub. Se conserva la huella del texto recibido o del objeto Git. `lineas_evidencia` indica las líneas dentro del texto, con numeración desde 1. Cuando está presente, `etiqueta_origen` conserva la etiqueta del proveedor. El tipo de ataque indica la acción que el texto busca provocar y la técnica indica cómo la presenta u oculta. Los tipos y los estados de revisión son anotaciones de Preclone.

## ClawHub

El [catálogo de ClawHub](clawhub.csv) incluye los 347 documentos del archivo recibido. De los 124 etiquetados como maliciosos, 117 presentan instrucciones para obtener o ejecutar código externo bajo un pretexto de instalación. Los siete restantes requieren revisión porque el texto cita indicadores, depende de scripts asociados o contiene un enlace aislado. Los 223 etiquetados como benignos conservan su etiqueta de origen pendiente de revisión. [Procedencia](../procedencia_clawhub.json)

| Técnica principal | Candidatos |
| --- | ---: |
| Ejecución de un comando oculto en Base64 | 53 |
| Copia y ejecución desde una página de fragmentos | 35 |
| Descarga directa de un instalador | 29 |

Los conteos asignan una técnica principal por documento. Una fila puede registrar técnicas adicionales, como el uso de un archivo protegido con contraseña. Los comandos Base64 se decodificaron como texto para comprobar si incluyen una descarga. Las variantes que reutilizan la misma instrucción o plantilla deben agruparse antes de definir las particiones.

## CloneGuard

El [catálogo de CloneGuard](cloneguard.csv) reúne una primera selección revisada de 33 textos. Se eligieron fragmentos con estructura de documentación y ejemplos breves donde la orden dirigida al agente se distingue en el propio texto. El JSONL conserva el texto y la etiqueta, de modo que la selección se registra como fragmentos. [Procedencia](../procedencia_cloneguard.json)

| Tipo principal | Candidatos prioritarios |
| --- | ---: |
| Exposición o envío de datos | 6 |
| Alteración de instrucciones | 2 |
| Desactivación de controles | 2 |
| Ejecución de código externo | 1 |
| Propagación de reglas | 1 |
| Generación de código inseguro | 1 |

La selección también incluye 13 controles de documentación y siete casos pendientes de revisión. En estos últimos, el riesgo descrito puede depender de otro archivo o aparecer en una explicación del ataque.

## MaliciousSkillBench

El [catálogo de MaliciousSkillBench](maliciousskillbench.csv) registra las 209 filas de `primary.parquet` que incluyen `SRC002` o `SRC004` en su lista de fuentes. Hay 153 con `SRC002` como fuente principal, 33 con `SRC004` y 23 cuyo texto canónico se atribuye a `SRC001`. Los tres textos que coinciden con ClawHub aparecen con su fila original en `coincidencias_locales`. La comparación aplica la normalización de formato documentada por el benchmark. [Procedencia](../procedencia_maliciousskillbench.json) · [Normalización del benchmark](https://arxiv.org/html/2608.19901v1#A3.SS1)

Siete candidatos prioritarios tienen evidencia revisada en el texto de ejecución externa, persistencia, envío de datos o desactivación de controles. Uno es representante de un patrón de instalación que aparece en 85 documentos. Los otros 84 quedan como variantes para revisar y agrupar. También se marcaron dos textos editados por el proveedor y una muestra que se presenta como demostración desactivada. La etiqueta del benchmark se conserva por separado.

## MalSkillBench

El [catálogo de MalSkillBench](malskillbench_wild.csv) cruza 20 archivos `SKILL.md` marcados `WILD` en el inventario original con los JSONL y el Parquet disponibles. El inventario consultado tiene la huella Git `92119062b087b4f8d73760ba6f24d15c8837e071`. Se comparó la huella Git de los textos UTF-8 con sus variantes de fin de línea LF y CRLF. Se eligieron muestras de distintas cuentas para explorar la fuente. Los resultados describen esa selección. [Inventario de MalSkillBench](https://github.com/lxyeternal/MalSkillBench/blob/main/Dataset/Skills/malware/_source_inventory.txt) · [Estudio](https://arxiv.org/abs/2606.07131)

Los 20 archivos representan 18 textos distintos. Doce ya estaban catalogados. De los seis nuevos, cinco están disponibles en el Parquet y uno se conserva como referencia a GitHub con la huella del objeto. Cuatro son prioritarios por sus instrucciones para obtener o ejecutar software externo y dos quedan pendientes de confirmar. `WILD` indica la procedencia declarada en el inventario. Para confirmar la etiqueta de cada Markdown, se revisa si la instrucción maliciosa aparece en el propio texto.

## Muestras de laboratorio

El [catálogo de laboratorio](laboratorio.csv) registra 1.400 candidatos con etiqueta positiva de MaliciousSkillBench en dos lotes de 700. Los textos se consultan por `id_benchmark` en `descargas/primary.parquet`, cuya versión y huella figuran en el [registro de procedencia](../procedencia_maliciousskillbench.json). El CSV conserva metadatos y huellas. La procedencia `laboratorio` describe cómo se preparó la muestra. La etiqueta y el estado de revisión textual se guardan en columnas separadas. [Ficha del benchmark](https://huggingface.co/datasets/ProtectSkills/MaliciousSkillBench) · [Metodología del benchmark](https://arxiv.org/html/2608.19901v1#A2.SS5)

| Procedencia declarada por el benchmark | Candidatos |
| --- | ---: |
| Inyección controlada (`injected`) | 1.287 |
| Caso preparado para pruebas (`test_fixture`) | 77 |
| Documento sintético (`synthetic`) | 31 |
| Puerta trasera introducida (`backdoored`) | 5 |

Se admitieron textos completos y sin redacciones según el benchmark, con una sola fuente declarada, entre 200 y 24.000 caracteres y con un encabezado Markdown inicial o un bloque YAML inicial con `name`. Se descartaron coincidencias de identificador, huella y familia cuando esos datos existían en los catálogos previos. También se comparó con los textos del profesor, CloneGuard y ClawHub usando normalización Unicode NFC, finales de línea LF, sin BOM y con espacios exteriores y de fin de línea recortados. Para las referencias de MalSkillBench disponibles solo en GitHub se comparó la huella Git con variantes de fin de línea. Se tomó un representante por familia estructural, alternando por ID de fuente y ordenando las candidatas de cada fuente por SHA-256 del ID.

El primer lote reúne 311 de SkillTrustBench, 241 de SkillHarm, 63 de AgentTrap, 50 de SkillSafetyBench, 20 de SkillFortifyBench, 14 de ATR Skill Security Benchmark y uno de SkillTrojan. El segundo lote se añadió al final con el mismo criterio, excluidas las familias del primero. Sus 700 filas son de SkillTrustBench. Esta fuente representa 1.011 de los 1.400 candidatos.

El filtro identifica candidatos para revisión. El benchmark también etiqueta paquetes de skills, así que hay que comprobar si la instrucción maliciosa aparece en el Markdown. Los catálogos sirven para revisar candidatos y localizar la evidencia. La asignación a entrenamiento, validación y prueba se hará después de validar las etiquetas y agrupar las variantes.

### Revisión de evidencia en el Markdown

El [registro de revisión](revision_laboratorio.csv) cubre los 1.400 candidatos. Cada fila conserva el resultado de la revisión por separado de la etiqueta del benchmark. El análisis automático buscó controles completos con etiqueta benigna y el mismo `name` declarado. Se compararon secuencias de líneas, omitiendo líneas en blanco y normalizando espacios horizontales. Se eligió el control con mayor similitud, dando preferencia a la misma fuente en caso de empate. Se registraron los pares con similitud de al menos 0,85 y sus líneas agregadas o modificadas.

Se encontraron 964 pares candidatos, 958 de la misma fuente. Se registraron 95 nombres repetidos entre 328 muestras de laboratorio para revisar su documento base. La coincidencia de nombre y las parejas propuestas orientan esa revisión. Si se confirma una base común, todas sus versiones, incluido el control, deberán quedar juntas al formar las particiones.

En SkillTrustBench se localizaron automáticamente 260 inserciones de hasta 25 líneas con una orden de ejecutar un script, acompañada de lenguaje que pide ocultar la ejecución, anular instrucciones, omitir la confirmación o actuar fuera de la solicitud. La regla exigió un control de la misma fuente con similitud de al menos 0,95. La fuente incluye tanto ataques en las instrucciones como ataques en scripts del paquete. [Taxonomía de SkillTrustBench](https://huggingface.co/datasets/cuhk-zhuque/SkillTrustBench)

| Resultado de revisión | Candidatos |
| --- | ---: |
| Evidencia localizada y revisada directamente | 39 |
| Indicio localizado por regla, pendiente de revisión directa | 226 |
| Ambigüedad tras revisar el texto | 9 |
| Requiere revisar un archivo asociado | 5 |
| Pendiente de revisión textual | 1.121 |

La revisión directa abarcó 53 casos, entre ellos 34 de las 260 coincidencias automáticas. En los 39 con evidencia se anotaron las líneas y el motivo. Los indicios, los casos ambiguos y las dependencias externas mantienen su etiqueta original y quedan pendientes de una decisión para Preclone. Una de las comprobaciones encontró que omitir la salida de un instalador puede ser parte de la documentación normal. Otra localizó una orden para buscar y enviar credenciales dentro del propio texto.

El Parquet contiene 2.141 controles potenciales con etiqueta benigna, texto completo y sin redacciones. Son una reserva para revisar por fuente y procedencia. Los 600 textos benignos del profesor corresponden a escenarios y se registran aparte de los controles Markdown. Antes de fijar las particiones queda por validar los controles seleccionados, resolver la agrupación por documento base y mantener una evaluación separada para los casos reales.
