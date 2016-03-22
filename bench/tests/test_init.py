from __future__ import unicode_literals
import unittest
import json, os, shutil, subprocess
import bench
import bench.utils
import bench.app
import bench.config.common_site_config
import bench.cli

bench.cli.from_command_line = True

class TestBenchInit(unittest.TestCase):
	def setUp(self):
		self.benches_path = "."
		self.benches = []

	def tearDown(self):
		for bench_name in self.benches:
			bench_path = os.path.join(self.benches_path, bench_name)
			if os.path.exists(bench_path):
				shutil.rmtree(bench_path, ignore_errors=True)

	def test_init(self, bench_name="test-bench"):
		self.init_bench(bench_name)

		self.assert_folders(bench_name)

		self.assert_virtual_env(bench_name)

		self.assert_common_site_config(bench_name, bench.config.common_site_config.default_config)

		self.assert_config(bench_name)

		self.assert_socketio(bench_name)

	def test_multiple_benches(self):
		# 1st bench
		self.test_init("test-bench-1")

		self.assert_common_site_config("test-bench-1", {
			"webserver_port": 8000,
			"socketio_port": 9000,
			"redis_queue": "redis://localhost:11000",
			"redis_socketio": "redis://localhost:12000",
			"redis_cache": "redis://localhost:13000"
		})

		# 2nd bench
		self.test_init("test-bench-2")

		self.assert_common_site_config("test-bench-2", {
			"webserver_port": 8001,
			"socketio_port": 9001,
			"redis_queue": "redis://localhost:11001",
			"redis_socketio": "redis://localhost:12001",
			"redis_cache": "redis://localhost:13001"
		})

	def test_new_site(self):
		self.new_site("test-site-1.dev")

	def new_site(self, site_name):
		self.test_init()

		new_site_cmd = ["bench", "new-site", site_name, "--admin-password", "admin"]

		# set in travis
		if os.environ.get("TRAVIS"):
			new_site_cmd.extend(["--mariadb-root-password", "travis"])

		subprocess.check_output(new_site_cmd, cwd=os.path.join(self.benches_path, "test-bench"))

		site_path = os.path.join(self.benches_path, "test-bench", "sites", site_name)

		self.assertTrue(os.path.exists(site_path))
		self.assertTrue(os.path.exists(os.path.join(site_path, "private", "backups")))
		self.assertTrue(os.path.exists(os.path.join(site_path, "private", "files")))
		self.assertTrue(os.path.exists(os.path.join(site_path, "public", "files")))

		site_config_path = os.path.join(site_path, "site_config.json")
		self.assertTrue(os.path.exists(site_config_path))
		with open(site_config_path, "r") as f:
			site_config = json.loads(f.read())

		for key in ("db_name", "db_password"):
			self.assertTrue(key in site_config)
			self.assertTrue(site_config[key])

	def test_install_app(self):
		site_name = "test-site-2.dev"

		self.new_site(site_name)

		bench_path = os.path.join(self.benches_path, "test-bench")

		# get app
		bench.app.get_app("erpnext", "https://github.com/frappe/erpnext", "develop", bench=bench_path)

		self.assertTrue(os.path.exists(os.path.join(bench_path, "apps", "erpnext")))

		# install app
		bench.app.install_app("erpnext", bench=bench_path)

		# install it to site
		subprocess.check_output(["bench", "--site", site_name, "install-app", "erpnext"], cwd=bench_path)

		out = subprocess.check_output(["bench", "--site", site_name, "list-apps"], cwd=bench_path)
		self.assertTrue("erpnext" in out)

	def init_bench(self, bench_name):
		self.benches.append(bench_name)
		bench.utils.init(bench_name)

	def assert_folders(self, bench_name):
		for folder in bench.utils.folders_in_bench:
			self.assert_exists(bench_name, folder)

		self.assert_exists(bench_name, "sites", "assets")
		self.assert_exists(bench_name, "apps", "frappe")
		self.assert_exists(bench_name, "apps", "frappe", "setup.py")

	def assert_virtual_env(self, bench_name):
		bench_path = os.path.abspath(bench_name)
		python = os.path.join(bench_path, "env", "bin", "python")
		python_path = bench.utils.get_cmd_output('{python} -c "import os; print os.path.dirname(os.__file__)"'.format(python=python))

		# part of bench's virtualenv
		self.assertTrue(python_path.startswith(bench_path))
		self.assert_exists(python_path)
		self.assert_exists(python_path, "site-packages")
		self.assert_exists(python_path, "site-packages", "IPython")
		self.assert_exists(python_path, "site-packages", "pip")

		site_packages = os.listdir(os.path.join(python_path, "site-packages"))
		self.assertTrue(any(package.startswith("MySQL_python-1.2.5") for package in site_packages))

	def assert_config(self, bench_name):
		for config, search_key in (
			("redis_queue.conf", "redis_queue.rdb"),
			("redis_socketio.conf", "redis_socketio.rdb"),
			("redis_cache.conf", "redis_cache.rdb")):

			self.assert_exists(bench_name, "config", config)

			with open(os.path.join(bench_name, "config", config), "r") as f:
				f = f.read().decode("utf-8")
				self.assertTrue(search_key in f)

	def assert_socketio(self, bench_name):
		self.assert_exists(bench_name, "node_modules")
		self.assert_exists(bench_name, "node_modules", "socket.io")

	def assert_common_site_config(self, bench_name, expected_config):
		common_site_config_path = os.path.join(bench_name, 'sites', 'common_site_config.json')
		self.assertTrue(os.path.exists(common_site_config_path))

		config = self.load_json(common_site_config_path)

		for key, value in expected_config.items():
			self.assertEquals(config.get(key), value)

	def assert_exists(self, *args):
		self.assertTrue(os.path.exists(os.path.join(*args)))

	def load_json(self, path):
		with open(path, "r") as f:
			return json.loads(f.read().decode("utf-8"))
