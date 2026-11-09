# Instalar Preclone como servidor MCP

Selecciona la rama `integracion-mcp` en GitHub. Puedes clonarla con el comando de abajo o usar **Code → Download ZIP** y extraer el archivo completo. Abre la carpeta que contiene `AGENTS.md` y el modelo `artefactos/v3/modelo.joblib`. [Rama de instalación en GitHub](https://github.com/idian1/preclone/tree/integracion-mcp)

```sh
git clone --branch integracion-mcp --single-branch https://github.com/idian1/preclone.git
```

## Windows con Codex de escritorio

Con Windows x64, Git y Codex de escritorio instalados, abre **`Instalar-Preclone.exe`** con doble clic. La instalación descarga Python 3.12.10 con Tk y prepara el entorno en `.preclone/`. Necesita conexión a internet.

Cuando el instalador indique que Preclone está listo, abre `Datos-MCP.txt` junto al ejecutable. En Codex ve a **Ajustes → Complementos → MCP** y agrega un servidor local. Si ya tienes un servidor `preclone`, edítalo y sustituye sus valores por los del archivo.

| Campo en Codex | Valor |
| --- | --- |
| Nombre | `preclone` |
| Transporte | `stdio` |
| Comando | La ruta de `.preclone\venv\Scripts\python.exe` que aparece en el archivo. |
| Argumentos | Solo la ruta de `instalacion\iniciar_mcp.py` que aparece en el archivo. |

Guarda la entrada en los ajustes generales de Codex. Puedes usarla desde cualquier chat local. La primera prueba está en [Probar desde el chat](#probar-desde-el-chat).

Si mueves la carpeta de Preclone, ejecuta el instalador de nuevo y actualiza el comando y el argumento en Codex.

## Instalación manual

Sigue esta opción para instalar en Linux o preparar tu propio entorno en Windows. Necesitas Git, Python 3.11 a 3.13 y un cliente MCP con ejecución local. La ventana de autorización necesita Tk y una sesión de escritorio. El modelo usa scikit-learn 1.6.1. [Compatibilidad de scikit-learn](https://scikit-learn.org/stable/install.html)

### Windows

Si tienes el administrador de Python para Windows y aún te falta la versión 3.12, ejecuta `py install 3.12`. Luego, desde la carpeta de Preclone, crea el entorno e instala las dependencias.

En PowerShell:

```powershell
py -3.12 -m venv .venv-mcp
.\.venv-mcp\Scripts\python.exe -m pip install -e ".[mcp]"
```

En Git Bash:

```bash
py -3.12 -m venv .venv-mcp
./.venv-mcp/Scripts/python.exe -m pip install -e '.[mcp]'
```

### Linux

En Debian o Ubuntu puedes instalar Tk, `venv` y Git para el Python del sistema con `sudo apt install python3-tk python3-venv git`.

Comprueba la versión con `python3 --version`. Si queda fuera del rango indicado, usa el ejecutable de una versión compatible instalada en tu equipo.

```sh
python3 -m venv .venv-mcp
./.venv-mcp/bin/python -m pip install -e ".[mcp]"
```

### Registrar el MCP manualmente

Con el entorno manual `.venv-mcp` listo, registra el servidor desde la app de escritorio o el CLI. Si usaste el ejecutable de Windows, usa en su lugar los valores de `Datos-MCP.txt`.

#### Codex de escritorio

En Ajustes, abre Servidores MCP y añade un servidor local con el nombre `preclone` y el tipo `stdio`. En **Comando** pon la ruta absoluta del Python del entorno. En Windows termina en `.venv-mcp\Scripts\python.exe` y en Linux, en `.venv-mcp/bin/python`.

En **Argumentos** agrega cada línea por separado. Este ejemplo usa rutas de Windows. Sustitúyelas por las rutas absolutas de tu equipo.

```text
-B
-m
preclone.mcp
--modelo
C:\ruta\preclone\artefactos\v3\modelo.joblib
--destinos
C:\ruta\preclone\.preclone\clones
```

En otro cliente MCP local, registra el mismo comando y argumentos con el nombre `preclone`.

#### CLI de Codex

En PowerShell:

```powershell
$preclonePython = (Resolve-Path ".venv-mcp/Scripts/python.exe").Path
$precloneModel = (Resolve-Path "artefactos/v3/modelo.joblib").Path
$precloneClones = Join-Path (Get-Location).Path ".preclone/clones"
codex mcp add preclone -- $preclonePython -B -m preclone.mcp --modelo $precloneModel --destinos $precloneClones
```

En Linux:

```sh
preclone_dir="$(pwd -P)"
codex mcp add preclone -- "$preclone_dir/.venv-mcp/bin/python" -B -m preclone.mcp \
  --modelo "$preclone_dir/artefactos/v3/modelo.joblib" \
  --destinos "$preclone_dir/.preclone/clones"
```


## Probar desde el chat

1. En un chat local de Codex, escribe `/mcp` y comprueba que aparece `preclone` con `revisar_markdown` y `clonar_protegido`.
2. Escribe `Usa Preclone para revisar el Markdown de <URL pública de GitHub>`. La respuesta indica el commit revisado, la clasificación y cuántos archivos se revisaron.
3. Para clonar, escribe `Usa Preclone para clonar <URL pública de GitHub>`. Si la revisión se completa, Preclone abre una ventana de autorización. Pulsa **Cancelar** para terminar o **Aceptar** para guardar el clon. Codex muestra la ruta y el commit verificado.

La [skill incluida](../.agents/skills/revisar-antes-de-clonar/SKILL.md) indica al agente qué herramienta usar cuando escribes **Clona** y una URL. Codex la detecta como skill de proyecto en la carpeta de Preclone. Si quieres usarla en otros proyectos, puedes copiarla a la carpeta de skills de tu usuario. El registro del servidor se hace por separado. [Cómo carga skills Codex](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)

## Interpretar el resultado

Preclone usa Git para leer los archivos `.md` y `.markdown` de un commit de un repositorio público. El modelo v3 analiza ese texto. Las estrellas y los comentarios de GitHub quedan fuera del análisis. La revisión admite hasta 256 archivos Markdown en UTF-8, 512 KiB por archivo y 8 MiB en total. Los submódulos quedan fuera del árbol revisado.

| Clasificación | Significado |
| --- | --- |
| Sin indicios detectados | El detector no señaló fragmentos en los Markdown revisados. |
| No identificado | El detector no pudo clasificar con suficiente claridad o el commit carece de Markdown. |
| No seguro | Al menos un fragmento superó el umbral de alerta. En la ventana de clonación puedes revisar el archivo y las líneas señaladas. |

El detector puede alertar sobre documentación legítima. Revisa las líneas señaladas antes de decidir si quieres clonar. El resultado cubre los Markdown que analizó.

Si la revisión queda incompleta, por ejemplo por un archivo ilegible o por superar un límite, el servidor devuelve `detenido`. Si cancelas en la ventana, devuelve `rechazado`. Tras la autorización, devuelve `clonado` si guardó el repositorio y verificó que su commit coincide con el revisado.

## Si el servidor no aparece o la revisión tarda

- Comprueba que guardaste `preclone` en los ajustes generales de Codex y que el comando y sus argumentos apuntan a archivos que siguen en su carpeta original. Abre un chat local nuevo y vuelve a consultar `/mcp`.
- Si el instalador termina con un error, comprueba que abriste el ejecutable desde la carpeta completa del repositorio y que Git e internet están disponibles. Revisa el mensaje del instalador antes de usar `Datos-MCP.txt`.
- El ejecutable de esta rama no tiene firma digital. Windows puede mostrar un aviso al abrirlo.
- Si Codex agota el tiempo de espera durante la revisión o mientras decides en la ventana, añade `tool_timeout_sec = 420` a la tabla existente `[mcp_servers.preclone]` de `config.toml`. [Configuración MCP de Codex](https://learn.chatgpt.com/docs/extend/mcp)
