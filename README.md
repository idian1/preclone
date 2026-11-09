# Preclone

Preclone revisa los archivos Markdown de un repositorio público de GitHub. Si pides clonar, te muestra el resultado y solicita tu autorización antes de guardar el clon.

## Instalar en Windows

Necesitas Windows x64, Git, Codex de escritorio y conexión a internet para la instalación.

1. Clona la rama `integracion-mcp` o extrae su ZIP completo. [Rama de instalación en GitHub](https://github.com/idian1/preclone/tree/integracion-mcp)
2. Abre `Instalar-Preclone.exe` junto a `AGENTS.md`. Cuando termine, abre `Datos-MCP.txt` en esa misma carpeta.
3. En Codex, entra a **Ajustes → Complementos → MCP** y agrega o edita `preclone`. Elige `stdio` y pega el comando y el único argumento de `Datos-MCP.txt`. Guarda.

## Usar desde Codex

En cualquier chat local, escribe **Usa Preclone para revisar el Markdown de** seguido de la URL pública de GitHub. Si quieres guardar el repositorio, escribe **Usa Preclone para clonar** seguido de la URL. Después de la revisión, la ventana de autorización te permite aceptar o cancelar.

Para instalar en Linux, registrar el servidor por CLI o resolver problemas, consulta la [guía del MCP](docs/mcp.md).
