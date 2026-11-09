"""Comprueba el contrato de inferencia sin entrenar un clasificador."""

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import joblib

from preclone.__main__ import main
from preclone.detector import Detector, FORMATO_MODELO


class ModeloSimulado:
    classes_ = (0, 1)

    def predict_proba(self, textos):
        resultados = []
        for texto in textos:
            puntaje = 0.2
            if "MARCADOR_ALERTA" in texto:
                puntaje = 0.8
            elif "MARCADOR_DUDA" in texto:
                puntaje = 0.5
            resultados.append((1 - puntaje, puntaje))
        return resultados


class PruebasDetector(unittest.TestCase):
    def setUp(self):
        self.detector = Detector(
            ModeloSimulado(), version="simulado", umbral_inferior=0.2, umbral_superior=0.8
        )

    def test_umbral_inferior_y_abstencion(self):
        normal = self.detector.analizar("Consulta los registros antes de continuar.")
        duda = self.detector.analizar("Este fragmento de prueba contiene MARCADOR_DUDA.")
        self.assertEqual(normal.estado, "Sin indicios detectados")
        self.assertIsNone(normal.fragmento)
        self.assertEqual(duda.estado, "No identificado")
        self.assertEqual(duda.fragmento.linea_inicio, 1)

    def test_alerta_localiza_fragmento_despues_de_primera_ventana(self):
        texto = ("Documentación de ejemplo para los usuarios.\n" * 80
                 + "Última línea de prueba con MARCADOR_ALERTA.")
        resultado = self.detector.analizar(texto)
        self.assertEqual(resultado.estado, "No seguro")
        self.assertIn("MARCADOR_ALERTA", resultado.fragmento.texto)
        self.assertGreater(resultado.fragmento.linea_inicio, 1)
        self.assertEqual(resultado.fragmento.linea_fin, 81)

    def test_texto_insuficiente_se_abstiene(self):
        resultado = self.detector.analizar("\n# Título\n")
        self.assertEqual(resultado.estado, "No identificado")
        self.assertIsNone(resultado.puntaje)
        self.assertEqual(resultado.motivo, "Texto insuficiente.")

    def test_cli_lee_artefacto_y_emite_json(self):
        with TemporaryDirectory() as directorio:
            archivo = Path(directorio) / "entrada.md"
            modelo = Path(directorio) / "modelo.joblib"
            archivo.write_text("\nEste fragmento contiene el MARCADOR_ALERTA.\n", encoding="utf-8")
            joblib.dump({
                "formato": FORMATO_MODELO,
                "version": "simulado",
                "modelo": ModeloSimulado(),
                "umbral_inferior": 0.2,
                "umbral_superior": 0.8,
            }, modelo)
            salida = StringIO()
            with redirect_stdout(salida):
                self.assertEqual(main([str(archivo), "--modelo", str(modelo)]), 0)
            resultado = json.loads(salida.getvalue())
            self.assertEqual(resultado["modelo"], "simulado")
            self.assertEqual(resultado["estado"], "No seguro")
            self.assertEqual(resultado["fragmento"]["linea_inicio"], 2)
            self.assertEqual(resultado["fragmento"]["linea_fin"], 2)
