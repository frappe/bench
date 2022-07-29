# imports - standard imports
import getpass
import os
import pathlib
import re
import subprocess
import time
import unittest

# imports - module imports
from bench.utils import exec_cmd, get_cmd_output, which
from bench.config.production_setup import get_supervisor_confdir
from bench.tests.test_base import TestBenchBase


class TestSetupProduction(TestBenchBase):
	def test_setup_production(self):
		user = getpass.getuser()

		for bench_name in ("test-bench-1", "test-bench-2"):
			bench_path = os.path.join(os.path.abspath(self.benches_path), bench_name)
			self.init_bench(bench_name)
			exec_cmd(f"sudo bench setup production {user} --yes", cwd=bench_path)
			self.assert_nginx_config(bench_name)
			self.assert_supervisor_config(bench_name)
			self.assert_supervisor_process(bench_name)

		self.assert_nginx_process()
		exec_cmd(f"sudo bench setup sudoers {user}")
		self.assert_sudoers(user)

		for bench_name in self.benches:
			bench_path = os.path.join(os.path.abspath(self.benches_path), bench_name)
			exec_cmd("sudo bench disable-production", cwd=bench_path)

	def production(self):
		try:
			self.test_setup_production()
		except Exception:
			print(self.get_traceback())

	def assert_nginx_config(self, bench_name):
		conf_src = os.path.join(
			os.path.abspath(self.benches_path), bench_name, "config", "nginx.conf"
		)
		conf_dest = f"/etc/nginx/conf.d/{bench_name}.conf"

		self.assertTrue(self.file_exists(conf_src))
		self.assertTrue(self.file_exists(conf_dest))

		# symlink matches
		self.assertEqual(os.path.realpath(conf_dest), conf_src)

		# file content
		with open(conf_src) as f:
			f = f.read()

			for key in (
				f"upstream {bench_name}-frappe",
				f"upstream {bench_name}-socketio-server",
			):
				self.assertTrue(key in f)

	def assert_nginx_process(self):
		out = get_cmd_output("sudo nginx -t 2>&1")
		self.assertTrue(
			"nginx: configuration file /etc/nginx/nginx.conf test is successful" in out
		)

	def assert_sudoers(self, user):
		sudoers_file = "/etc/sudoers.d/frappe"
		service = which("service")
		nginx = which("nginx")

		self.assertTrue(self.file_exists(sudoers_file))

		if os.environ.get("CI"):
			sudoers = subprocess.check_output(["sudo", "cat", sudoers_file]).decode("utf-8")
		else:
			sudoers = pathlib.Path(sudoers_file).read_text()
		self.assertTrue(f"{user} ALL = (root) NOPASSWD: {service} nginx *" in sudoers)
		self.assertTrue(f"{user} ALL = (root) NOPASSWD: {nginx}" in sudoers)

	def assert_supervisor_config(self, bench_name, use_rq=True):
		conf_src = os.path.join(
			os.path.abspath(self.benches_path), bench_name, "config", "supervisor.conf"
		)

		supervisor_conf_dir = get_supervisor_confdir()
		conf_dest = f"{supervisor_conf_dir}/{bench_name}.conf"

		self.assertTrue(self.file_exists(conf_src))
		self.assertTrue(self.file_exists(conf_dest))

		# symlink matches
		self.assertEqual(os.path.realpath(conf_dest), conf_src)

		# file content
		with open(conf_src) as f:
			f = f.read()

			tests = [
				f"program:{bench_name}-frappe-web",
				f"program:{bench_name}-redis-cache",
				f"program:{bench_name}-redis-queue",
				f"program:{bench_name}-redis-socketio",
				f"group:{bench_name}-web",
				f"group:{bench_name}-workers",
				f"group:{bench_name}-redis",
			]

			if not os.environ.get("CI"):
				tests.append(f"program:{bench_name}-node-socketio")

			if use_rq:
				tests.extend(
					[
						f"program:{bench_name}-frappe-schedule",
						f"program:{bench_name}-frappe-default-worker",
						f"program:{bench_name}-frappe-short-worker",
						f"program:{bench_name}-frappe-long-worker",
					]
				)

			else:
				tests.extend(
					[
						f"program:{bench_name}-frappe-workerbeat",
						f"program:{bench_name}-frappe-worker",
						f"program:{bench_name}-frappe-longjob-worker",
						f"program:{bench_name}-frappe-async-worker",
					]
				)

			for key in tests:
				self.assertTrue(key in f)

	def assert_supervisor_process(self, bench_name, use_rq=True, disable_production=False):
		out = get_cmd_output("supervisorctl status")

		while "STARTING" in out:
			print("Waiting for all processes to start...")
			time.sleep(10)
			out = get_cmd_output("supervisorctl status")

		tests = [
			r"{bench_name}-web:{bench_name}-frappe-web[\s]+RUNNING",
			# Have commented for the time being. Needs to be uncommented later on. Bench is failing on travis because of this.
			# It works on one bench and fails on another.giving FATAL or BACKOFF (Exited too quickly (process log may have details))
			# "{bench_name}-web:{bench_name}-node-socketio[\s]+RUNNING",
			r"{bench_name}-redis:{bench_name}-redis-cache[\s]+RUNNING",
			r"{bench_name}-redis:{bench_name}-redis-queue[\s]+RUNNING",
			r"{bench_name}-redis:{bench_name}-redis-socketio[\s]+RUNNING",
		]

		if use_rq:
			tests.extend(
				[
					r"{bench_name}-workers:{bench_name}-frappe-schedule[\s]+RUNNING",
					r"{bench_name}-workers:{bench_name}-frappe-default-worker-0[\s]+RUNNING",
					r"{bench_name}-workers:{bench_name}-frappe-short-worker-0[\s]+RUNNING",
					r"{bench_name}-workers:{bench_name}-frappe-long-worker-0[\s]+RUNNING",
				]
			)

		else:
			tests.extend(
				[
					r"{bench_name}-workers:{bench_name}-frappe-workerbeat[\s]+RUNNING",
					r"{bench_name}-workers:{bench_name}-frappe-worker[\s]+RUNNING",
					r"{bench_name}-workers:{bench_name}-frappe-longjob-worker[\s]+RUNNING",
					r"{bench_name}-workers:{bench_name}-frappe-async-worker[\s]+RUNNING",
				]
			)

		for key in tests:
			if disable_production:
				self.assertFalse(re.search(key, out))
			else:
				self.assertTrue(re.search(key, out))


if __name__ == "__main__":
	unittest.main()
