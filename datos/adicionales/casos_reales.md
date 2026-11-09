# Casos reales para analizar con Preclone

## AgentBaiting

Island identificó repositorios falsos que presentaban instaladores maliciosos como herramientas para agentes. Los casos de esta tabla son señuelos de la misma campaña y conviene agruparlos si se recuperan los archivos originales. [Informe de Island](https://www.island.io/blog/agentbaiting-how-800-fake-ai-skills-and-mcp-servers-delivered-malware) · [Indicadores de la campaña](https://github.com/island-io/island-security-research-artifacts/tree/main/agentbaiting)

| Repositorio reportado | Evidencia en Markdown | Disponibilidad |
| --- | --- | --- |
| `adlaiponderous700/claude-skill-cinematic-prompt` | El README indica ejecutar un instalador y continuar si Windows muestra una advertencia. En una prueba de Island, Claude encontró el repositorio y repitió sus instrucciones. | Vista indexada del README. GitHub devolvió 404 al consultar el original por API. [Vista indexada](https://github.com/adlaiponderous700/claude-skill-cinematic-prompt/blob/main/README.md) |
| `Mann1988/awesome-claude-skills` | El README del proyecto suplantado dirige a un ZIP que Island identificó como SmartLoader. | Vista indexada del README. GitHub devolvió 404 al consultar el original por API. [Vista indexada](https://github.com/Mann1988/awesome-claude-skills/blob/main/README.md) |
| `45d5r/databricks-mcp-server` | El README dirige al lector a descargar, extraer y ejecutar un instalador. | Captura conservada en la figura 5 del informe. GitHub devolvió 404 al consultar el original por API. |

Estos casos permiten estudiar instrucciones de instalación engañosas y el papel del README como vía de entrega. Conviene registrar por separado si el texto se dirige explícitamente al agente o si este retransmite instrucciones escritas para el lector.

## Hackerbot-Claw contra ambient-code/platform

Los PR 732 y 733 incluyeron reemplazos de `CLAUDE.md` dirigidos al revisor automatizado. El texto le pedía modificar el README, subir cambios y publicar una aprobación engañosa. StepSecurity documentó que Claude detectó los dos intentos. GitHub devolvió 404 al consultar los archivos de ambos PR, y el informe conserva capturas y un resumen de las instrucciones. Es un caso de manipulación de la revisión mediante instrucciones del proyecto. [Informe de StepSecurity](https://www.stepsecurity.io/blog/hackerbot-claw-github-actions-exploitation#attack-5-ambient-codeplatform---ai-prompt-injection)

## Archivo de skills observadas en registros públicos

El estudio *Malicious Agent Skills in the Wild* confirmó comportamiento malicioso en 157 skills publicadas en registros públicos. El archivo `SRC002_packages.tar.gz` conserva 157 artefactos de esa fuente. El manifiesto principal incluye 153 identidades de esta colección. Para Preclone interesa inspeccionar cada `SKILL.md` como texto y comprobar en qué archivo aparece la orden maliciosa. El estudio verifica el comportamiento del paquete, que puede depender de scripts asociados. [Estudio](https://arxiv.org/abs/2602.06547) · [Archivo SRC002](https://github.com/protectskills/MaliciousSkillBench/blob/main/packages/SRC002_packages.tar.gz) · [Manifiesto](https://github.com/protectskills/MaliciousSkillBench/blob/main/packages/package_manifest.csv)

## Campañas de afiliación y transferencias en ClawHub

Unit 42 documentó `money-radar`, una skill que usaba enlaces de afiliación, y `letssendit`, que coordinaba una transferencia de criptomonedas. Se conservan como referencias de investigación. Sus nombres no aparecieron en una búsqueda literal sobre los textos de `primary.parquet` y queda pendiente localizar el Markdown completo de cada caso. [Informe de Unit 42](https://unit42.paloaltonetworks.com/openclaw-ai-supply-chain-risk/)
