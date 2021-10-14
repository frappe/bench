import os
import shutil
import sys
import logging
from typing import MutableSequence

import bench
from bench.utils import remove_backups_crontab, folders_in_bench, get_venv_path, exec_cmd, get_env_cmd
from bench.config.common_site_config import setup_config


logger = logging.getLogger(bench.PROJECT_NAME)


class Base:
	def run(self, cmd):
		return exec_cmd(cmd, cwd=self.cwd)


class Bench(Base):
	def __init__(self, path):
		self.name = path
		self.cwd = os.path.abspath(path)
		self.exists = os.path.exists(self.name)
		self.setup = BenchSetup(self)
		self.teardown = BenchTearDown(self)
		self.apps = BenchApps(self)

	@property
	def sites(self):
		return [
			path for path in os.listdir(os.path.join(self.name, 'sites'))
			if os.path.exists(
				os.path.join("sites", path, "site_config.json")
			)
		]

	@property
	def conf(self):
		from bench.config.common_site_config import get_config
		return get_config(self.name)

	def init(self):
		self.setup.dirs()
		self.setup.env()
		self.setup.backups()

	def drop(self):
		self.teardown.backups()
		self.teardown.dirs()

	def get_app(self, app, version=None):
		pass

	def drop_app(self, app, version=None):
		pass

	def install(self, app, branch=None):
		from bench.app import App

		app = App(app, branch=branch)

		# get app?
		# install app to env
		# add to apps.txt
		return

	def uninstall(self, app):
		# remove from apps.txt
		# uninstall app from env
		# remove app?
		return


class BenchApps(MutableSequence):
	def __init__(self, bench : Bench):
		self.bench = bench
		self.initialize_apps()

	def initialize_apps(self):
		try:
			self.apps = open(
				os.path.join(self.bench.name, "sites", "apps.txt")
			).read().splitlines()
		except FileNotFoundError:
			self.apps = []

	def __getitem__(self, key):
		''' retrieves an item by its index, key'''
		return self.apps[key]

	def __setitem__(self, key, value):
		''' set the item at index, key, to value '''
		# should probably not be allowed
		# self.apps[key] = value
		raise NotImplementedError

	def __delitem__(self, key):
		''' removes the item at index, key '''
		# TODO: uninstall and delete app from bench
		del self.apps[key]

	def __len__(self):
		return len(self.apps)

	def insert(self, key, value):
		''' add an item, value, at index, key. '''
		# TODO: fetch and install app to bench
		self.apps.insert(key, value)

	def __repr__(self):
		return self.__str__()

	def __str__(self):
		return str([x for x in self.apps])


class BenchSetup(Base):
	def __init__(self, bench : Bench):
		self.bench = bench
		self.cwd = self.bench.cwd

	def dirs(self):
		os.makedirs(self.bench.name, exist_ok=True)

		for dirname in folders_in_bench:
			os.makedirs(os.path.join(self.bench.name, dirname), exist_ok=True)

	def env(self, python="python3"):
		"""Setup env folder
		- create env if not exists
		- upgrade env pip
		- install frappe python dependencies
		"""
		frappe = os.path.join(self.bench.name, "apps", "frappe")
		env_python = get_env_cmd("python", bench_path=self.bench.name)
		virtualenv = get_venv_path()

		if not os.path.exists(env_python):
			self.run(f"{virtualenv} -q env -p {python}")

		self.run(f"{env_python} -m pip install -q -U pip")

		if os.path.exists(frappe):
			self.run(f"{env_python} -m pip install -q -U -e {frappe}")

	def config(self, redis=True, procfile=True):
		"""Setup config folder
		- create pids folder
		- generate sites/common_site_config.json
		"""
		setup_config(self.bench.name)

		if redis:
			from bench.config.redis import generate_config
			generate_config(self.bench.name)

		if procfile:
			from bench.config.procfile import setup_procfile
			setup_procfile(self.bench.name, skip_redis=not redis)

	def logging(self):
		from bench.utils import setup_logging
		return setup_logging(bench_path=self.bench.name)

	def patches(self):
		import shutil

		shutil.copy(
			os.path.join(os.path.dirname(os.path.abspath(__file__)), 'patches', 'patches.txt'),
			os.path.join(self.bench.name, 'patches.txt')
		)

	def backups(self):
		# TODO: to something better for logging data? - maybe a wrapper that auto-logs with more context
		logger.log('setting up backups')

		from crontab import CronTab

		bench_dir = os.path.abspath(self.bench.name)
		user = self.bench.conf.get('frappe_user')
		logfile = os.path.join(bench_dir, 'logs', 'backup.log')
		system_crontab = CronTab(user=user)
		backup_command = f"cd {bench_dir} && {sys.argv[0]} --verbose --site all backup"
		job_command = f"{backup_command} >> {logfile} 2>&1"

		if job_command not in str(system_crontab):
			job = system_crontab.new(command=job_command, comment="bench auto backups set for every 6 hours")
			job.every(6).hours()
			system_crontab.write()

		logger.log('backups were set up')


class BenchTearDown:
	def __init__(self, bench):
		self.bench = bench

	def backups(self):
		remove_backups_crontab(self.bench.name)

	def dirs(self):
		shutil.rmtree(self.bench.name)
