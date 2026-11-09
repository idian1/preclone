"""Consolida los índices de las fuentes sin copiar su contenido."""

import csv
import hashlib
from pathlib import Path


DATOS = Path(__file__).resolve().parent
CLASIFICACION = DATOS / "adicionales" / "clasificacion"
DESCARGAS = "adicionales/descargas"
PARQUET = f"{DESCARGAS}/primary.parquet"
BENCHMARK_URL = "https://huggingface.co/datasets/ProtectSkills/MaliciousSkillBench"
CAMPOS = (
    "id", "coleccion", "procedencia", "procedencia_origen", "fuente", "formato",
    "etiqueta_origen", "etiqueta_preclone", "estado_revision", "tipo_ataque",
    "archivo_texto", "selector_texto", "url_procedencia", "huella_texto",
    "grupo_fuente", "grupo_revision", "control_candidato", "lineas_evidencia", "particion",
)


def leer_csv(ruta):
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        return list(csv.DictReader(archivo))


def registro(**campos):
    return {"particion": "sin_asignar", **campos}


def filas_profesor():
    ruta = "profesor/escenarios_profesor.csv"
    for fila in leer_csv(DATOS / ruta):
        muestra = fila["sample_id"]
        huella = hashlib.sha256(fila["text"].encode("utf-8")).hexdigest()
        yield registro(
            id=f"profesor:{muestra}", coleccion="profesor", procedencia="escenario_derivado",
            fuente="Corpus del profesor", formato="escenario", etiqueta_origen=fila["label"],
            estado_revision="etiqueta_del_profesor", tipo_ataque=fila["attack_family"],
            archivo_texto=ruta, selector_texto=f"sample_id={muestra}",
            url_procedencia=fila["source_url"], huella_texto=f"sha256:{huella}",
            grupo_fuente=f"escenario:{fila['scenario_id']}",
        )


def filas_jsonl(clawhub, cloneguard, wild_por_linea, familia_por_linea):
    fuentes = (
        (clawhub, "ClawHub", "skills.jsonl", "skill_md",
         "https://huggingface.co/datasets/yoonholee/agent-skill-malware"),
        (cloneguard, "CloneGuard", "train.jsonl", "fragmento",
         "https://huggingface.co/datasets/prodnull/prompt-injection-repo-dataset"),
    )
    for filas, fuente, archivo, formato, url in fuentes:
        for fila in filas:
            linea = fila["fila_jsonl"]
            procedencia = "por_verificar"
            if fuente == "ClawHub":
                procedencia = "caso_real" if fila["etiqueta_origen"] == "malicious" else "documentacion_real"
            referencia = f"{archivo}:{linea}"
            evidencia_wild = wild_por_linea.get(referencia)
            yield registro(
                id=f"{fuente.lower()}:{fila['id_origen'] or linea}", coleccion="adicionales",
                procedencia=procedencia, fuente=fuente, formato=formato,
                procedencia_origen="WILD" if evidencia_wild else "",
                etiqueta_origen=fila["etiqueta_origen"], estado_revision=fila["estado"],
                tipo_ataque=fila["tipo_principal"], archivo_texto=f"{DESCARGAS}/{archivo}",
                selector_texto=f"linea={linea}",
                url_procedencia=evidencia_wild["url_markdown"] if evidencia_wild else url,
                huella_texto=f"sha256:{fila['sha256_texto']}",
                grupo_fuente=familia_por_linea.get(referencia, ""),
                lineas_evidencia=fila["lineas_evidencia"],
            )


def fila_parquet(identificador, familia, **campos):
    return registro(
        id=f"benchmark:{identificador}", formato="skill_md", archivo_texto=PARQUET,
        selector_texto=f"benchmark_id={identificador}",
        grupo_fuente=f"familia_benchmark:{familia}" if familia else "", **campos,
    )


def filas_adicionales_parquet(benchmark, wild_por_id):
    ids_originales = {fila["id_benchmark"] for fila in benchmark}
    for fila in benchmark:
        if fila["estado_preclone"] == "duplicado_local":
            continue
        identificador = fila["id_benchmark"]
        wild = wild_por_id.get(identificador)
        origen = fila["procedencia_origen"]
        es_caso_real = (origen == "wild" or wild is not None) and fila["estado_preclone"] != "demostracion_explicita"
        grupo = fila["grupo_preliminar"]
        yield fila_parquet(
            identificador, fila["familia_origen"], coleccion="adicionales",
            procedencia="caso_real" if es_caso_real else "por_verificar", procedencia_origen=origen,
            fuente=f"MaliciousSkillBench/{fila['fuente_principal']}", etiqueta_origen=fila["etiqueta_origen"],
            estado_revision=fila["estado_preclone"],
            tipo_ataque=fila["tipo_preclone"] or fila["categorias_origen"],
            url_procedencia=wild["url_markdown"] if wild else BENCHMARK_URL,
            huella_texto=f"sha256:{fila['sha256_texto']}",
            grupo_revision=f"patron:{grupo}" if grupo else "", lineas_evidencia=fila["lineas_evidencia"],
        )
    for identificador, fila in wild_por_id.items():
        if identificador in ids_originales or fila["estado_preclone"] == "ya_catalogado":
            continue
        yield fila_parquet(
            identificador, fila["familia_benchmark"], coleccion="adicionales",
            procedencia="caso_real", procedencia_origen=fila["procedencia_inventario"],
            fuente="MalSkillBench via MaliciousSkillBench", etiqueta_origen="1",
            estado_revision=fila["estado_preclone"], tipo_ataque=fila["tipo_preclone"],
            url_procedencia=fila["url_markdown"], huella_texto=f"git-blob:{fila['sha_git']}",
            lineas_evidencia=fila["lineas_evidencia"],
        )


def filas_laboratorio(laboratorio, revision):
    por_id = {fila["id_benchmark"]: fila for fila in revision}
    if len(por_id) != len(revision) or set(por_id) != {fila["id_benchmark"] for fila in laboratorio}:
        raise ValueError("Los identificadores de laboratorio y revisión no coinciden")
    for fila in laboratorio:
        identificador = fila["id_benchmark"]
        nota = por_id[identificador]
        nombre = nota["nombre_declarado_repetido"]
        estado = nota["estado_revision"]
        yield fila_parquet(
            identificador, fila["familia_estructural_benchmark"], coleccion="laboratorio",
            procedencia=fila["procedencia_preclone"], procedencia_origen=fila["procedencia_benchmark"],
            fuente=fila["fuente"], etiqueta_origen=fila["etiqueta_benchmark"],
            etiqueta_preclone="1" if estado == "evidencia_textual_revisada" else "",
            estado_revision=estado, tipo_ataque=fila["categorias_benchmark"],
            url_procedencia=fila["url_fuente"], huella_texto=f"sha256:{fila['sha256_texto']}",
            grupo_revision=f"nombre_declarado:{nombre}" if nombre else "",
            control_candidato=nota["id_control_candidato"], lineas_evidencia=nota["lineas_evidencia"],
        )


def generar():
    clawhub = leer_csv(CLASIFICACION / "clawhub.csv")
    cloneguard = leer_csv(CLASIFICACION / "cloneguard.csv")
    benchmark = leer_csv(CLASIFICACION / "maliciousskillbench.csv")
    wild = leer_csv(CLASIFICACION / "malskillbench_wild.csv")
    laboratorio = leer_csv(CLASIFICACION / "laboratorio.csv")
    revision = leer_csv(CLASIFICACION / "revision_laboratorio.csv")
    wild_por_id = {}
    wild_por_linea = {}
    for fila in wild:
        if fila["id_benchmark"]:
            wild_por_id.setdefault(fila["id_benchmark"], fila)
        for referencia in fila["coincidencias_previas"].split("|"):
            if referencia.startswith(("skills.jsonl:", "train.jsonl:")):
                wild_por_linea.setdefault(referencia, fila)
    familia_por_linea = {}
    referencias = {f"skills.jsonl:{fila['fila_jsonl']}" for fila in clawhub}
    for fila in benchmark:
        if fila["estado_preclone"] == "duplicado_local":
            referencia = fila["coincidencias_locales"]
            if referencia not in referencias:
                raise ValueError(f"El duplicado no tiene una fila canónica conocida: {referencia}")
            familia_por_linea[referencia] = f"familia_benchmark:{fila['familia_origen']}"
    filas = [
        *filas_profesor(),
        *filas_laboratorio(laboratorio, revision),
        *filas_jsonl(clawhub, cloneguard, wild_por_linea, familia_por_linea),
        *filas_adicionales_parquet(benchmark, wild_por_id),
    ]
    if len({fila["id"] for fila in filas}) != len(filas):
        raise ValueError("El catálogo contiene identificadores repetidos")
    destino = DATOS / "catalogo.csv"
    temporal = destino.with_suffix(".csv.tmp")
    with temporal.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=CAMPOS, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(filas)
    temporal.replace(destino)
    print(f"{len(filas)} entradas en {destino}")


if __name__ == "__main__":
    generar()
