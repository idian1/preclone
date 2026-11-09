"""Lee el árbol de GitHub desde los objetos de Git, antes del checkout."""

from dataclasses import dataclass
from io import BytesIO
import os
from pathlib import Path
import re
import shutil
import subprocess

from .detector import Detector, Resultado


class ProblemaRepositorio(Exception):
    """Impidió completar la revisión o verificar el clon."""


@dataclass(frozen=True)
class Markdown:
    ruta: str
    objeto: bytes
    tamano: int


_REPOSITORIO = re.compile(
    r"(?:https://github\.com/)?([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9_.-]{1,104})/?",
    re.IGNORECASE | re.ASCII,
)
_SHA = re.compile(rb"[0-9a-f]{40}")
_EXTENSIONES = (b".md", b".markdown")
_MAX_ARCHIVOS = 256
_MAX_ARCHIVO = 512 * 1024
_MAX_TOTAL = 8 * 1024 * 1024


def github(repositorio: str) -> str:
    """Acepta solo identificadores y URLs HTTPS de GitHub."""
    coincidencia = _REPOSITORIO.fullmatch(repositorio.strip())
    if coincidencia:
        propietario, nombre = coincidencia.groups()
        if nombre.lower().endswith(".git"):
            nombre = nombre[:-4]
        if nombre not in ("", ".", "..") and len(nombre) <= 100:
            return f"{propietario}/{nombre}"
    raise ProblemaRepositorio("Indica una URL HTTPS de GitHub o un propietario/repositorio.")


def git(directorio: Path, *argumentos: str, entrada: bytes = b"", tiempo: int = 30) -> bytes:
    # Se ignoran configuraciones que puedan ejecutar filtros, hooks o reescribir la URL.
    entorno = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    entorno.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")
    ejecutable = entorno.get("PRECLONE_GIT")
    if ejecutable:
        ruta_git = Path(ejecutable)
        if not ruta_git.is_absolute() or not ruta_git.is_file():
            raise ProblemaRepositorio("La ruta de Git configurada para Preclone no es válida.")
    else:
        rutas = os.pathsep.join(ruta for ruta in os.get_exec_path(entorno) if os.path.isabs(ruta))
        modo = os.F_OK if os.name == "nt" else os.F_OK | os.X_OK
        ejecutable = shutil.which("git", mode=modo, path=rutas)
    if not ejecutable:
        raise ProblemaRepositorio("Git no está disponible en el PATH.")
    try:
        proceso = subprocess.run(
            [
                ejecutable,
                "-c", f"core.hooksPath={os.devnull}",
                "-c", "credential.helper=",
                "-c", "http.followRedirects=false",
                "-c", "protocol.allow=never",
                "-c", "protocol.https.allow=always",
                "-c", "submodule.recurse=false",
                *argumentos,
            ],
            cwd=directorio, env=entorno, input=entrada, capture_output=True, timeout=tiempo,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProblemaRepositorio(f"Git excedió el tiempo permitido en {argumentos[0]}.") from exc
    except OSError as exc:
        raise ProblemaRepositorio("No se pudo ejecutar Git.") from exc
    if proceso.returncode:
        if argumentos[0] == "fetch":
            raise ProblemaRepositorio("Git no pudo obtener el repositorio público o la referencia.")
        if argumentos[0] == "check-ref-format":
            raise ProblemaRepositorio("La referencia debe ser una rama, etiqueta o SHA válido.")
        raise ProblemaRepositorio(f"Git no pudo completar {argumentos[0]}.")
    return proceso.stdout


def obtener_commit(directorio: Path, repositorio: str, ref: str | None) -> str:
    referencia = "HEAD" if ref is None else ref.strip()
    if not referencia or referencia.startswith(("-", "+")) or len(referencia) > 250:
        raise ProblemaRepositorio("La referencia debe ser una rama, etiqueta o SHA válido.")
    git(directorio, "check-ref-format", "--allow-onelevel", referencia)
    git(directorio, "init", "--template=", "--object-format=sha1")
    git(directorio, "remote", "add", "origin", f"https://github.com/{repositorio}.git")
    git(directorio, "fetch", "--no-tags", "--depth=1", "--no-recurse-submodules",
        "--", "origin", referencia, tiempo=120)
    return verificar_commit(directorio, "FETCH_HEAD")


def verificar_commit(directorio: Path, ref: str) -> str:
    objeto = git(directorio, "rev-parse", "--verify", f"{ref}^{{commit}}").strip()
    if not _SHA.fullmatch(objeto):
        raise ProblemaRepositorio("Git no devolvió un SHA de commit válido.")
    return objeto.decode("ascii")


def revisar_commit(directorio: Path, commit: str, detector: Detector) -> list[tuple[str, Resultado]]:
    archivos = []
    total = 0
    arbol = git(directorio, "ls-tree", "-r", "-l", "-z", commit)
    for linea in arbol.rstrip(b"\0").split(b"\0") if arbol else ():
        metadatos, ruta = linea.split(b"\t", 1)
        if not ruta.lower().endswith(_EXTENSIONES):
            continue
        modo, _, objeto, tamano = metadatos.split()
        if modo not in (b"100644", b"100755"):
            raise ProblemaRepositorio("El árbol contiene un Markdown que no es un archivo regular.")
        archivo = Markdown(ruta.decode("utf-8", "replace"), objeto, int(tamano))
        archivos.append(archivo)
        total += archivo.tamano
        if archivo.tamano > _MAX_ARCHIVO or total > _MAX_TOTAL or len(archivos) > _MAX_ARCHIVOS:
            raise ProblemaRepositorio("El conjunto de Markdown supera el límite local de revisión.")
    if not archivos:
        return []

    entrada = b"".join(archivo.objeto + b"\n" for archivo in archivos)
    blobs = BytesIO(git(directorio, "cat-file", "--batch", entrada=entrada))
    resultados = []
    for archivo in archivos:
        cabecera = b"%s blob %d\n" % (archivo.objeto, archivo.tamano)
        if blobs.readline() != cabecera:
            raise ProblemaRepositorio("Git devolvió un objeto distinto al registrado en el árbol.")
        contenido = blobs.read(archivo.tamano)
        if len(contenido) != archivo.tamano or blobs.read(1) != b"\n":
            raise ProblemaRepositorio("Git devolvió un archivo Markdown incompleto.")
        try:
            texto = contenido.decode("utf-8-sig")
        except UnicodeError as exc:
            raise ProblemaRepositorio("Un archivo Markdown no está codificado en UTF-8.") from exc
        if "\0" in texto:
            raise ProblemaRepositorio("Un archivo Markdown contiene datos binarios.")
        resultados.append((archivo.ruta, detector.analizar(texto)))
    return resultados
