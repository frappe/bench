from __future__ import unicode_literals
import unittest
import bench
import bench.utils
import json
import os
import shutil

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

		self.assert_bench_config(bench_name)

		self.assert_config(bench_name)

		self.assert_socketio(bench_name)

	def test_multiple_benches(self):
		# 1st bench
		self.test_init("test-bench-1")

		self.assert_ports("test-bench-1", {
			"webserver_port": 8000,
			"socketio_port": 9000,
			"redis_celery_broker_port": 11000,
			"redis_async_broker_port": 12000,
			"redis_cache_port": 13000
		})

		self.assert_common_site_config("test-bench-1", {
			"celery_broker": "redis://localhost:11000",
			"async_redis_server": "redis://localhost:12000",
			"cache_redis_server": "redis://localhost:13000"
		})

		# 2nd bench
		self.test_init("test-bench-2")

		self.assert_ports("test-bench-2", {
			"webserver_port": 8001,
			"socketio_port": 9001,
			"redis_celery_broker_port": 11001,
			"redis_async_broker_port": 12001,
			"redis_cache_port": 13001
		})

		self.assert_common_site_config("test-bench-2", {
			"celery_broker": "redis://localhost:11001",
			"async_redis_server": "redis://localhost:12001",
			"cache_redis_server": "redis://localhost:13001"
		})

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

	def assert_bench_config(self, bench_name):
		config_json = os.path.join(bench_name, "config.json")
		self.assertTrue(os.path.exists(config_json))

		config = self.load_json(config_json)
		for key, value in bench.utils.default_config.items():
			self.assertEquals(config.get(key), value)

	def assert_config(self, bench_name):
		for config, search_key in (
			("redis_celery_broker.conf", "redis_celery_broker.rdb"),
			("redis_async_broker.conf", "redis_async_broker.rdb"),
			("redis_cache.conf", "redis_cache_dump.rdb")):

			self.assert_exists(bench_name, "config", config)

			with open(os.path.join(bench_name, "config", config), "r") as f:
				f = f.read().decode("utf-8")
				self.assertTrue(search_key in f)

	def assert_socketio(self, bench_name):
		self.assert_exists(bench_name, "node_modules")
		self.assert_exists(bench_name, "node_modules", "socket.io")

	def assert_ports(self, bench_name, ports):
		config_path = os.path.join(bench_name, 'config.json')
		config = self.load_json(config_path)

		for key, port in ports.items():
			self.assertEquals(config.get(key), port)

	def assert_common_site_config(self, bench_name, expected_config):
		common_site_config_path = os.path.join(bench_name, 'sites', 'common_site_config.json')
		config = self.load_json(common_site_config_path)

		for key, value in expected_config.items():
			self.assertEquals(config.get(key), value)

	def assert_exists(self, *args):
		self.assertTrue(os.path.exists(os.path.join(*args)))

	def load_json(self, path):
		with open(path, "r") as f:
			return json.loads(f.read().decode("utf-8"))
