import os
import shutil
import sys
import logging
from typing import MutableSequence, TYPE_CHECKING

import bench
from bench.exceptions import ValidationError
from bench.config.common_site_config import setup_config
from bench.utils import paths_in_bench, exec_cmd, is_frappe_app, get_git_version, run_frappe_cmd
from bench.utils.bench import validate_app_installed_on_sites, restart_supervisor_processes, restart_systemd_processes, remove_backups_crontab, get_venv_path, get_env_cmd


if TYPE_CHECKING:
	from bench.app import App

logger = logging.getLogger(bench.PROJECT_NAME)


class Base:
	def run(self, cmd, cwd=None):
		return exec_cmd(cmd, cwd=cwd or self.cwd)


class Validator:
	def validate_app_uninstall(self, app):
		if app not in self.apps:
			raise ValidationError(f"No app named {app}")
		validate_app_installed_on_sites(app, bench_path=self.name)


class Bench(Base, Validator):
	def __init__(self, path):
		self.name = path
		self.cwd = os.path.abspath(path)
		self.exists = os.path.exists(self.name)

		self.setup = BenchSetup(self)
		self.teardown = BenchTearDown(self)
		self.apps = BenchApps(self)

		self.apps_txt = os.path.join(self.name, 'sites', 'apps.txt')
		self.excluded_apps_txt = os.path.join(self.name, 'sites', 'excluded_apps.txt')

	@property
	def shallow_clone(self):
		config = self.conf

		if config:
			if config.get('release_bench') or not config.get('shallow_clone'):
				return False

		if get_git_version() > 1.9:
			return True

	@property
	def excluded_apps(self):
		try:
			with open(self.excluded_apps_txt) as f:
				return f.read().strip().split('\n')
		except Exception:
			return []

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
		self.apps.append(app)
		self.apps.sync()

	def uninstall(self, app):
		from bench.app import App

		self.validate_app_uninstall(app)
		self.apps.remove(App(app, bench=self))
		self.apps.sync()
		self.build()
		self.reload()

	def build(self):
		# build assets & stuff
		run_frappe_cmd("build", bench_path=self.name)

	def reload(self):
		conf = self.conf
		if conf.get('restart_supervisor_on_update'):
			restart_supervisor_processes(bench_path=self.name)
		if conf.get('restart_systemd_on_update'):
			restart_systemd_processes(bench_path=self.name)


class BenchApps(MutableSequence):
	def __init__(self, bench : Bench):
		self.bench = bench
		self.initialize_apps()

	def sync(self):
		self.initialize_apps()
		with open(self.bench.apps_txt, "w") as f:
			return f.write("\n".join(self.apps))

	def initialize_apps(self):
		try:
			self.apps = [x for x in os.listdir(
				os.path.join(self.bench.name, "apps")
			) if is_frappe_app(os.path.join(self.bench.name, "apps", x))]
			self.apps.sort()
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

	def add(self, app: "App"):
		app.get()
		app.install()
		super().append(app.repo)
		self.apps.sort()

	def remove(self, app: "App"):
		app.uninstall()
		app.remove()
		super().remove(app.repo)

	def append(self, app : "App"):
		return self.add(app)

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

		for dirname in paths_in_bench:
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
