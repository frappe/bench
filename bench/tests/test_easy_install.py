import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


EASY_INSTALL_PATH = Path(__file__).resolve().parents[2] / "easy-install.py"
_spec = importlib.util.spec_from_file_location("easy_install", EASY_INSTALL_PATH)
easy_install = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(easy_install)


class TestEasyInstall(unittest.TestCase):
    def _create_example_env(self, root: str):
        with open(os.path.join(root, "example.env"), "w") as f:
            f.write("ERPNEXT_VERSION=v16.0.0\n")

    def test_write_to_env_sets_default_sites_rule(self):
        with tempfile.TemporaryDirectory() as frappe_docker_dir, tempfile.NamedTemporaryFile() as out_file:
            self._create_example_env(frappe_docker_dir)
            easy_install.write_to_env(
                frappe_docker_dir=frappe_docker_dir,
                out_file=out_file.name,
                sites=[],
                db_pass="db_pass",
                admin_pass="admin_pass",
                email="test@example.com",
                cronstring="@every 6h",
            )

            with open(out_file.name) as f:
                env_data = f.read()

        self.assertIn("SITES=`site1.localhost`", env_data)
        self.assertIn("SITES_RULE=Host(`site1.localhost`)", env_data)

    def test_write_to_env_preserves_provided_sites_rule(self):
        with tempfile.TemporaryDirectory() as frappe_docker_dir, tempfile.NamedTemporaryFile() as out_file:
            self._create_example_env(frappe_docker_dir)
            custom_rule = "Host(`custom.localhost`)"
            easy_install.write_to_env(
                frappe_docker_dir=frappe_docker_dir,
                out_file=out_file.name,
                sites=["site1.localhost"],
                db_pass="db_pass",
                admin_pass="admin_pass",
                email="test@example.com",
                cronstring="@every 6h",
                sites_rule=custom_rule,
            )

            with open(out_file.name) as f:
                env_data = f.read()

        self.assertIn(f"SITES_RULE={custom_rule}", env_data)


if __name__ == "__main__":
    unittest.main()
