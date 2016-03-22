from __future__ import unicode_literals
from bench.tests import test_init
from bench.config.production_setup import setup_production, get_supervisor_confdir
import bench.utils
import os
import getpass
import re
import unittest
import time

class TestSetupProduction(test_init.TestBenchInit):
	# setUp, tearDown and other tests are defiend in TestBenchInit

	def test_setup_production(self):
		self.test_multiple_benches()

		user = getpass.getuser()

		for bench_name in ("test-bench-1", "test-bench-2"):
			bench_path = os.path.join(os.path.abspath(self.benches_path), bench_name)
			setup_production(user, bench_path)
			self.assert_nginx_config(bench_name)
			self.assert_supervisor_config(bench_name)

		# test after start of both benches
		for bench_name in ("test-bench-1", "test-bench-2"):
			self.assert_supervisor_process(bench_name)

		self.assert_nginx_process()

	def assert_nginx_config(self, bench_name):
		conf_src = os.path.join(os.path.abspath(self.benches_path), bench_name, 'config', 'nginx.conf')
		conf_dest = "/etc/nginx/conf.d/{bench_name}.conf".format(bench_name=bench_name)

		self.assertTrue(os.path.exists(conf_src))
		self.assertTrue(os.path.exists(conf_dest))

		# symlink matches
		self.assertEquals(os.path.realpath(conf_dest), conf_src)

		# file content
		with open(conf_src, "r") as f:
			f = f.read().decode("utf-8")

			for key in (
					"upstream {bench_name}-frappe",
					"upstream {bench_name}-socketio-server"
				):
				self.assertTrue(key.format(bench_name=bench_name) in f)

	def assert_supervisor_config(self, bench_name):
		conf_src = os.path.join(os.path.abspath(self.benches_path), bench_name, 'config', 'supervisor.conf')

		supervisor_conf_dir = get_supervisor_confdir()
		conf_dest = "{supervisor_conf_dir}/{bench_name}.conf".format(supervisor_conf_dir=supervisor_conf_dir, bench_name=bench_name)

		self.assertTrue(os.path.exists(conf_src))
		self.assertTrue(os.path.exists(conf_dest))

		# symlink matches
		self.assertEquals(os.path.realpath(conf_dest), conf_src)

		# file content
		with open(conf_src, "r") as f:
			f = f.read().decode("utf-8")

			for key in (
					"program:{bench_name}-frappe-web",
					"program:{bench_name}-frappe-worker",
					"program:{bench_name}-frappe-longjob-worker",
					"program:{bench_name}-frappe-async-worker",
					"program:{bench_name}-frappe-workerbeat",
					"program:{bench_name}-redis-cache",
					"program:{bench_name}-redis-queue",
					"program:{bench_name}-redis-socketio",
					"program:{bench_name}-node-socketio",
					"group:{bench_name}-processes",
					"group:{bench_name}-redis"
				):
				self.assertTrue(key.format(bench_name=bench_name) in f)

	def assert_supervisor_process(self, bench_name):
		out = bench.utils.get_cmd_output("sudo supervisorctl status")

		if "STARTING" in out:
			time.sleep(10)
			out = bench.utils.get_cmd_output("sudo supervisorctl status")

		for key in (
				"{bench_name}-processes:{bench_name}-frappe-web[\s]+RUNNING",
				"{bench_name}-processes:{bench_name}-frappe-worker[\s]+RUNNING",
				"{bench_name}-processes:{bench_name}-frappe-longjob-worker[\s]+RUNNING",
				"{bench_name}-processes:{bench_name}-frappe-async-worker[\s]+RUNNING",
				"{bench_name}-processes:{bench_name}-frappe-workerbeat[\s]+RUNNING",
				"{bench_name}-processes:{bench_name}-node-socketio[\s]+RUNNING",
				"{bench_name}-redis:{bench_name}-redis-cache[\s]+RUNNING",
				"{bench_name}-redis:{bench_name}-redis-queue[\s]+RUNNING",
				"{bench_name}-redis:{bench_name}-redis-socketio[\s]+RUNNING",
			):
			self.assertTrue(re.search(key.format(bench_name=bench_name), out))

	def assert_nginx_process(self):
		out = bench.utils.get_cmd_output("sudo nginx -t 2>&1")
		self.assertTrue("nginx: configuration file /etc/nginx/nginx.conf test is successful" in out)


