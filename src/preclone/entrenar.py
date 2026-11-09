"""Entrena la línea base y registra sus particiones y resultados."""

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import random
from tempfile import TemporaryDirectory
import unicodedata

import joblib
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from .detector import Detector, FORMATO_MODELO, fragmentos_markdown


VERSION = "base-escenarios-v1"
SEMILLA = 42
ESTADOS = ("No seguro", "Sin indicios detectados", "No identificado")


def leer_csv(ruta):
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        return list(csv.DictReader(archivo))


def particionar(filas):
    grupos = sorted({fila["scenario_id"] for fila in filas})
    if len(grupos) != 50:
        raise ValueError("Esta versión requiere los 50 escenarios del corpus de referencia.")
    random.Random(SEMILLA).shuffle(grupos)
    return {
        nombre: [fila for fila in filas if fila["scenario_id"] in ids]
        for nombre, ids in (
            ("entrenamiento", set(grupos[:35])),
            ("validacion", set(grupos[35:43])),
            ("prueba", set(grupos[43:])),
        )
    }


def ajustar_modelo(filas):
    textos, etiquetas, pesos = [], [], []
    for fila in filas:
        fragmentos = fragmentos_markdown(fila["text"])
        textos.extend(fragmento.texto for fragmento in fragmentos)
        etiquetas.extend([int(fila["label"])] * len(fragmentos))
        if fragmentos:
            pesos.extend([1 / len(fragmentos)] * len(fragmentos))
    modelo = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
        LogisticRegression(max_iter=1000, random_state=SEMILLA),
    )
    return modelo.fit(textos, etiquetas, logisticregression__sample_weight=pesos)


def calibrar(modelo, filas):
    detector = Detector(modelo, version=VERSION, umbral_inferior=0, umbral_superior=1)
    puntajes = {0: [], 1: []}
    for fila in filas:
        puntaje = detector.analizar(fila["text"]).puntaje
        if puntaje is not None:
            puntajes[int(fila["label"])].append(puntaje)
    mayor_benigno = max(puntajes[0])
    menor_malicioso = min(puntajes[1])
    if mayor_benigno < menor_malicioso:
        tercio = (menor_malicioso - mayor_benigno) / 3
        return mayor_benigno + tercio, menor_malicioso - tercio
    return math.nextafter(menor_malicioso, 0), math.nextafter(mayor_benigno, 1)


def evaluar(detector, filas):
    resultados = {0: Counter(), 1: Counter()}
    for fila in filas:
        estado = detector.analizar(fila["text"]).estado
        resultados[int(fila["label"])][estado] += 1
    return {
        str(clase): {estado: conteos[estado] for estado in ESTADOS}
        for clase, conteos in resultados.items() if conteos
    }


def sha256(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def verificar_huella(texto, huella):
    tipo, esperado = huella.split(":", 1)
    if tipo == "sha256":
        return sha256(texto) == esperado
    if tipo != "git-blob":
        return False
    lf = texto.replace("\r\n", "\n")
    for variante in (texto, lf, lf.replace("\n", "\r\n")):
        bytes_texto = variante.encode("utf-8")
        encabezado = f"blob {len(bytes_texto)}\0".encode("ascii")
        if hashlib.sha1(encabezado + bytes_texto).hexdigest() == esperado:
            return True
    return False


def huella_normalizada(texto):
    lf = unicodedata.normalize("NFC", texto.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n"))
    return sha256("\n".join(linea.rstrip(" \t") for linea in lf.split("\n")).strip())


def pruebas_externas(datos):
    import duckdb

    catalogo = leer_csv(datos / "catalogo.csv")
    seleccion = {
        "laboratorio_confirmado": [
            fila for fila in catalogo if fila["estado_revision"] == "evidencia_textual_revisada"
        ],
        "casos_reales_prioritarios": [
            fila for fila in catalogo if fila["procedencia"] == "caso_real"
            and fila["estado_revision"] == "candidato_prioritario"
        ],
        "documentacion_real_etiqueta_fuente": [
            fila for fila in catalogo if fila["procedencia"] == "documentacion_real"
            and fila["etiqueta_origen"] == "benign"
        ],
    }
    carpeta = datos / "adicionales" / "descargas"
    ids_control = {fila["control_candidato"] for fila in seleccion["laboratorio_confirmado"]
                   if fila["control_candidato"]}
    ids_parquet = ids_control | {
        fila["selector_texto"].split("=", 1)[1] for filas in seleccion.values() for fila in filas
        if fila["archivo_texto"].endswith(".parquet")
    }
    with duckdb.connect(config={"autoload_known_extensions": "false", "autoinstall_known_extensions": "false"}) as db:
        parquet = {
            id_fila: (texto, etiqueta)
            for id_fila, texto, etiqueta in db.execute(
                "SELECT benchmark_id, skill_text, label FROM read_parquet(?) "
                "WHERE benchmark_id IN (SELECT unnest(?))",
                [str(carpeta / "primary.parquet"), sorted(ids_parquet)],
            ).fetchall()
        }
    with (carpeta / "skills.jsonl").open(encoding="utf-8-sig") as archivo:
        clawhub = {n: json.loads(linea)["content"] for n, linea in enumerate(archivo, 1) if linea.strip()}
    salida = {}
    for nombre, filas in seleccion.items():
        etiqueta = 0 if nombre == "documentacion_real_etiqueta_fuente" else 1
        salida[nombre] = []
        for fila in filas:
            clave = fila["selector_texto"].split("=", 1)[1]
            texto = parquet[clave][0] if fila["archivo_texto"].endswith(".parquet") else clawhub[int(clave)]
            if not verificar_huella(texto, fila["huella_texto"]):
                raise ValueError(f"La huella del texto no coincide para {fila['id']}.")
            salida[nombre].append({"id": fila["id"], "text": texto, "label": etiqueta})
    controles = []
    for clave in sorted(ids_control):
        texto, etiqueta = parquet[clave]
        if str(etiqueta) != "0":
            raise ValueError(f"El control {clave} debe tener etiqueta benigna en el benchmark.")
        controles.append({"id": f"benchmark:{clave}", "text": texto, "label": 0})
    salida["controles_pareados_etiqueta_fuente"] = controles
    return salida


def entrenar(datos, salida, evaluar_adicionales):
    ruta_profesor = datos / "profesor" / "escenarios_profesor.csv"
    huella_profesor = hashlib.sha256(ruta_profesor.read_bytes()).hexdigest()
    procedencia = json.loads(ruta_profesor.with_name("procedencia.json").read_text(encoding="utf-8-sig"))
    if huella_profesor != procedencia["sha256"]:
        raise ValueError("El CSV del profesor difiere de la huella de procedencia.")
    filas = leer_csv(ruta_profesor)
    conjuntos = particionar(filas)
    externas = pruebas_externas(datos) if evaluar_adicionales else {}
    huellas_profesor = {huella_normalizada(fila["text"]) for fila in filas}
    if any(huella_normalizada(fila["text"]) in huellas_profesor for grupo in externas.values() for fila in grupo):
        raise ValueError("Hay textos repetidos entre el corpus del profesor y la prueba externa.")

    modelo = ajustar_modelo(conjuntos["entrenamiento"])
    inferior, superior = calibrar(modelo, conjuntos["validacion"])
    detector = Detector(modelo, version=VERSION, umbral_inferior=inferior, umbral_superior=superior)
    artefacto = {
        "formato": FORMATO_MODELO, "version": VERSION, "modelo": modelo,
        "umbral_inferior": inferior, "umbral_superior": superior,
    }
    informe = {
        "version": VERSION, "semilla": SEMILLA, "sha256_corpus_profesor": huella_profesor,
        "scikit_learn": sklearn.__version__, "joblib": joblib.__version__,
        "umbrales": {"inferior": inferior, "superior": superior},
        "particiones_profesor": {nombre: len(grupo) for nombre, grupo in conjuntos.items()},
        "validacion_profesor": evaluar(detector, conjuntos["validacion"]),
        "prueba_profesor": evaluar(detector, conjuntos["prueba"]),
        "pruebas_externas": {nombre: evaluar(detector, grupo) for nombre, grupo in externas.items()},
    }
    salida.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=salida) as carpeta:
        temporal = Path(carpeta)
        ruta_modelo = temporal / "modelo.joblib"
        joblib.dump(artefacto, ruta_modelo, compress=3)
        Detector.cargar(ruta_modelo)
        informe["sha256_modelo"] = hashlib.sha256(ruta_modelo.read_bytes()).hexdigest()
        (temporal / "evaluacion.json").write_text(
            json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        with (temporal / "particiones.csv").open("w", encoding="utf-8", newline="") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(("id", "particion", "escenario", "etiqueta"))
            for nombre, grupo in conjuntos.items():
                for fila in grupo:
                    escritor.writerow((f"profesor:{fila['sample_id']}", nombre, fila["scenario_id"], fila["label"]))
            for nombre, grupo in externas.items():
                for fila in grupo:
                    escritor.writerow((fila["id"], f"prueba_externa/{nombre}", "", fila["label"]))
        for nombre in ("particiones.csv", "evaluacion.json", "modelo.joblib"):
            (temporal / nombre).replace(salida / nombre)
    print(json.dumps(informe, ensure_ascii=True, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datos", type=Path, default=Path("datos"))
    parser.add_argument("--salida", type=Path, default=Path("artefactos"))
    parser.add_argument("--evaluar-adicionales", action="store_true")
    argumentos = parser.parse_args()
    entrenar(argumentos.datos, argumentos.salida, argumentos.evaluar_adicionales)


if __name__ == "__main__":
    main()
