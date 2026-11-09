"""Entrena y evalúa el detector con Markdown externo y escenarios."""

import argparse
from collections import Counter
import csv
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory

import duckdb
import joblib
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, make_pipeline

from .detector import Detector, FORMATO_MODELO, fragmentos_markdown
from .entrenar import huella_normalizada, leer_csv, particionar, verificar_huella


VERSION = "markdown-mixto-v2"
VERSION_AMPLIADA = "markdown-mixto-v3"
FORMATO_PARQUET = "adicionales/descargas/primary.parquet"
PATRONES = {
    "mandatory setup": "entrenamiento",
    "environment probe": "entrenamiento",
    "activation condition": "entrenamiento",
    "pre-flight guard": "validacion",
    "gated side-effect step": "validacion",
    "if the user says": "prueba",
}


@dataclass(frozen=True)
class Muestra:
    id: str
    texto: str
    etiqueta: int
    fuente: str
    grupo: str
    familia: str = ""
    evidencia: str = ""

    @property
    def nombre(self):
        encabezado = self.texto.lstrip("\ufeff \n\r").splitlines()[:16]
        for linea in encabezado:
            coincidencia = re.fullmatch(r"name:\s*([\w'\" -]{2,95})", linea.strip())
            if coincidencia:
                return re.sub(r"[-_\s]+", "-", coincidencia[1].strip("'\" ").casefold())
        return ""


def leer_parquet(datos):
    ruta = datos / FORMATO_PARQUET
    registro = datos / "adicionales/procedencia_maliciousskillbench.json"
    esperado = json.loads(registro.read_text(encoding="utf-8"))["sha256"]
    if hashlib.sha256(ruta.read_bytes()).hexdigest() != esperado:
        raise ValueError("La huella del Parquet no coincide con su registro de procedencia.")
    with duckdb.connect(config={"autoload_known_extensions": "false", "autoinstall_known_extensions": "false"}) as db:
        filas = db.execute(
            "SELECT benchmark_id, skill_text, label, source_id, structural_family_id, provenance "
            "FROM read_parquet(?) WHERE text_available AND NOT text_redacted "
            "AND release_status = 'FULL_TEXT' AND length(skill_text) <= 65000 ORDER BY benchmark_id",
            [str(ruta)],
        ).fetchall()
    return {
        identificador: Muestra(f"benchmark:{identificador}", texto, int(etiqueta), fuente,
                              f"benchmark:{identificador}", familia or "")
        for identificador, texto, etiqueta, fuente, familia, _ in filas
    }, {fila[0]: fila[5] for fila in filas}


def intervalos(valor):
    for intervalo in re.split(r"[,;|]", valor):
        if intervalo.strip():
            extremos = [int(n) for n in re.split(r"[-–]", intervalo)]
            yield extremos[0], extremos[-1]


def desde_catalogo(fila, texto, etiqueta):
    if not verificar_huella(texto, fila["huella_texto"]):
        raise ValueError(f"No coincide la huella de {fila['id']}.")
    grupo = fila["grupo_fuente"] or fila["id"]
    familia = grupo.split(":", 1)[1] if grupo.startswith("familia_benchmark:") else ""
    return Muestra(fila["id"], texto, etiqueta, fila["fuente"], grupo, familia, fila["lineas_evidencia"])


def leer_clawhub(datos, catalogo):
    ruta = datos / "adicionales/descargas/skills.jsonl"
    with ruta.open(encoding="utf-8-sig") as archivo:
        filas = {n: json.loads(linea) for n, linea in enumerate(archivo, 1) if linea.strip()}
    muestras = []
    for fila in catalogo:
        if fila["fuente"] != "ClawHub" or fila["estado_revision"] not in (
            "candidato_prioritario", "etiqueta_benigna_de_origen",
        ):
            continue
        original = filas[int(fila["selector_texto"].split("=", 1)[1])]
        if original["label"] != fila["etiqueta_origen"]:
            raise ValueError(f"No coincide la etiqueta de {fila['id']}.")
        etiqueta = int(original["label"] == "malicious")
        muestras.append(desde_catalogo(fila, original["content"], etiqueta))
    return muestras


def leer_cloneguard(datos, catalogo):
    ruta = datos / "adicionales/descargas/train.jsonl"
    with ruta.open(encoding="utf-8-sig") as archivo:
        filas = {n: json.loads(linea) for n, linea in enumerate(archivo, 1) if linea.strip()}
    muestras = []
    for fila in catalogo:
        if fila["fuente"] != "CloneGuard" or fila["estado_revision"] not in (
            "candidato_prioritario", "control_candidato",
        ):
            continue
        original = filas[int(fila["selector_texto"].split("=", 1)[1])]
        if str(original["label"]) != fila["etiqueta_origen"]:
            raise ValueError(f"No coincide la etiqueta de {fila['id']}.")
        muestras.append(desde_catalogo(fila, original["text"], int(original["label"])))
    return muestras


def pares_laboratorio(datos, parquet):
    revision = leer_csv(datos / "adicionales/clasificacion/revision_laboratorio.csv")
    pares = {nombre: [] for nombre in ("entrenamiento", "validacion", "prueba")}
    vistos = set()
    for fila in revision:
        if fila["estado_revision"] == "evidencia_textual_revisada":
            for clave in (fila["id_benchmark"], fila["id_control_candidato"]):
                if clave in parquet and parquet[clave].nombre:
                    vistos.add(parquet[clave].nombre)
    for fila in revision:
        if not fila["patron_automatico"] or float(fila["similitud_lineas"] or 0) < 0.95:
            continue
        positiva = parquet[fila["id_benchmark"]]
        negativa = parquet[fila["id_control_candidato"]]
        if (positiva.etiqueta, negativa.etiqueta) != (1, 0) or not positiva.nombre:
            raise ValueError(f"Par de laboratorio inválido para {positiva.id}.")
        inicio, fin = next(intervalos(fila["lineas_evidencia"]))
        bloque = "\n".join(positiva.texto.splitlines()[inicio - 1:fin]).casefold()
        destino = next((particion for patron, particion in PATRONES.items() if patron in bloque), None)
        if destino is None:
            continue
        if destino == "prueba" and (positiva.nombre in vistos or negativa.nombre in vistos):
            continue
        grupo = f"skill:{positiva.nombre}"
        pares[destino].append((
            Muestra(positiva.id, positiva.texto, 1, positiva.fuente, grupo, positiva.familia, fila["lineas_evidencia"]),
            Muestra(negativa.id, negativa.texto, 0, negativa.fuente, grupo),
        ))
    return pares


def claves(muestras):
    nombres, familias, huellas = set(), set(), set()
    for muestra in muestras:
        if muestra.nombre:
            nombres.add(muestra.nombre)
        if muestra.familia:
            familias.add(muestra.familia)
        huellas.add(huella_normalizada(muestra.texto))
    return nombres, familias, huellas


def separadas(muestras, bloqueadas):
    nombres, familias, huellas = bloqueadas
    return all(
        muestra.nombre not in nombres and muestra.familia not in familias
        and huella_normalizada(muestra.texto) not in huellas for muestra in muestras
    )


def particionar_skillfortify(muestras):
    familias_prueba = {"FAMILY_4528", "FAMILY_4532", "FAMILY_4535", "FAMILY_4536", "FAMILY_4541"}
    familias_validacion = {"FAMILY_4524", "FAMILY_4533", "FAMILY_4540"}
    grupos = {"prueba": [], "validacion": [], "entrenamiento": []}
    for muestra in muestras:
        if muestra.etiqueta:
            if muestra.familia in familias_prueba:
                grupos["prueba"].append(muestra)
            elif muestra.familia in familias_validacion:
                grupos["validacion"].append(muestra)
            else:
                grupos["entrenamiento"].append(muestra)
    orden = sorted((muestra for muestra in muestras if not muestra.etiqueta),
                   key=lambda muestra: hashlib.sha256(muestra.id.encode()).hexdigest())
    destinos = {m.nombre: destino for destino, grupo in reversed(grupos.items()) for m in grupo if m.nombre}
    for muestra in orden:
        if muestra.nombre in destinos:
            grupos[destinos[muestra.nombre]].append(muestra)
            continue
        destino = next((d for d in ("prueba", "validacion")
                        if sum(not m.etiqueta for m in grupos[d]) < sum(m.etiqueta for m in grupos[d])),
                       "entrenamiento")
        grupos[destino].append(muestra)
        if muestra.nombre:
            destinos[muestra.nombre] = destino
    return grupos


def preparar_datos(datos, ampliar=False):
    catalogo = leer_csv(datos / "catalogo.csv")
    parquet, procedencias = leer_parquet(datos)
    escenarios = particionar(leer_csv(datos / "profesor/escenarios_profesor.csv"))
    profesor = {
        nombre: [Muestra(f"profesor:{f['sample_id']}", f["text"], int(f["label"]), "profesor", f["scenario_id"])
                 for f in filas]
        for nombre, filas in escenarios.items()
    }
    clawhub = leer_clawhub(datos, catalogo)
    pares = pares_laboratorio(datos, parquet)
    # Se protegen primero las muestras de prueba, luego la validación.
    prueba_lab = [muestra for par in pares["prueba"] for muestra in par]
    sinteticas = [muestra for muestra in parquet.values() if muestra.fuente == "SRC012"]
    sinteticas_partidas = particionar_skillfortify(sinteticas) if ampliar else {
        "prueba": sinteticas, "validacion": [], "entrenamiento": [],
    }
    prueba_sintetica = sinteticas_partidas["prueba"]
    casos_reales = []
    for fila in catalogo:
        if fila["procedencia"] == "caso_real" and fila["estado_revision"] == "candidato_prioritario" and fila["archivo_texto"] == FORMATO_PARQUET:
            referencia = fila["selector_texto"].split("=", 1)[1]
            if referencia in parquet:
                casos_reales.append(desde_catalogo(fila, parquet[referencia].texto, 1))
    bloqueadas = claves(prueba_lab + prueba_sintetica + casos_reales)
    validacion = [muestra for par in pares["validacion"] if separadas(par, bloqueadas) for muestra in par]
    validacion += [m for m in sinteticas_partidas["validacion"] if separadas((m,), bloqueadas)]
    congeladas = claves(prueba_lab + prueba_sintetica + casos_reales + validacion)
    entrenamiento = [
        muestra for par in pares["entrenamiento"] if separadas(par, congeladas) for muestra in par
    ]
    entrenamiento += [muestra for muestra in clawhub if separadas((muestra,), congeladas)]
    entrenamiento += [m for m in sinteticas_partidas["entrenamiento"] if separadas((m,), congeladas)]
    if ampliar:
        entrenamiento += [m for m in leer_cloneguard(datos, catalogo) if separadas((m,), congeladas)]
    entrenamiento += profesor["entrenamiento"]
    ocupadas = claves(entrenamiento + validacion + prueba_lab + prueba_sintetica + casos_reales)
    controles = [
        muestra for clave, muestra in parquet.items()
        if muestra.fuente == "SRC011" and muestra.etiqueta == 0 and procedencias[clave] == "wild"
        and separadas((muestra,), ocupadas)
    ]
    # Selección estable por ID, independiente del texto del modelo y su puntaje.
    controles.sort(key=lambda muestra: hashlib.sha256(muestra.id.encode()).hexdigest())
    pruebas = {
        "laboratorio_pareado": prueba_lab,
        "skillfortify_familias_reservadas" if ampliar else "laboratorio_fuente_reservada": prueba_sintetica,
        "transferencia_real": casos_reales + controles[:100],
        "escenarios_profesor": profesor["prueba"],
    }
    if ampliar:
        usadas = claves(entrenamiento + validacion)
        pruebas["agenttrap_fuente_reservada"] = [
            m for m in parquet.values() if m.fuente == "SRC006"
            and separadas((m,), usadas)
        ]
    externos = [m for nombre, grupo in pruebas.items() if nombre != "escenarios_profesor" for m in grupo]
    if not separadas(entrenamiento, claves(validacion + externos)) or not separadas(validacion, claves(externos)):
        raise ValueError("Hay nombres, familias o textos compartidos entre las particiones.")
    for grupo in (entrenamiento, validacion, *pruebas.values()):
        if {muestra.etiqueta for muestra in grupo} != {0, 1}:
            raise ValueError("Todas las particiones deben contener ambas clases.")
    return entrenamiento, validacion, pruebas


def ventanas_entrenamiento(muestras, peso_profesor, peso_skillfortify):
    textos, clases, pesos = [], [], []
    for muestra in muestras:
        ventanas = fragmentos_markdown(muestra.texto)
        evidencia = list(intervalos(muestra.evidencia))
        if muestra.etiqueta and evidencia:
            ventanas = [v for v in ventanas if any(v.linea_inicio <= fin and v.linea_fin >= inicio
                                                   for inicio, fin in evidencia)]
        if not ventanas:
            raise ValueError(f"La evidencia no se pudo ubicar en las ventanas de {muestra.id}.")
        peso = {"profesor": peso_profesor, "SRC012": peso_skillfortify}.get(muestra.fuente, 1.0)
        textos.extend(ventana.texto for ventana in ventanas)
        clases.extend([muestra.etiqueta] * len(ventanas))
        pesos.extend([peso / len(ventanas)] * len(ventanas))
    return textos, clases, pesos


def puntajes(modelo, muestras):
    por_doc = [fragmentos_markdown(muestra.texto) for muestra in muestras]
    textos = [ventana.texto for ventanas in por_doc for ventana in ventanas]
    predicciones = modelo.predict_proba(textos)[:, 1]
    posicion = 0
    salida = []
    for ventanas in por_doc:
        siguiente = posicion + len(ventanas)
        salida.append(float(max(predicciones[posicion:siguiente])) if ventanas else -1.0)
        posicion = siguiente
    return np.array(salida)


def resumir(etiquetas, valores, inferior, superior):
    aciertos, resumen = [], {}
    for etiqueta in (0, 1):
        grupo = valores[etiquetas == etiqueta]
        alarmas = int(np.sum(grupo >= superior))
        benignos = int(np.sum((grupo >= 0) & (grupo <= inferior)))
        total = len(grupo)
        aciertos.append((alarmas if etiqueta else benignos) / total)
        resumen[str(etiqueta)] = {"alerta": alarmas, "sin_indicios": benignos,
                                  "abstencion": total - alarmas - benignos, "total": total}
    return {"exactitud_balanceada": sum(aciertos) / 2, "deteccion": aciertos[1],
            "benignos_correctos": aciertos[0], "por_clase": resumen}


def calibrar(valores, etiquetas, segmentos):
    mejor = None
    for centro in np.arange(0.05, 0.951, 0.005):
        for margen in (0.005, 0.02):
            inferior, superior = float(centro - margen), float(centro + margen)
            r = resumir(etiquetas, valores, inferior, superior)
            parciales = [resumir(etiquetas[s], valores[s], inferior, superior) for s in segmentos]
            promedio = sum(m["exactitud_balanceada"] for m in parciales) / len(parciales)
            minimo = min(min(m["deteccion"], m["benignos_correctos"]) for m in parciales)
            rango = (promedio, minimo, margen)
            if mejor is None or rango > mejor[0]:
                mejor = rango, inferior, superior, r
    return mejor


def ajustar(entrenamiento, validacion, ampliar):
    etiquetas = np.array([m.etiqueta for m in validacion])
    skillfortify = np.array([m.fuente == "SRC012" for m in validacion])
    segmentos = [skillfortify, ~skillfortify] if ampliar else [~skillfortify]
    if any(set(etiquetas[segmento]) != {0, 1} for segmento in segmentos):
        raise ValueError("Cada segmento de validación debe contener las dos clases.")
    mejor = None
    candidatos = []
    pesos_dominio = ((0.15, 1.0), (0.15, 3.0), (0.45, 3.0)) if ampliar else ((0.15, 1.0), (0.45, 1.0))
    for peso_profesor, peso_skillfortify in pesos_dominio:
        textos, clases, pesos = ventanas_entrenamiento(entrenamiento, peso_profesor, peso_skillfortify)
        for caracteres in (False, True):
            for regularizacion in (1.0, 6.0):
                palabras = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
                vectorizador = palabras
                if caracteres:
                    vectorizador = FeatureUnion([
                        ("palabras", palabras),
                        ("caracteres", TfidfVectorizer(analyzer="char", ngram_range=(3, 5), min_df=3,
                                                       max_features=45000, sublinear_tf=True)),
                    ])
                modelo = make_pipeline(vectorizador, LogisticRegression(
                    solver="liblinear", C=regularizacion, max_iter=1000, random_state=42,
                ))
                modelo.fit(textos, clases, logisticregression__sample_weight=pesos)
                rango, inferior, superior, resumen = calibrar(puntajes(modelo, validacion), etiquetas, segmentos)
                candidato = {"peso_profesor": peso_profesor, "caracteres": caracteres,
                             "peso_skillfortify": peso_skillfortify, "C": regularizacion,
                             "validacion_promedio_por_dominio": rango[0], "validacion": resumen}
                candidatos.append(candidato)
                if mejor is None or rango > mejor[0]:
                    mejor = rango, modelo, inferior, superior, candidato
    return mejor, candidatos


def ejecutar(datos, salida, ampliar=False):
    version = VERSION_AMPLIADA if ampliar else VERSION
    entrenamiento, validacion, pruebas = preparar_datos(datos, ampliar)
    (_, modelo, inferior, superior, elegido), candidatos = ajustar(entrenamiento, validacion, ampliar)
    evaluaciones = {}
    etiquetas_externas, puntajes_externos = [], []
    for nombre, grupo in pruebas.items():
        etiquetas = np.array([m.etiqueta for m in grupo])
        valores = puntajes(modelo, grupo)
        evaluaciones[nombre] = resumir(etiquetas, valores, inferior, superior)
        if nombre != "escenarios_profesor":
            etiquetas_externas.append(etiquetas)
            puntajes_externos.append(valores)
    total_externo = resumir(
        np.concatenate(etiquetas_externas), np.concatenate(puntajes_externos), inferior, superior,
    )
    modelo_exportado = {"formato": FORMATO_MODELO, "version": version, "modelo": modelo,
                         "umbral_inferior": inferior, "umbral_superior": superior}
    informe = {
        "version": version, "scikit_learn": sklearn.__version__,
        "umbrales": {"inferior": inferior, "superior": superior}, "configuracion": elegido,
        "candidatos": candidatos,
        "entrenamiento_por_fuente_y_clase": dict(Counter(f"{m.fuente}/{m.etiqueta}" for m in entrenamiento)),
        "pruebas": evaluaciones, "total_externo": total_externo,
    }
    salida.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=salida) as carpeta:
        temporal = Path(carpeta)
        joblib.dump(modelo_exportado, temporal / "modelo.joblib", compress=3)
        detector = Detector.cargar(temporal / "modelo.joblib")
        for nombre, grupo in pruebas.items():
            etiquetas = np.array([m.etiqueta for m in grupo])
            real = [detector.analizar(m.texto).puntaje for m in grupo]
            reporte = resumir(etiquetas, np.array([p if p is not None else -1 for p in real]), inferior, superior)
            assert reporte == evaluaciones[nombre]
        informe["sha256_modelo"] = hashlib.sha256((temporal / "modelo.joblib").read_bytes()).hexdigest()
        (temporal / "evaluacion.json").write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        with (temporal / "particiones.csv").open("w", encoding="utf-8", newline="") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(("id", "particion", "fuente", "grupo", "etiqueta"))
            for nombre, grupo in {"entrenamiento": entrenamiento, "validacion": validacion, **pruebas}.items():
                escritor.writerows((m.id, nombre, m.fuente, m.grupo, m.etiqueta) for m in grupo)
        for nombre in ("particiones.csv", "evaluacion.json", "modelo.joblib"):
            (temporal / nombre).replace(salida / nombre)
    print(json.dumps({"version": version, "validacion": elegido, "pruebas": evaluaciones,
                      "total_externo": total_externo}, ensure_ascii=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datos", type=Path, default=Path("datos"))
    parser.add_argument("--salida", type=Path)
    parser.add_argument("--ampliar", action="store_true")
    argumentos = parser.parse_args()
    salida = argumentos.salida or Path("artefactos/v3" if argumentos.ampliar else "artefactos/v2")
    ejecutar(argumentos.datos, salida, argumentos.ampliar)


if __name__ == "__main__":
    main()
