"""Prueba la barrera de aprobación con un repositorio Git local."""

from importlib.util import find_spec
from pathlib import Path
from shutil import copytree, which
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

if not find_spec("mcp") or not which("git"):
    raise unittest.SkipTest("Instala el extra MCP y Git para estas pruebas.")

from preclone.detector import Detector
from preclone.mcp import proteger
from preclone.repositorio import git, verificar_commit


class ModeloPrueba:
    classes_ = (0, 1)

    def predict_proba(self, textos):
        return [(0.1, 0.9) for _ in textos]


class PruebasMcp(unittest.TestCase):
    def setUp(self):
        temporal = TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        base = Path(temporal.name)
        self.origen = base / "origen"
        self.origen.mkdir()
        self.destinos = base / "clones"
        git(self.origen, "init", "--template=", "--object-format=sha1")
        git(self.origen, "config", "user.name", "Pruebas")
        git(self.origen, "config", "user.email", "pruebas@example.invalid")
        (self.origen / "README.md").write_text("Texto adversarial del caso de prueba.", encoding="utf-8")
        self.commit = self.guardar()
        self.detector = Detector(ModeloPrueba(), version="prueba", umbral_inferior=0.2, umbral_superior=0.8)

    def guardar(self):
        git(self.origen, "add", "README.md")
        git(self.origen, "commit", "-m", "Prueba")
        return verificar_commit(self.origen, "HEAD")

    def obtener_local(self, revision, *_):
        self.revision = revision
        copytree(self.origen / ".git", revision / ".git")
        return self.commit

    def operacion(self, confirmar):
        with patch("preclone.mcp.obtener_commit", self.obtener_local), patch("preclone.mcp.confirmar", confirmar):
            return proteger(self.detector, self.destinos, "prueba/ejemplo", None, clonar=True)

    def test_cancelacion_y_checkout_del_commit_revisado(self):
        # Simula que avanzó la rama después de fijar la referencia de la revisión.
        (self.origen / "README.md").write_text("Contenido distinto en el commit más nuevo.", encoding="utf-8")
        posterior = self.guardar()
        self.assertNotEqual(self.commit, posterior)

        def decision(detalle):
            self.assertFalse((self.revision / "README.md").exists())
            self.assertIn(self.commit, detalle)
            return self.autorizado

        self.autorizado = False
        self.assertEqual(self.operacion(decision)["estado"], "rechazado")
        self.assertEqual(list(self.destinos.iterdir()), [])

        self.autorizado = True
        informe = self.operacion(decision)
        self.assertEqual(informe["estado"], "clonado")
        self.assertEqual(informe["alertas"], 1)
        self.assertEqual(informe["head_verificado"], self.commit)
        self.assertEqual(verificar_commit(Path(informe["destino"]), "HEAD"), self.commit)

    def test_revision_incompleta_no_pide_autorizacion(self):
        (self.origen / "README.md").write_bytes(b"texto \xff")
        self.commit = self.guardar()
        informe = self.operacion(lambda _: self.fail("No debe pedir aprobación con revisión incompleta."))
        self.assertEqual(informe["estado"], "detenido")
        self.assertIn("UTF-8", informe["motivo"])
        self.assertEqual(list(self.destinos.iterdir()), [])
