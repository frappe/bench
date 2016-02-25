from __future__ import unicode_literals
import unittest
import bench
import bench.utils
import json
import os
import shutil
import socket

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

		self.assert_folders(bench_name)

		self.assert_virtual_env(bench_name)

		self.assert_bench_config(bench_name)

		self.assert_config(bench_name)

		self.assert_socketio(bench_name)

	def test_multiple_benches(self):
		self.test_init("test-bench-1")
		test_bench_1_ports = {
			"webserver_port": 8000,
			"socketio_port": 9000,
			"redis_celery_broker_port": 11000,
			"redis_async_broker_port": 12000,
			"redis_cache_port": 13000
		}
		self.assert_ports("test-bench-1", test_bench_1_ports)

		self.test_init("test-bench-2")
		test_bench_2_ports = {
			"webserver_port": 8001,
			"socketio_port": 9001,
			"redis_celery_broker_port": 11001,
			"redis_async_broker_port": 12001,
			"redis_cache_port": 13001
		}
		self.assert_ports("test-bench-2", test_bench_2_ports)

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
			print f
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

	def assert_ports(self, bench_name, ports):
		config_path = os.path.join(self.benches_path, bench_name, 'config', 'config.json')

		with open(config_path, "r") as f:
			config_json = json.load(f)

		for key, port in ports:
			self.assertEqual(config_json.get(key), port)

	def assert_site_config(self, bench_name):
		pass

	def assert_exists(self, *args):
		self.assertTrue(os.path.exists(os.path.join(*args)))
