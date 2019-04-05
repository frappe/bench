
import unittest
import json, os, shutil, subprocess
import bench
import bench.utils
import bench.app
import bench.config.common_site_config
import bench.cli
from bench.release import get_bumped_version

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

		self.assert_common_site_config(bench_name, bench.config.common_site_config.default_config)

		self.assert_config(bench_name)

		self.assert_socketio(bench_name)

	def test_multiple_benches(self):
		# 1st bench
		self.test_init("test-bench-1")

		self.assert_common_site_config("test-bench-1", {
			"webserver_port": 8000,
			"socketio_port": 9000,
			"file_watcher_port": 6787,
			"redis_queue": "redis://localhost:11000",
			"redis_socketio": "redis://localhost:12000",
			"redis_cache": "redis://localhost:13000"
		})

		# 2nd bench
		self.test_init("test-bench-2")

		self.assert_common_site_config("test-bench-2", {
			"webserver_port": 8001,
			"socketio_port": 9001,
			"file_watcher_port": 6788,
			"redis_queue": "redis://localhost:11001",
			"redis_socketio": "redis://localhost:12001",
			"redis_cache": "redis://localhost:13001"
		})

	def test_new_site(self):
		self.init_bench('test-bench')
		self.new_site("test-site-1.dev")

	def new_site(self, site_name):
		new_site_cmd = ["bench", "new-site", site_name, "--admin-password", "admin"]

		# set in CI
		if os.environ.get('CI'):
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

	def test_get_app(self):
		site_name = "test-site-2.dev"
		self.init_bench('test-bench')

		self.new_site(site_name)
		bench_path = os.path.join(self.benches_path, "test-bench")

		bench.app.get_app("https://github.com/frappe/frappe-client", bench_path=bench_path)
		self.assertTrue(os.path.exists(os.path.join(bench_path, "apps", "frappeclient")))

	def test_install_app(self):
		site_name = "test-site-3.dev"
		self.init_bench('test-bench')

		self.new_site(site_name)
		bench_path = os.path.join(self.benches_path, "test-bench")

		# get app
		bench.app.get_app("https://github.com/frappe/erpnext", "develop", bench_path=bench_path)

		self.assertTrue(os.path.exists(os.path.join(bench_path, "apps", "erpnext")))

		# install app
		bench.app.install_app("erpnext", bench_path=bench_path)

		# install it to site
		subprocess.check_output(["bench", "--site", site_name, "install-app", "erpnext"], cwd=bench_path)

		out = subprocess.check_output(["bench", "--site", site_name, "list-apps"], cwd=bench_path)
		self.assertTrue("erpnext" in out)


	def test_remove_app(self):
		self.init_bench('test-bench')

		bench_path = os.path.join(self.benches_path, "test-bench")

		# get app
		bench.app.get_app("https://github.com/frappe/erpnext", "develop", bench_path=bench_path)

		self.assertTrue(os.path.exists(os.path.join(bench_path, "apps", "erpnext")))

		# remove it
		bench.app.remove_app("erpnext", bench_path=bench_path)

		self.assertFalse(os.path.exists(os.path.join(bench_path, "apps", "erpnext")))


	def test_switch_to_branch(self):
		self.init_bench('test-bench')

		bench_path = os.path.join(self.benches_path, "test-bench")
		app_path = os.path.join(bench_path, "apps", "frappe")

		bench.app.switch_branch(branch="master", apps=["frappe"], bench_path=bench_path, check_upgrade=False)
		out = subprocess.check_output(['git', 'status'], cwd=app_path)
		self.assertTrue("master" in out)

		# bring it back to develop!
		bench.app.switch_branch(branch="develop", apps=["frappe"], bench_path=bench_path, check_upgrade=False)
		out = subprocess.check_output(['git', 'status'], cwd=app_path)
		self.assertTrue("develop" in out)

	def init_bench(self, bench_name, **kwargs):
		self.benches.append(bench_name)
		bench.utils.init(bench_name, **kwargs)

	def test_drop_site(self):
		self.init_bench('test-bench')
		# Check without archive_path given to drop-site command
		self.drop_site("test-drop-without-archive-path")

		# Check with archive_path given to drop-site command
		home = os.path.abspath(os.path.expanduser('~'))
		archived_sites_path = os.path.join(home, 'archived_sites')

		self.drop_site("test-drop-with-archive-path", archived_sites_path=archived_sites_path)

	def drop_site(self, site_name, archived_sites_path=None):
		self.new_site(site_name)

		drop_site_cmd = ['bench', 'drop-site', site_name]

		if archived_sites_path:
			drop_site_cmd.extend(['--archived-sites-path', archived_sites_path])

		if os.environ.get('CI'):
			drop_site_cmd.extend(['--root-password', 'travis'])

		bench_path = os.path.join(self.benches_path, 'test-bench')
		try:
			subprocess.check_output(drop_site_cmd, cwd=bench_path)
		except subprocess.CalledProcessError as err:
			print(err.output)

		if not archived_sites_path:
			archived_sites_path = os.path.join(bench_path, 'archived_sites')
			self.assertTrue(os.path.exists(archived_sites_path))
			self.assertTrue(os.path.exists(os.path.join(archived_sites_path, site_name)))

		else:
			self.assertTrue(os.path.exists(archived_sites_path))
			self.assertTrue(os.path.exists(os.path.join(archived_sites_path, site_name)))

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
		# removing test case temporarily
		# as develop and master branch havin differnt version of mysqlclient
		#self.assertTrue(any(package.startswith("mysqlclient-1.3.12") for package in site_packages))

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
		try: # for v10 and under
			self.assert_exists(bench_name, "node_modules")
			self.assert_exists(bench_name, "node_modules", "socket.io")
		except: # for v11 and above
			self.assert_exists(bench_name, "apps", "frappe", "node_modules")
			self.assert_exists(bench_name, "apps", "frappe", "node_modules", "socket.io")

	def assert_common_site_config(self, bench_name, expected_config):
		common_site_config_path = os.path.join(bench_name, 'sites', 'common_site_config.json')
		self.assertTrue(os.path.exists(common_site_config_path))

		config = self.load_json(common_site_config_path)

		for key, value in list(expected_config.items()):
			self.assertEqual(config.get(key), value)

	def assert_exists(self, *args):
		self.assertTrue(os.path.exists(os.path.join(*args)))

	def load_json(self, path):
		with open(path, "r") as f:
			return json.loads(f.read().decode("utf-8"))
