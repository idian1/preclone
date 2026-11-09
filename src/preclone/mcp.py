"""Servidor MCP local que analiza con el modelo entrenado y protege el checkout."""

import argparse
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from unicodedata import category
from uuid import uuid4

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .aprobacion import confirmar
from .detector import Detector, Resultado
from .repositorio import ProblemaRepositorio, git, github, obtener_commit, revisar_commit, verificar_commit


def texto_visible(texto: str, limite: int) -> str:
    limpio = "".join(" " if category(c).startswith("C") else c for c in texto)
    return limpio[:limite] + ("…" if len(limpio) > limite else "")


def detalle_aprobacion(informe: dict, resultados: list[tuple[str, Resultado]], destino: Path) -> str:
    lineas = [
        f"Repositorio: {informe['repositorio']}",
        f"Commit: {informe['commit']}",
        f"Modelo: {informe['modelo']}",
        f"Resultado: {informe['clasificacion']}",
        f"Markdown revisados: {informe['markdown_revisados']}",
        f"Alertas: {informe['alertas']} · Sin identificar: {informe['sin_identificar']}",
        f"Carpeta: {texto_visible(str(destino), 140)}",
    ]
    evidencias = [(ruta, r) for ruta, r in resultados if r.fragmento]
    evidencias.sort(key=lambda item: (item[1].estado != "No seguro", -(item[1].puntaje or 0)))
    for ruta, resultado in evidencias[:3]:
        fragmento = resultado.fragmento
        lineas.extend((
            "",
            f"{texto_visible(ruta, 100)} · líneas {fragmento.linea_inicio}–{fragmento.linea_fin}",
            texto_visible(fragmento.texto, 150),
        ))
    lineas.extend(("", "Aceptar autoriza el checkout del commit revisado. ¿Deseas clonar?"))
    return "\n".join(lineas)


def proteger(
    detector: Detector, destinos: Path, repositorio: str, ref: str | None, *, clonar: bool,
) -> dict[str, str | int]:
    informe = {"modelo": detector.version}
    try:
        nombre = github(repositorio)
        informe["repositorio"] = nombre
        destinos.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".revision-", dir=destinos) as temporal:
            revision = Path(temporal) / "repositorio"
            revision.mkdir()
            commit = obtener_commit(revision, nombre, ref)
            informe["commit"] = commit
            resultados = revisar_commit(revision, commit, detector)
            estados = Counter(r.estado for _, r in resultados)
            clasificacion = "No identificado"
            if estados["No seguro"]:
                clasificacion = "No seguro"
            elif resultados and not estados["No identificado"]:
                clasificacion = "Sin indicios detectados"
            informe.update(
                clasificacion=clasificacion, markdown_revisados=len(resultados),
                alertas=estados["No seguro"], sin_identificar=estados["No identificado"],
            )
            if not clonar:
                return {**informe, "estado": "revisado"}
            destino = destinos / f"{nombre.split('/')[1]}-{uuid4().hex[:12]}"
            if not confirmar(detalle_aprobacion(informe, resultados, destino)):
                return {**informe, "estado": "rechazado"}
            git(revision, "checkout", "--detach", "--no-recurse-submodules", commit, tiempo=60)
            head = verificar_commit(revision, "HEAD")
            if head != commit:
                raise ProblemaRepositorio("HEAD no coincide con el commit revisado.")
            revision.rename(destino)
            return {**informe, "estado": "clonado", "destino": str(destino), "head_verificado": head}
    except ProblemaRepositorio as exc:
        return {**informe, "estado": "detenido", "motivo": str(exc)}
    except (OSError, ValueError):
        return {**informe, "estado": "detenido", "motivo": "No se pudo completar el análisis o guardar el clon local."}


def crear_servidor(detector: Detector, destinos: Path) -> FastMCP:
    servidor = FastMCP(
        "Preclone",
        instructions=(
            "Si la persona pide clonar un repositorio público de GitHub, usa clonar_protegido. "
            "La decisión se recoge en la ventana local. Si la respuesta es detenido o rechazado, "
            "termina la operación. Si solo pide revisar, usa revisar_markdown."
        ),
    )

    @servidor.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
    def revisar_markdown(repositorio: str, ref: str | None = None) -> dict[str, str | int]:
        """Revisa el Markdown de un commit público de GitHub, sin hacer checkout."""
        return proteger(detector, destinos, repositorio, ref, clonar=False)

    @servidor.tool(annotations=ToolAnnotations(destructiveHint=False, openWorldHint=True))
    def clonar_protegido(repositorio: str, ref: str | None = None) -> dict[str, str | int]:
        """Revisa GitHub y pide autorización en el escritorio antes de clonar el commit."""
        return proteger(detector, destinos, repositorio, ref, clonar=True)

    return servidor


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modelo", type=Path, required=True, help="Artefacto local de origen confiable.")
    parser.add_argument("--destinos", type=Path, required=True, help="Carpeta para los clones aprobados.")
    args = parser.parse_args()
    detector = Detector.cargar(args.modelo)
    crear_servidor(detector, args.destinos.resolve()).run(transport="stdio")


if __name__ == "__main__":
    main()
