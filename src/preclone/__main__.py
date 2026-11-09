"""Analiza un archivo Markdown local y escribe el resultado en JSON."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .detector import Detector


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown", type=Path, help="Ruta del archivo Markdown en UTF-8.")
    parser.add_argument("--modelo", required=True, type=Path, help="Artefacto local de origen confiable.")
    argumentos = parser.parse_args(argv)

    try:
        texto = argumentos.markdown.read_text(encoding="utf-8-sig")
        detector = Detector.cargar(argumentos.modelo)
        resultado = detector.analizar(texto)
    except (OSError, ValueError, EOFError) as exc:
        parser.error(str(exc))

    print(json.dumps(asdict(resultado), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
