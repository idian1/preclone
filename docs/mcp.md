# Instalar Preclone como servidor MCP

Necesitas Git, Python 3.11 o posterior y un cliente MCP con ejecución local. Para autorizar una clonación desde el chat, el servidor necesita Tk y una sesión de escritorio. La instalación estándar de Python para Windows incluye Tk si se selecciona Tcl/Tk. En Debian o Ubuntu puedes instalarlo con `sudo apt install python3-tk python3-venv git`.

Clona [idian1/preclone](https://github.com/idian1/preclone) en una carpeta local con una cuenta que tenga acceso y abre una terminal en esa carpeta.

## Windows

Abre PowerShell y ejecuta estos comandos. Si tu instalación usa `python` en lugar de `py -3.12`, sustituye el lanzador en la primera línea.

```powershell
py -3.12 -m venv .venv-mcp
$preclonePython = (Resolve-Path ".venv-mcp/Scripts/python.exe").Path
& $preclonePython -m pip install -e ".[mcp]"
$precloneModel = (Resolve-Path "artefactos/v3/modelo.joblib").Path
$precloneClones = Join-Path (Get-Location).Path ".preclone/clones"
codex mcp add preclone -- $preclonePython -B -m preclone.mcp --modelo $precloneModel --destinos $precloneClones
```

## Linux

```sh
python3 -m venv .venv-mcp
preclone_dir="$(pwd -P)"
"$preclone_dir/.venv-mcp/bin/python" -m pip install -e ".[mcp]"
codex mcp add preclone -- "$preclone_dir/.venv-mcp/bin/python" -B -m preclone.mcp \
  --modelo "$preclone_dir/artefactos/v3/modelo.joblib" \
  --destinos "$preclone_dir/.preclone/clones"
```

Si usas la configuración de escritorio o un cliente distinto, elige `stdio`, usa la ruta absoluta de Python del entorno como comando y pasa como argumentos `-B`, `-m`, `preclone.mcp`, `--modelo`, la ruta absoluta del modelo, `--destinos` y la ruta absoluta donde quedarán los clones. Nombra el servidor `preclone` para que coincida con la skill.

Si el cliente permite ajustar el tiempo de ejecución de cada herramienta, usa 420 segundos para dar tiempo a Git y a la decisión humana. En el archivo de configuración de Codex, añade `tool_timeout_sec = 420` a la tabla `[mcp_servers.preclone]` ya creada. [Configuración MCP de Codex](https://learn.chatgpt.com/docs/extend/mcp)

## Probar desde el chat

1. Abre la carpeta de Preclone en un chat local nuevo. En Codex, la skill se carga desde [`.agents/skills`](../.agents/skills/revisar-antes-de-clonar/SKILL.md). En otro cliente, copia esa carpeta de skill a la ubicación que reconozca.
2. Comprueba que `preclone` expone `revisar_markdown` y `clonar_protegido`. En Codex puedes comprobarlo con `/mcp`.
3. Escribe **Clona** seguido de la URL HTTPS de un repositorio público de GitHub. La skill indica que debe invocarse `clonar_protegido`. Para solo revisar, escribe **Revisa el Markdown de** seguido de la URL.
4. Pulsa **Cancelar** para terminar sin crear el clon o **Aceptar** para autorizar el checkout. Codex muestra la ruta y el HEAD verificado.

El MCP usa Git para obtener los objetos de un commit y analiza los archivos `.md` y `.markdown` de ese árbol con el modelo entrenado v3. El checkout ocurre después de autorizarlo. La lectura admite repositorios públicos, hasta 256 archivos Markdown en UTF-8, 512 KiB por archivo y 8 MiB en total. La herramienta se detiene si excede esos límites o encuentra un Markdown que no puede leer. Los submódulos quedan fuera del árbol revisado.
