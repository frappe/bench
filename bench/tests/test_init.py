# imports - standard imports
import json
import os
import subprocess
import unittest

# imports - third paty imports
import git

# imports - module imports
from bench.utils import exec_cmd
from bench.release import get_bumped_version
from bench.tests.test_base import FRAPPE_BRANCH, TestBenchBase


# changed from frappe_theme because it wasn't maintained and incompatible,
# chat app & wiki was breaking too. hopefully frappe_docs will be maintained
# for longer since docs.erpnext.com is powered by it ;)
TEST_FRAPPE_APP = "frappe_docs"

class TestBenchInit(TestBenchBase):
	def test_semantic_version(self):
		self.assertEqual( get_bumped_version('11.0.4', 'major'), '12.0.0' )
		self.assertEqual( get_bumped_version('11.0.4', 'minor'), '11.1.0' )
		self.assertEqual( get_bumped_version('11.0.4', 'patch'), '11.0.5' )
		self.assertEqual( get_bumped_version('11.0.4', 'prerelease'), '11.0.5-beta.1' )

		self.assertEqual( get_bumped_version('11.0.5-beta.22', 'major'), '12.0.0' )
		self.assertEqual( get_bumped_version('11.0.5-beta.22', 'minor'), '11.1.0' )
		self.assertEqual( get_bumped_version('11.0.5-beta.22', 'patch'), '11.0.5' )
		self.assertEqual( get_bumped_version('11.0.5-beta.22', 'prerelease'), '11.0.5-beta.23' )


	def test_utils(self):
		self.assertEqual(subprocess.call("bench"), 0)


	def test_init(self, bench_name="test-bench", **kwargs):
		self.init_bench(bench_name, **kwargs)
		self.assert_folders(bench_name)
		self.assert_virtual_env(bench_name)
		self.assert_config(bench_name)


	def basic(self):
		try:
			self.test_init()
		except Exception:
			print(self.get_traceback())


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
		bench_name = "test-bench"
		site_name = "test-site.local"
		bench_path = os.path.join(self.benches_path, bench_name)
		site_path = os.path.join(bench_path, "sites", site_name)
		site_config_path = os.path.join(site_path, "site_config.json")

		self.init_bench(bench_name)
		exec_cmd("bench setup requirements --node", cwd=bench_path)
		self.new_site(site_name, bench_name)

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
		exec_cmd(f"bench get-app {TEST_FRAPPE_APP}", cwd=bench_path)
		self.assertTrue(os.path.exists(os.path.join(bench_path, "apps", TEST_FRAPPE_APP)))
		app_installed_in_env = TEST_FRAPPE_APP in subprocess.check_output(["bench", "pip", "freeze"], cwd=bench_path).decode('utf8')
		self.assertTrue(app_installed_in_env)


	def test_install_app(self):
		bench_name = "test-bench"
		site_name = "install-app.test"
		bench_path = os.path.join(self.benches_path, "test-bench")

		self.init_bench(bench_name)
		exec_cmd("bench setup requirements --node", cwd=bench_path)
		exec_cmd("bench build", cwd=bench_path)
		exec_cmd(f"bench get-app {TEST_FRAPPE_APP} --branch master", cwd=bench_path)

		self.assertTrue(os.path.exists(os.path.join(bench_path, "apps", TEST_FRAPPE_APP)))

		# check if app is installed
		app_installed_in_env = TEST_FRAPPE_APP in subprocess.check_output(["bench", "pip", "freeze"], cwd=bench_path).decode('utf8')
		self.assertTrue(app_installed_in_env)

		# create and install app on site
		self.new_site(site_name, bench_name)
		installed_app = not exec_cmd(f"bench --site {site_name} install-app {TEST_FRAPPE_APP}", cwd=bench_path)

		app_installed_on_site = subprocess.check_output(["bench", "--site", site_name, "list-apps"], cwd=bench_path).decode('utf8')

		if installed_app:
			self.assertTrue(TEST_FRAPPE_APP in app_installed_on_site)


	def test_remove_app(self):
		self.init_bench("test-bench")
		bench_path = os.path.join(self.benches_path, "test-bench")

		exec_cmd("bench setup requirements --node", cwd=bench_path)
		exec_cmd(f"bench get-app {TEST_FRAPPE_APP} --branch master --overwrite", cwd=bench_path)
		exec_cmd(f"bench remove-app {TEST_FRAPPE_APP}", cwd=bench_path)

		with open(os.path.join(bench_path, "sites", "apps.txt")) as f:
			self.assertFalse(TEST_FRAPPE_APP in f.read())
		self.assertFalse(TEST_FRAPPE_APP in subprocess.check_output(["bench", "pip", "freeze"], cwd=bench_path).decode('utf8'))
		self.assertFalse(os.path.exists(os.path.join(bench_path, "apps", TEST_FRAPPE_APP)))


	def test_switch_to_branch(self):
		self.init_bench("test-bench")
		bench_path = os.path.join(self.benches_path, "test-bench")
		app_path = os.path.join(bench_path, "apps", "frappe")

		# * chore: change to 14 when avalible
		prevoius_branch = "version-13"
		if FRAPPE_BRANCH != "develop":
			# assuming we follow `version-#`
			prevoius_branch = f"version-{int(FRAPPE_BRANCH.split('-')[1]) - 1}"

		successful_switch = not exec_cmd(f"bench switch-to-branch {prevoius_branch} frappe --upgrade", cwd=bench_path)
		app_branch_after_switch = str(git.Repo(path=app_path).active_branch)
		if successful_switch:
			self.assertEqual(prevoius_branch, app_branch_after_switch)

		successful_switch = not exec_cmd(f"bench switch-to-branch {FRAPPE_BRANCH} frappe --upgrade", cwd=bench_path)
		app_branch_after_second_switch = str(git.Repo(path=app_path).active_branch)
		if successful_switch:
			self.assertEqual(FRAPPE_BRANCH, app_branch_after_second_switch)


if __name__ == '__main__':
	unittest.main()
