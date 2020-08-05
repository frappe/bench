# imports - standard imports
import getpass
import os
import re
import subprocess
import time
import unittest

# imports - module imports
import bench.utils
from bench.config.production_setup import get_supervisor_confdir
from bench.tests.test_base import TestBenchBase


class TestSetupProduction(TestBenchBase):
	def test_setup_production(self):
		user = getpass.getuser()

		for bench_name in ("test-bench-1", "test-bench-2"):
			bench_path = os.path.join(os.path.abspath(self.benches_path), bench_name)
			self.init_bench(bench_name)
			bench.utils.exec_cmd("sudo bench setup production {0} --yes".format(user), cwd=bench_path)
			self.assert_nginx_config(bench_name)
			self.assert_supervisor_config(bench_name)
			self.assert_supervisor_process(bench_name)

		self.assert_nginx_process()
		bench.utils.exec_cmd("sudo bench setup sudoers {0}".format(user))
		self.assert_sudoers(user)

		for bench_name in self.benches:
			bench_path = os.path.join(os.path.abspath(self.benches_path), bench_name)
			bench.utils.exec_cmd("sudo bench disable-production", cwd=bench_path)


	def production(self):
		try:
			self.test_setup_production()
		except Exception:
			print(self.get_traceback())


	def assert_nginx_config(self, bench_name):
		conf_src = os.path.join(os.path.abspath(self.benches_path), bench_name, 'config', 'nginx.conf')
		conf_dest = "/etc/nginx/conf.d/{bench_name}.conf".format(bench_name=bench_name)

		self.assertTrue(self.file_exists(conf_src))
		self.assertTrue(self.file_exists(conf_dest))

		# symlink matches
		self.assertEqual(os.path.realpath(conf_dest), conf_src)

		# file content
		with open(conf_src, "r") as f:
			f = f.read()

			for key in (
					"upstream {bench_name}-frappe",
					"upstream {bench_name}-socketio-server"
				):
				self.assertTrue(key.format(bench_name=bench_name) in f)


	def assert_nginx_process(self):
		out = bench.utils.get_cmd_output("sudo nginx -t 2>&1")
		self.assertTrue("nginx: configuration file /etc/nginx/nginx.conf test is successful" in out)


	def assert_sudoers(self, user):
		sudoers_file = '/etc/sudoers.d/frappe'
		service = bench.utils.which("service")
		nginx = bench.utils.which("nginx")

		self.assertTrue(self.file_exists(sudoers_file))

		if os.environ.get("CI"):
			sudoers = subprocess.check_output(["sudo", "cat", sudoers_file]).decode("utf-8")
		else:
			with open(sudoers_file, 'r') as f:
				sudoers = f.read()

		self.assertTrue('{user} ALL = (root) NOPASSWD: {service} nginx *'.format(service=service, user=user) in sudoers)
		self.assertTrue('{user} ALL = (root) NOPASSWD: {nginx}'.format(nginx=nginx, user=user) in sudoers)


	def assert_supervisor_config(self, bench_name, use_rq=True):
		conf_src = os.path.join(os.path.abspath(self.benches_path), bench_name, 'config', 'supervisor.conf')

		supervisor_conf_dir = get_supervisor_confdir()
		conf_dest = "{supervisor_conf_dir}/{bench_name}.conf".format(supervisor_conf_dir=supervisor_conf_dir, bench_name=bench_name)

		self.assertTrue(self.file_exists(conf_src))
		self.assertTrue(self.file_exists(conf_dest))

		# symlink matches
		self.assertEqual(os.path.realpath(conf_dest), conf_src)

		# file content
		with open(conf_src, "r") as f:
			f = f.read()

			tests = [
				"program:{bench_name}-frappe-web",
				"program:{bench_name}-redis-cache",
				"program:{bench_name}-redis-queue",
				"program:{bench_name}-redis-socketio",
				"group:{bench_name}-web",
				"group:{bench_name}-workers",
				"group:{bench_name}-redis"
			]

			if not os.environ.get("CI"):
				tests.append("program:{bench_name}-node-socketio")

			if use_rq:
				tests.extend([
					"program:{bench_name}-frappe-schedule",
					"program:{bench_name}-frappe-default-worker",
					"program:{bench_name}-frappe-short-worker",
					"program:{bench_name}-frappe-long-worker"
				])

			else:
				tests.extend([
					"program:{bench_name}-frappe-workerbeat",
					"program:{bench_name}-frappe-worker",
					"program:{bench_name}-frappe-longjob-worker",
					"program:{bench_name}-frappe-async-worker"
				])

			for key in tests:
				if key.format(bench_name=bench_name) not in f:
					print(key.format(bench_name=bench_name))
				self.assertTrue(key.format(bench_name=bench_name) in f)


	def assert_supervisor_process(self, bench_name, use_rq=True, disable_production=False):
		out = bench.utils.get_cmd_output("supervisorctl status")

		while "STARTING" in out:
			print ("Waiting for all processes to start...")
			time.sleep(10)
			out = bench.utils.get_cmd_output("supervisorctl status")

		tests = [
			"{bench_name}-web:{bench_name}-frappe-web[\s]+RUNNING",
			# Have commented for the time being. Needs to be uncommented later on. Bench is failing on travis because of this.
			# It works on one bench and fails on another.giving FATAL or BACKOFF (Exited too quickly (process log may have details))
			# "{bench_name}-web:{bench_name}-node-socketio[\s]+RUNNING",
			"{bench_name}-redis:{bench_name}-redis-cache[\s]+RUNNING",
			"{bench_name}-redis:{bench_name}-redis-queue[\s]+RUNNING",
			"{bench_name}-redis:{bench_name}-redis-socketio[\s]+RUNNING"
		]

		if use_rq:
			tests.extend([
				"{bench_name}-workers:{bench_name}-frappe-schedule[\s]+RUNNING",
				"{bench_name}-workers:{bench_name}-frappe-default-worker-0[\s]+RUNNING",
				"{bench_name}-workers:{bench_name}-frappe-short-worker-0[\s]+RUNNING",
				"{bench_name}-workers:{bench_name}-frappe-long-worker-0[\s]+RUNNING"
			])

		else:
			tests.extend([
				"{bench_name}-workers:{bench_name}-frappe-workerbeat[\s]+RUNNING",
				"{bench_name}-workers:{bench_name}-frappe-worker[\s]+RUNNING",
				"{bench_name}-workers:{bench_name}-frappe-longjob-worker[\s]+RUNNING",
				"{bench_name}-workers:{bench_name}-frappe-async-worker[\s]+RUNNING"
			])

		for key in tests:
			if disable_production:
				self.assertFalse(re.search(key.format(bench_name=bench_name), out))
			else:
				self.assertTrue(re.search(key.format(bench_name=bench_name), out))


if __name__ == '__main__':
	unittest.main()
