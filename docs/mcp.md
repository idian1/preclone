# Instalar Preclone como servidor MCP

Clona [idian1/preclone](https://github.com/idian1/preclone) o extrae el ZIP completo. Si estás probando `integracion-mcp`, selecciona esa rama antes de descargar.

## Windows con Codex de escritorio

En Windows de 64 bits (x64), con Git y Codex instalados, abre **`Instalar-Preclone.exe`** con doble clic desde la misma carpeta que `AGENTS.md`. La instalación necesita internet para descargar Python y las dependencias.

El instalador comprueba la descarga de Python 3.12.10 con Tk, prepara el entorno en `.preclone/` y deja `Datos-MCP.txt` junto al ejecutable.

Abre **Ajustes → Complementos → MCP** en Codex. Agrega un servidor local o edita la entrada `preclone` si ya existe. Usa el nombre, el tipo, el comando y el único argumento de `Datos-MCP.txt`. Guarda y prueba el servidor desde un chat local de tu elección.

Si mueves la carpeta de Preclone, ejecuta el instalador de nuevo y actualiza el comando y el argumento en Codex.

## Instalación manual

Necesitas Git, Python 3.11 a 3.13 y un cliente MCP con ejecución local. La ventana de autorización necesita Tk y una sesión de escritorio. El modelo usa scikit-learn 1.6.1. [Compatibilidad de scikit-learn](https://scikit-learn.org/stable/install.html)

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

Elige la app de escritorio o el CLI para registrar el servidor.

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

Si el cliente permite ajustar el tiempo de ejecución de cada herramienta, usa 420 segundos para dar tiempo a Git y a la decisión humana. En el archivo de configuración de Codex, añade `tool_timeout_sec = 420` a la tabla `[mcp_servers.preclone]` ya creada. [Configuración MCP de Codex](https://learn.chatgpt.com/docs/extend/mcp)

## Probar desde el chat

1. En un chat local comprueba que `preclone` expone `revisar_markdown` y `clonar_protegido`. En Codex puedes comprobarlo con `/mcp`.
2. Escribe **Usa Preclone para clonar** seguido de la URL HTTPS de un repositorio público de GitHub. Para solo revisar, escribe **Usa Preclone para revisar el Markdown de** seguido de la URL.
3. Pulsa **Cancelar** para terminar sin crear el clon o **Aceptar** para autorizar el checkout. Codex muestra la ruta y el HEAD verificado.

La [skill incluida](../.agents/skills/revisar-antes-de-clonar/SKILL.md) indica al agente qué herramienta usar cuando escribes **Clona** y una URL. Codex la detecta como skill de proyecto en la carpeta de Preclone. Si quieres usarla en otros proyectos, puedes copiarla a la carpeta de skills de tu usuario. El registro del servidor se hace por separado. [Cómo carga skills Codex](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)

El MCP usa Git para obtener los objetos de un commit y analiza los archivos `.md` y `.markdown` de ese árbol con el modelo entrenado v3. El checkout ocurre después de autorizarlo. La lectura admite repositorios públicos, hasta 256 archivos Markdown en UTF-8, 512 KiB por archivo y 8 MiB en total. La herramienta se detiene si excede esos límites o encuentra un Markdown que no puede leer. Los submódulos quedan fuera del árbol revisado.

El código del instalador está en `instalacion/InstalarPreclone.cs`. En Windows, `instalacion/compilar-windows.ps1` genera el ejecutable con el compilador de .NET Framework.
