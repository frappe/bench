# imports - standard imports
import functools
import os
import shutil
import sys
import logging
from typing import List, MutableSequence, TYPE_CHECKING

# imports - module imports
import bench
from bench.exceptions import ValidationError
from bench.config.common_site_config import setup_config
from bench.utils import (
	paths_in_bench,
	exec_cmd,
	is_bench_directory,
	is_frappe_app,
	get_cmd_output,
	get_git_version,
	log,
	run_frappe_cmd,
)
from bench.utils.bench import (
	validate_app_installed_on_sites,
	restart_supervisor_processes,
	restart_systemd_processes,
	restart_process_manager,
	remove_backups_crontab,
	get_venv_path,
	get_env_cmd,
)
from bench.utils.render import job, step


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


@functools.lru_cache(maxsize=None)
class Bench(Base, Validator):
	def __init__(self, path):
		self.name = path
		self.cwd = os.path.abspath(path)
		self.exists = is_bench_directory(self.name)

		self.setup = BenchSetup(self)
		self.teardown = BenchTearDown(self)
		self.apps = BenchApps(self)

		self.apps_txt = os.path.join(self.name, "sites", "apps.txt")
		self.excluded_apps_txt = os.path.join(self.name, "sites", "excluded_apps.txt")

	@property
	def python(self) -> str:
		return get_env_cmd("python", bench_path=self.name)

	@property
	def shallow_clone(self) -> bool:
		config = self.conf

		if config:
			if config.get("release_bench") or not config.get("shallow_clone"):
				return False

		return get_git_version() > 1.9

	@property
	def excluded_apps(self) -> List:
		try:
			with open(self.excluded_apps_txt) as f:
				return f.read().strip().split("\n")
		except Exception:
			return []

	@property
	def sites(self) -> List:
		return [
			path
			for path in os.listdir(os.path.join(self.name, "sites"))
			if os.path.exists(os.path.join("sites", path, "site_config.json"))
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

	def install(self, app, branch=None):
		from bench.app import App

		app = App(app, branch=branch)
		self.apps.append(app)
		self.apps.sync()

	def uninstall(self, app):
		from bench.app import App

		self.validate_app_uninstall(app)
		self.apps.remove(App(app, bench=self, to_clone=False))
		self.apps.sync()
		# self.build() - removed because it seems unnecessary
		self.reload()

	@step(title="Building Bench Assets", success="Bench Assets Built")
	def build(self):
		# build assets & stuff
		run_frappe_cmd("build", bench_path=self.name)

	@step(title="Reloading Bench Processes", success="Bench Processes Reloaded")
	def reload(self, web=False, supervisor=True, systemd=True):
		"""If web is True, only web workers are restarted
		"""
		conf = self.conf

		if conf.get("developer_mode"):
			restart_process_manager(bench_path=self.name, web_workers=web)
		if supervisor and conf.get("restart_supervisor_on_update"):
			restart_supervisor_processes(bench_path=self.name, web_workers=web)
		if systemd and conf.get("restart_systemd_on_update"):
			restart_systemd_processes(bench_path=self.name, web_workers=web)


class BenchApps(MutableSequence):
	def __init__(self, bench: Bench):
		self.bench = bench
		self.initialize_apps()

	def sync(self):
		self.initialize_apps()
		with open(self.bench.apps_txt, "w") as f:
			return f.write("\n".join(self.apps))

	def initialize_apps(self):
		is_installed = lambda app: app in installed_packages

		try:
			installed_packages = get_cmd_output(f"{self.bench.python} -m pip freeze", cwd=self.bench.name)
		except Exception:
			self.apps = []
			return

		try:
			self.apps = [
				x
				for x in os.listdir(os.path.join(self.bench.name, "apps"))
				if (
					is_frappe_app(os.path.join(self.bench.name, "apps", x))
					and is_installed(x)
				)
			]
			self.apps.sort()
		except FileNotFoundError:
			self.apps = []

	def __getitem__(self, key):
		""" retrieves an item by its index, key"""
		return self.apps[key]

	def __setitem__(self, key, value):
		""" set the item at index, key, to value """
		# should probably not be allowed
		# self.apps[key] = value
		raise NotImplementedError

	def __delitem__(self, key):
		""" removes the item at index, key """
		# TODO: uninstall and delete app from bench
		del self.apps[key]

	def __len__(self):
		return len(self.apps)

	def insert(self, key, value):
		""" add an item, value, at index, key. """
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

	def append(self, app: "App"):
		return self.add(app)

	def __repr__(self):
		return self.__str__()

	def __str__(self):
		return str([x for x in self.apps])


class BenchSetup(Base):
	def __init__(self, bench: Bench):
		self.bench = bench
		self.cwd = self.bench.cwd

	@step(title="Setting Up Directories", success="Directories Set Up")
	def dirs(self):
		os.makedirs(self.bench.name, exist_ok=True)

		for dirname in paths_in_bench:
			os.makedirs(os.path.join(self.bench.name, dirname), exist_ok=True)

	@step(title="Setting Up Environment", success="Environment Set Up")
	def env(self, python="python3"):
		"""Setup env folder
		- create env if not exists
		- upgrade env pip
		- install frappe python dependencies
		"""
		import bench.cli

		frappe = os.path.join(self.bench.name, "apps", "frappe")
		virtualenv = get_venv_path()
		quiet_flag = "" if bench.cli.verbose else "--quiet"

		if not os.path.exists(self.bench.python):
			self.run(f"{virtualenv} {quiet_flag} env -p {python}")

		self.pip()

		if os.path.exists(frappe):
			self.run(f"{self.bench.python} -m pip install {quiet_flag} --upgrade -e {frappe}")

	@step(title="Setting Up Bench Config", success="Bench Config Set Up")
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

	@step(title="Updating pip", success="Updated pip")
	def pip(self, verbose=False):
		"""Updates env pip; assumes that env is setup
		"""
		import bench.cli

		verbose = bench.cli.verbose or verbose
		quiet_flag = "" if verbose else "--quiet"

		return self.run(f"{self.bench.python} -m pip install {quiet_flag} --upgrade pip")

	def logging(self):
		from bench.utils import setup_logging

		return setup_logging(bench_path=self.bench.name)

	@step(title="Setting Up Bench Patches", success="Bench Patches Set Up")
	def patches(self):
		shutil.copy(
			os.path.join(os.path.dirname(os.path.abspath(__file__)), "patches", "patches.txt"),
			os.path.join(self.bench.name, "patches.txt"),
		)

	@step(title="Setting Up Backups Cronjob", success="Backups Cronjob Set Up")
	def backups(self):
		# TODO: to something better for logging data? - maybe a wrapper that auto-logs with more context
		logger.log("setting up backups")

		from crontab import CronTab

		bench_dir = os.path.abspath(self.bench.name)
		user = self.bench.conf.get("frappe_user")
		logfile = os.path.join(bench_dir, "logs", "backup.log")
		system_crontab = CronTab(user=user)
		backup_command = f"cd {bench_dir} && {sys.argv[0]} --verbose --site all backup"
		job_command = f"{backup_command} >> {logfile} 2>&1"

		if job_command not in str(system_crontab):
			job = system_crontab.new(
				command=job_command, comment="bench auto backups set for every 6 hours"
			)
			job.every(6).hours()
			system_crontab.write()

		logger.log("backups were set up")

	def __get_installed_apps(self) -> List:
		"""Returns list of installed apps on bench, not in excluded_apps.txt
		"""
		apps = [app for app in self.bench.apps if app not in self.bench.excluded_apps]
		apps.remove("frappe")
		apps.insert(0, "frappe")
		return apps

	@job(title="Setting Up Bench Dependencies", success="Bench Dependencies Set Up")
	def requirements(self):
		"""Install and upgrade all installed apps on given Bench
		"""
		from bench.app import App

		apps = self.__get_installed_apps()

		self.pip()

		print(f"Installing {len(apps)} applications...")

		for app in apps:
			App(app, bench=self.bench, to_clone=False).install()

	def python(self):
		"""Install and upgrade Python dependencies for installed apps on given Bench
		"""
		import bench.cli

		apps = self.__get_installed_apps()

		quiet_flag = "" if bench.cli.verbose else "--quiet"

		self.pip()

		for app in apps:
			app_path = os.path.join(self.bench.name, "apps", app)
			log(f"\nInstalling python dependencies for {app}", level=3, no_log=True)
			self.run(f"{self.bench.python} -m pip install {quiet_flag} --upgrade -e {app_path}")

	def node(self):
		"""Install and upgrade Node dependencies for all apps on given Bench
		"""
		from bench.utils.bench import update_node_packages

		return update_node_packages(bench_path=self.bench.name)


class BenchTearDown:
	def __init__(self, bench):
		self.bench = bench

	def backups(self):
		remove_backups_crontab(self.bench.name)

	def dirs(self):
		shutil.rmtree(self.bench.name)
