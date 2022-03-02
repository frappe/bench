import os
import shutil
import unittest

from bench.app import App
from bench.bench import Bench
from bench.utils import is_valid_frappe_branch


class TestUtils(unittest.TestCase):
	def test_app_utils(self):
		git_url = "https://github.com/frappe/frappe"
		branch = "develop"
		app = App(name=git_url, branch=branch, bench=Bench("."))
		self.assertTrue(
			all(
				[
					app.name == git_url,
					app.branch == branch,
					app.tag == branch,
					app.is_url == True,
					app.on_disk == False,
					app.org == "frappe",
					app.url == git_url,
				]
			)
		)

	def test_is_valid_frappe_branch(self):
		self.assertTrue(is_valid_frappe_branch("https://github.com/frappe/frappe", frappe_branch=""))
		self.assertTrue(is_valid_frappe_branch("https://github.com/frappe/frappe", frappe_branch="develop"))
		self.assertTrue(is_valid_frappe_branch("https://github.com/frappe/erpnext", frappe_branch="version-13"))
		self.assertFalse(is_valid_frappe_branch("https://github.com/frappe/erpnext", frappe_branch="version-1"))

	def test_app_states(self):
		bench_dir = "./sandbox"
		sites_dir = os.path.join(bench_dir, "sites")

		if not os.path.exists(sites_dir):
			os.makedirs(sites_dir)

		fake_bench = Bench(bench_dir)

		fake_bench.apps.set_states()

		self.assertTrue(hasattr(fake_bench.apps, "states"))
		self.assertTrue(os.path.exists(os.path.join(sites_dir, "apps_states.json")))

		fake_bench.apps.states = {"frappe": {"resolution": None, "version": "14.0.0-dev"}}
		fake_bench.apps.update_apps_states()

		self.assertEqual(fake_bench.apps.states, {})

		frappe_path = os.path.join(bench_dir, "apps", "frappe", "frappe")

		os.makedirs(frappe_path)

		with open(os.path.join(frappe_path, "__init__.py"), "w+") as f:
			f.write("__version__ = '11.0'")

		fake_bench.apps.update_apps_states("frappe")

		self.assertIn("frappe", fake_bench.apps.states)
		self.assertIn("version", fake_bench.apps.states["frappe"])
		self.assertEqual("11.0", fake_bench.apps.states["frappe"]["version"])

		shutil.rmtree(bench_dir)

	def test_get_dependencies(self):
		fake_app = App("frappe/healthcare@develop")
		self.assertIn("erpnext", fake_app._get_dependencies())
		fake_app = App("frappe/not_healthcare@not-a-branch")
		self.assertTrue(len(fake_app._get_dependencies()) == 0)
