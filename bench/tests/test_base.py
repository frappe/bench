# imports - standard imports
import getpass
import json
import os
import shutil
import subprocess
import sys
import traceback
import unittest

# imports - third party imports
from six import PY2

# imports - module imports
import bench
import bench.utils

if PY2:
	FRAPPE_BRANCH = "version-12"
else:
	FRAPPE_BRANCH = "develop"

class TestBenchBase(unittest.TestCase):
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
					subprocess.call(["bench", "drop-site", site, "--force", "--no-backup", "--root-password", mariadb_password], cwd=bench_path)
				shutil.rmtree(bench_path, ignore_errors=True)

	def assert_folders(self, bench_name):
		for folder in bench.utils.folders_in_bench:
			self.assert_exists(bench_name, folder)
		self.assert_exists(bench_name, "apps", "frappe")

	def assert_virtual_env(self, bench_name):
		bench_path = os.path.abspath(bench_name)
		python_path = os.path.abspath(os.path.join(bench_path, "env", "bin", "python"))
		self.assertTrue(python_path.startswith(bench_path))
		for subdir in ("bin", "include", "lib", "share"):
			self.assert_exists(bench_name, "env", subdir)

	def assert_config(self, bench_name):
		for config, search_key in (
			("redis_queue.conf", "redis_queue.rdb"),
			("redis_socketio.conf", "redis_socketio.rdb"),
			("redis_cache.conf", "redis_cache.rdb")):

			self.assert_exists(bench_name, "config", config)

			with open(os.path.join(bench_name, "config", config), "r") as f:
				self.assertTrue(search_key in f.read())

	def assert_common_site_config(self, bench_name, expected_config):
		common_site_config_path = os.path.join(self.benches_path, bench_name, 'sites', 'common_site_config.json')
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
			bench.utils.exec_cmd("git clone https://github.com/frappe/frappe -b {branch} --depth 1 --origin upstream {location}".format(branch=FRAPPE_BRANCH, location=frappe_tmp_path))

		kwargs.update(dict(
			python=sys.executable,
			no_procfile=True,
			no_backups=True,
			skip_assets=True,
			frappe_path=frappe_tmp_path
		))

		if not os.path.exists(os.path.join(self.benches_path, bench_name)):
			bench.utils.init(bench_name, **kwargs)
			bench.utils.exec_cmd("git remote set-url upstream https://github.com/frappe/frappe", cwd=os.path.join(self.benches_path, bench_name, "apps", "frappe"))

	def file_exists(self, path):
		if os.environ.get("CI"):
			return not subprocess.call(["sudo", "test", "-f", path])
		return os.path.isfile(path)

	def get_traceback(self):
		exc_type, exc_value, exc_tb = sys.exc_info()
		trace_list = traceback.format_exception(exc_type, exc_value, exc_tb)
		body = "".join(str(t) for t in trace_list)
		return body
