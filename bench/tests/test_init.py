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
				shutil.rmtree(bench_path)

	def test_init(self, bench_name="test-bench"):
		self.benches.append(bench_name)

		bench.utils.init(bench_name)

		# logging
		self.assert_exists(bench_name, "logs", "bench.log")

		self.assert_folders(bench_name)

		self.assert_virtual_env(bench_name)

		self.assert_bench_config(bench_name)

		self.assert_config(bench_name)

		self.assert_socketio(bench_name)

	def test_multiple_benches(self):
		self.test_init("test-bench-1")
		self.assert_ports("test-bench-1")

		self.test_init("test-bench-2")
		self.assert_ports("test-bench-2")

	def assert_folders(self, bench_name):
		for folder in bench.utils.folders_in_bench:
			self.assert_exists(bench_name, folder)

		self.assert_exists(bench_name, "sites", "assets")
		self.assert_exists(bench_name, "apps", "frappe")
		self.assert_exists(bench_name, "apps", "frappe", "setup.py")

	def assert_virtual_env(self, bench_name):
		self.assert_exists(bench_name, "env", "lib", "python2.7")
		self.assert_exists(bench_name, "env", "lib", "python2.7", "site-packages")
		self.assert_exists(bench_name, "env", "lib", "python2.7", "site-packages", "IPython")
		self.assert_exists(bench_name, "env", "lib", "python2.7", "site-packages", "MySQL_python-1.2.5.dist-info")
		self.assert_exists(bench_name, "env", "lib", "python2.7", "site-packages", "pip")

	def assert_bench_config(self, bench_name):
		config_json = os.path.exists(os.path.join(bench_name, "config.json"))
		self.assertTrue(config_json)
		with open(config_json, "r") as f:
			config_dict = json.loads(f.read().decode("utf-8"))
			for key, value in bench.utils.default_config.items():
				self.assertEquals(config_dict.get(key), value)

	def assert_config(self, bench_name):
		for config, search_key in (
			("redis_celery_broker.conf", "redis_celery_broker.rdb"),
			("redis_async_broker.conf", "redis_async_broker.rdb"),
			("redis_cache.conf", "redis_cache_dump.rdb")):

			self.assert_exists(bench_name, "config", config)

			with open(os.path.join(self.bench, "config", config), "r") as f:
				f = f.read().decode("utf-8")
				self.assertTrue(search_key in f)

	def assert_socketio(self, bench_name):
		self.assert_exists(bench_name, "node_modules")
		self.assert_exists(bench_name, "node_modules", "socket.io")

	def assert_ports(self, bench_name):
		pass

	def assert_exists(self, *args):
		self.assert_exists(*args)

