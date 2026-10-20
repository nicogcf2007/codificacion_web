"""Offline packaging regressions; never import providers or touch survey data."""
from pathlib import Path
import ast
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DeliveryContractTests(unittest.TestCase):
    def test_default_entrypoint_does_not_initialize_temporary_sessions(self):
        source = (ROOT / "backend/main.py").read_text(encoding="utf-8")
        imports = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ImportFrom)]
        self.assertTrue(any(node.module == "modern.app" for node in imports))
        self.assertNotIn("SessionManager", source)
        self.assertNotIn("temp_uploads", source)

    def test_compose_uses_durable_database_without_temporary_recovery_volume(self):
        source = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("DATABASE_URL:", source)
        self.assertIn("CODING_PROVIDER:", source)
        self.assertIn("CNC_ADMIN_EMAIL:", source)
        self.assertIn("CNC_ADMIN_PASSWORD:", source)
        self.assertIn("CNC_COOKIE_SECURE:", source)
        self.assertNotIn("APP_ACCESS_TOKEN:", source)
        self.assertNotIn("codificacion_temp", source)
        self.assertNotIn("TEMP_DIR:", source)

    def test_backend_container_creates_durable_data_directory(self):
        source = (ROOT / "backend/Dockerfile").read_text(encoding="utf-8")
        self.assertIn("mkdir -p /app/data", source)
        self.assertNotIn("/app/temp_uploads", source)


if __name__ == "__main__":
    unittest.main()
