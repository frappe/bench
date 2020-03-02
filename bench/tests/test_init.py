# imports - standard imports
import json
import os
import shutil
import subprocess
import unittest
import random
import getpass

# imports - third paty imports
import git

# imports - module imports
import bench
import bench.app
import bench.cli
import bench.config.common_site_config
import bench.utils
from bench.release import get_bumped_version

bench.cli.from_command_line = True

class TestBenchInit(unittest.TestCase):
	def setUp(self):
		self.benches_path = "."
		self.benches = []

	def tearDown(self):
		for bench_name in self.benches:
			bench_path = os.path.join(self.benches_path, bench_name)
			mariadb_password = "travis" if os.environ.get("CI") else getpass.getpass(prompt="Enter MariaDB root Password: ")
			if os.path.exists(bench_path):
				sites = bench.utils.get_sites(bench_path=bench_path)
				for site in sites:
					subprocess.call(["bench", "drop-site", site, "--force", "--root-password", mariadb_password], cwd=bench_path)
				shutil.rmtree(bench_path, ignore_errors=True)

	def test_bench_init(self):
		self.test_init()
		self.test_multiple_benches()
		self.test_new_site()
		self.test_get_app()
		self.test_install_app()
		self.test_remove_app()
		self.test_semantic_version()
		self.test_switch_to_branch()

	def test_semantic_version(self):
		self.assertEqual( get_bumped_version('11.0.4', 'major'), '12.0.0' )
		self.assertEqual( get_bumped_version('11.0.4', 'minor'), '11.1.0' )
		self.assertEqual( get_bumped_version('11.0.4', 'patch'), '11.0.5' )
		self.assertEqual( get_bumped_version('11.0.4', 'prerelease'), '11.0.5-beta.1' )

		self.assertEqual( get_bumped_version('11.0.5-beta.22', 'major'), '12.0.0' )
		self.assertEqual( get_bumped_version('11.0.5-beta.22', 'minor'), '11.1.0' )
		self.assertEqual( get_bumped_version('11.0.5-beta.22', 'patch'), '11.0.5' )
		self.assertEqual( get_bumped_version('11.0.5-beta.22', 'prerelease'), '11.0.5-beta.23' )

	def test_init(self, bench_name="test-bench", **kwargs):
		self.init_bench(bench_name, **kwargs)
		self.assert_folders(bench_name)
		self.assert_virtual_env(bench_name)
		self.assert_config(bench_name)

	def test_multiple_benches(self):
		for bench_name in ("test-bench-1", "test-bench-2"):
			self.init_bench(bench_name)

		self.assert_common_site_config("test-bench-1", {
			"webserver_port": 8000,
			"socketio_port": 9000,
			"file_watcher_port": 6787,
			"redis_queue": "redis://localhost:11000",
			"redis_socketio": "redis://localhost:12000",
			"redis_cache": "redis://localhost:13000"
		})

		self.assert_common_site_config("test-bench-2", {
			"webserver_port": 8001,
			"socketio_port": 9001,
			"file_watcher_port": 6788,
			"redis_queue": "redis://localhost:11001",
			"redis_socketio": "redis://localhost:12001",
			"redis_cache": "redis://localhost:13001"
		})

	def test_new_site(self):
		self.init_bench("test-bench")
		bench_path = os.path.join(self.benches_path, "test-bench")
		site_name = "test-site.local"
		site_path = os.path.join(bench_path, "sites", site_name)
		site_config_path = os.path.join(site_path, "site_config.json")

		self.assertTrue(os.path.exists(site_path))
		self.assertTrue(os.path.exists(os.path.join(site_path, "private", "backups")))
		self.assertTrue(os.path.exists(os.path.join(site_path, "private", "files")))
		self.assertTrue(os.path.exists(os.path.join(site_path, "public", "files")))
		self.assertTrue(os.path.exists(site_config_path))

		with open(site_config_path, "r") as f:
			site_config = json.loads(f.read())

			for key in ("db_name", "db_password"):
				self.assertTrue(key in site_config)
				self.assertTrue(site_config[key])

	def test_get_app(self):
		self.init_bench("test-bench")
		bench_path = os.path.join(self.benches_path, "test-bench")
		bench.app.get_app("https://github.com/frappe/frappe_theme", bench_path=bench_path, skip_assets=True)
		self.assertTrue(os.path.exists(os.path.join(bench_path, "apps", "frappe_theme")))

	def test_install_app(self):
		self.init_bench("test-bench")
		bench_path = os.path.join(self.benches_path, "test-bench")
		site_name = "install-app.test"

		self.new_site(site_name, "test-bench")
		bench.app.get_app("https://github.com/frappe/erpnext", "version-12", bench_path=bench_path, skip_assets=True)
		bench.app.install_app("erpnext", bench_path=bench_path)

		subprocess.call(["bench", "--site", site_name, "install-app", "erpnext"], cwd=bench_path)
		out = subprocess.check_output(["bench", "--site", site_name, "list-apps"], cwd=bench_path)
		self.assertTrue("erpnext" in out)

	def test_remove_app(self):
		self.init_bench("test-bench")
		bench_path = os.path.join(self.benches_path, "test-bench")
		bench.app.get_app("https://github.com/frappe/erpnext", "version-12", bench_path=bench_path, skip_assets=True)
		bench.app.remove_app("erpnext", bench_path=bench_path)
		self.assertFalse(os.path.exists(os.path.join(bench_path, "apps", "erpnext")))

	def test_switch_to_branch(self):
		self.init_bench("test-bench")
		bench_path = os.path.join(self.benches_path, "test-bench")
		app_path = os.path.join(bench_path, "apps", "frappe")

		bench.app.switch_branch(branch="version-12", apps=["frappe"], bench_path=bench_path, check_upgrade=False)
		app_branch_after_switch = str(git.Repo(path=app_path).active_branch)
		self.assertEqual("version-12", app_branch_after_switch)

		bench.app.switch_branch(branch="develop", apps=["frappe"], bench_path=bench_path, check_upgrade=False)
		app_branch_after_second_switch = str(git.Repo(path=app_path).active_branch)
		self.assertEqual("develop", app_branch_after_second_switch)

	def assert_folders(self, bench_name):
		for folder in bench.utils.folders_in_bench:
			self.assert_exists(bench_name, folder)

		self.assert_exists(bench_name, "sites", "assets")
		self.assert_exists(bench_name, "apps", "frappe")
		self.assert_exists(bench_name, "apps", "frappe", "setup.py")

	def assert_virtual_env(self, bench_name):
		bench_path = os.path.abspath(bench_name)
		python = os.path.join(bench_path, "env", "bin", "python")
		python_path = bench.utils.get_cmd_output('{python} -c "from __future__ import print_function; import os; print(os.path.dirname(os.__file__))"'.format(python=python))

		self.assertTrue(python_path.startswith(bench_path))
		self.assert_exists(python_path)
		self.assert_exists(python_path, "site-packages")
		self.assert_exists(python_path, "site-packages", "IPython")
		self.assert_exists(python_path, "site-packages", "pip")

	def assert_config(self, bench_name):
		for config, search_key in (
			("redis_queue.conf", "redis_queue.rdb"),
			("redis_socketio.conf", "redis_socketio.rdb"),
			("redis_cache.conf", "redis_cache.rdb")):

			self.assert_exists(bench_name, "config", config)

			with open(os.path.join(bench_name, "config", config), "r") as f:
				self.assertTrue(search_key in f.read())

	def assert_common_site_config(self, bench_name, expected_config):
		common_site_config_path = os.path.join(bench_name, 'sites', 'common_site_config.json')
		self.assertTrue(os.path.exists(common_site_config_path))

		with open(common_site_config_path, "r") as f:
			config = json.load(f)

		for key, value in list(expected_config.items()):
			self.assertEqual(config.get(key), value)

	def assert_exists(self, *args):
		self.assertTrue(os.path.exists(os.path.join(*args)))

	def new_site(self, site_name, bench_name):
		new_site_cmd = ["bench", "new-site", site_name, "--admin-password", "admin"]

		if os.environ.get('CI'):
			new_site_cmd.extend(["--mariadb-root-password", "travis"])

		subprocess.call(new_site_cmd, cwd=os.path.join(self.benches_path, bench_name))

	def init_bench(self, bench_name, **kwargs):
		self.benches.append(bench_name)
		frappe_tmp_path = "/tmp/frappe"

		if not os.path.exists(frappe_tmp_path):
			git.Repo.clone_from("https://github.com/frappe/frappe", frappe_tmp_path, depth=1)

		kwargs.update(dict(
			no_procfile=True,
			no_backups=True,
			skip_assets=True,
			frappe_path=frappe_tmp_path
		))

		bench.utils.init(bench_name, **kwargs)
