"""Inicia el servidor con rutas relativas a la instalación de Windows."""

import os
from pathlib import Path

from preclone.detector import Detector
from preclone.mcp import crear_servidor


def main() -> None:
    raiz = Path(__file__).resolve().parents[1]
    local = raiz / ".preclone"
    os.environ["PRECLONE_GIT"] = (local / "git.txt").read_text(encoding="utf-8").strip()
    detector = Detector.cargar(raiz / "artefactos/v3/modelo.joblib")
    crear_servidor(detector, local / "clones").run(transport="stdio")


if __name__ == "__main__":
    main()
