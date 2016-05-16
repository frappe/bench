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

		# sudoers
		bench.utils.setup_sudoers(user)
		self.assert_sudoers(user)

	def test_setup_production_v6(self):
		bench_name = 'test-bench-v6'
		self.test_init(bench_name, frappe_branch='master')

		user = getpass.getuser()

		bench_path = os.path.join(os.path.abspath(self.benches_path), bench_name)
		setup_production(user, bench_path)

		self.assert_nginx_config(bench_name)
		self.assert_nginx_process()

		self.assert_supervisor_config(bench_name, use_rq=False)
		self.assert_supervisor_process(bench_name, use_rq=False)

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

	def assert_nginx_process(self):
		out = bench.utils.get_cmd_output("sudo nginx -t 2>&1")
		self.assertTrue("nginx: configuration file /etc/nginx/nginx.conf test is successful" in out)

	def assert_sudoers(self, user):
		sudoers_file = '/etc/sudoers.d/frappe'
		self.assertTrue(os.path.exists(sudoers_file))

		with open(sudoers_file, 'r') as f:
			sudoers = f.read().decode('utf-8')

		self.assertTrue('{user} ALL = (root) NOPASSWD: /usr/sbin/service nginx *'.format(user=user) in sudoers)
		self.assertTrue('{user} ALL = (root) NOPASSWD: /usr/bin/supervisorctl'.format(user=user) in sudoers)
		self.assertTrue('{user} ALL = (root) NOPASSWD: /usr/sbin/nginx'.format(user=user) in sudoers)

	def assert_supervisor_config(self, bench_name, use_rq=True):
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

			tests = [
				"program:{bench_name}-frappe-web",
				"program:{bench_name}-redis-cache",
				"program:{bench_name}-redis-queue",
				"program:{bench_name}-redis-socketio",
				"program:{bench_name}-node-socketio",
				"group:{bench_name}-web",
				"group:{bench_name}-workers",
				"group:{bench_name}-redis"
			]

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
				self.assertTrue(key.format(bench_name=bench_name) in f)

	def assert_supervisor_process(self, bench_name, use_rq=True):
		out = bench.utils.get_cmd_output("sudo supervisorctl status")

		if "STARTING" in out:
			time.sleep(10)
			out = bench.utils.get_cmd_output("sudo supervisorctl status")

		tests = [
			"{bench_name}-web:{bench_name}-frappe-web[\s]+RUNNING",
			"{bench_name}-web:{bench_name}-node-socketio[\s]+RUNNING",
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
			self.assertTrue(re.search(key.format(bench_name=bench_name), out))



