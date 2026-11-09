"""Inferencia sobre Markdown con un modelo binario entrenado por separado."""

from bisect import bisect_left
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
import re

import joblib


LONGITUD_VENTANA = 1200
SALTO_VENTANA = 900
MINIMO_PALABRAS = 4
FORMATO_MODELO = 1


@dataclass(frozen=True)
class Fragmento:
    texto: str
    linea_inicio: int
    linea_fin: int


def fragmentos_markdown(texto: str) -> list[Fragmento]:
    """Conserva los números de línea de cada fragmento del texto original."""
    saltos = [match.start() for match in re.finditer(r"\n", texto)]
    fragmentos = []
    for inicio in range(0, len(texto), SALTO_VENTANA):
        fin = min(inicio + LONGITUD_VENTANA, len(texto))
        candidato = texto[inicio:fin]
        contenido = candidato.strip()
        if len(re.findall(r"\w+", contenido)) >= MINIMO_PALABRAS:
            primer_caracter = inicio + len(candidato) - len(candidato.lstrip())
            ultimo_caracter = inicio + len(candidato.rstrip()) - 1
            fragmentos.append(Fragmento(
                contenido,
                bisect_left(saltos, primer_caracter) + 1,
                bisect_left(saltos, ultimo_caracter) + 1,
            ))
        if fin == len(texto):
            break
    return fragmentos


@dataclass(frozen=True)
class Resultado:
    estado: str
    modelo: str
    puntaje: float | None
    fragmento: Fragmento | None
    motivo: str | None = None


class Detector:
    def __init__(self, modelo, *, version: str, umbral_inferior: float, umbral_superior: float):
        if not isinstance(version, str) or not version.strip():
            raise ValueError("El modelo requiere una versión.")
        if not 0 <= umbral_inferior < umbral_superior <= 1:
            raise ValueError("Los umbrales deben estar ordenados entre 0 y 1.")
        if list(getattr(modelo, "classes_", ())) != [0, 1]:
            raise ValueError("El modelo debe tener las clases 0 (legítimo) y 1 (inyección).")
        if not callable(getattr(modelo, "predict_proba", None)):
            raise ValueError("El modelo debe exponer predict_proba.")
        self.modelo = modelo
        self.version = version
        self.umbral_inferior = umbral_inferior
        self.umbral_superior = umbral_superior

    @classmethod
    def cargar(cls, ruta: Path) -> "Detector":
        """Abre un artefacto joblib generado localmente y de origen confiable."""
        artefacto = joblib.load(ruta)
        if not isinstance(artefacto, dict) or artefacto.get("formato") != FORMATO_MODELO:
            raise ValueError("Formato de artefacto de Preclone incompatible.")
        try:
            return cls(
                artefacto["modelo"],
                version=artefacto["version"],
                umbral_inferior=artefacto["umbral_inferior"],
                umbral_superior=artefacto["umbral_superior"],
            )
        except (KeyError, TypeError) as exc:
            raise ValueError("El artefacto del modelo tiene campos incompletos o inválidos.") from exc

    def analizar(self, texto: str) -> Resultado:
        fragmentos = fragmentos_markdown(texto)
        if not fragmentos:
            return Resultado("No identificado", self.version, None, None, "Texto insuficiente.")

        predicciones = self.modelo.predict_proba([fragmento.texto for fragmento in fragmentos])
        puntajes = [float(prediccion[1]) for prediccion in predicciones]
        if len(puntajes) != len(fragmentos) or any(
            not isfinite(puntaje) or not 0 <= puntaje <= 1 for puntaje in puntajes
        ):
            raise ValueError("El modelo devolvió puntajes inválidos.")
        indice = max(range(len(puntajes)), key=puntajes.__getitem__)
        puntaje = puntajes[indice]

        if puntaje >= self.umbral_superior:
            return Resultado("No seguro", self.version, puntaje, fragmentos[indice])
        if puntaje <= self.umbral_inferior:
            return Resultado("Sin indicios detectados", self.version, puntaje, None)
        return Resultado("No identificado", self.version, puntaje, fragmentos[indice])
