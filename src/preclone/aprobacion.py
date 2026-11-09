"""Recoge una decisión en el escritorio local sin usar el stdio del MCP."""

import subprocess
import sys

from .repositorio import ProblemaRepositorio


def confirmar(detalle: str) -> bool:
    try:
        respuesta = subprocess.run(
            [sys.executable, "-B", "-m", "preclone.aprobacion"],
            input=detalle.encode("utf-8"), capture_output=True, timeout=90,
        )
    except subprocess.TimeoutExpired:
        return False
    except OSError as exc:
        raise ProblemaRepositorio("No se pudo iniciar la ventana de autorización local.") from exc
    if respuesta.returncode not in (0, 1):
        raise ProblemaRepositorio("No se pudo abrir la ventana. Comprueba Tk y la sesión de escritorio.")
    return respuesta.returncode == 0


def main() -> int:
    import tkinter as tk
    from tkinter import messagebox

    detalle = sys.stdin.buffer.read().decode("utf-8")
    raiz = tk.Tk()
    raiz.withdraw()
    raiz.attributes("-topmost", True)
    try:
        aprobado = messagebox.askokcancel(
            title="Preclone — Autorizar clonación",
            message=detalle,
            icon=messagebox.WARNING,
            default=messagebox.CANCEL,
            parent=raiz,
        )
        return 0 if aprobado else 1
    finally:
        raiz.destroy()


if __name__ == "__main__":
    try:
        codigo = main()
    except Exception:
        # Se reserva 1 para una decisión humana negativa.
        codigo = 2
    raise SystemExit(codigo)
