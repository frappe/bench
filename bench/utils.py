#!/usr/bin/env python
# -*- coding: utf-8 -*-

# imports - standard imports
import errno
import glob
import grp
import itertools
import json
import logging
import multiprocessing
import os
import pwd
import re
import select
import shutil
import site
import subprocess
import sys
from datetime import datetime
from distutils.spawn import find_executable

# imports - third party imports
import click
from crontab import CronTab
import requests
from semantic_version import Version
from six import iteritems
from six.moves.urllib.parse import urlparse

# imports - module imports
import bench


class PatchError(Exception):
	pass

class CommandFailedError(Exception):
	pass

logger = logging.getLogger(bench.PROJECT_NAME)
bench_cache_file = '.bench.cmd'
folders_in_bench = ('apps', 'sites', 'config', 'logs', 'config/pids')
sudoers_file = '/etc/sudoers.d/frappe'


class color:
	nc = '\033[0m'
	blue = '\033[94m'
	green = '\033[92m'
	yellow = '\033[93m'
	red = '\033[91m'
	silver = '\033[90m'


def is_bench_directory(directory=os.path.curdir):
	is_bench = True

	for folder in folders_in_bench:
		path = os.path.abspath(os.path.join(directory, folder))
		is_bench = is_bench and os.path.exists(path)

	return is_bench


def log(message, level=0):
	levels = {
		0: color.blue + 'INFO',			# normal
		1: color.green + 'SUCCESS',		# success
		2: color.red + 'ERROR',			# fail
		3: color.yellow + 'WARN'		# warn/suggest
	}
	loggers = {
		2: logger.error,
		3: logger.warning
	}

	start_line = (levels.get(level) + ': ') if level in levels else ''
	level_logger = loggers.get(level, logger.info)
	end_line = '\033[0m'

	level_logger(message)
	print(start_line + message + end_line)


def safe_decode(string, encoding = 'utf-8'):
	try:
		string = string.decode(encoding)
	except Exception:
		pass
	return string


def check_latest_version():
	try:
		pypi_request = requests.get("https://pypi.org/pypi/frappe-bench/json")
	except Exception:
		# Exceptions thrown are defined in requests.exceptions
		# ignore checking on all Exceptions
		return

	if pypi_request.status_code == 200:
		pypi_version_str = pypi_request.json().get('info').get('version')
		pypi_version = Version(pypi_version_str)
		local_version = Version(bench.VERSION)

		if pypi_version > local_version:
			log("A newer version of bench is available: {0} → {1}".format(local_version, pypi_version))


def get_frappe(bench_path='.'):
	frappe = get_env_cmd('frappe', bench_path=bench_path)
	if not os.path.exists(frappe):
		print('frappe app is not installed. Run the following command to install frappe')
		print('bench get-app https://github.com/frappe/frappe.git')
	return frappe


def get_env_cmd(cmd, bench_path='.'):
	return os.path.abspath(os.path.join(bench_path, 'env', 'bin', cmd))


def init(path, apps_path=None, no_procfile=False, no_backups=False,
		frappe_path=None, frappe_branch=None, verbose=False, clone_from=None,
		skip_redis_config_generation=False, clone_without_update=False, ignore_exist=False, skip_assets=False,
		python='python3'):
	"""Initialize a new bench directory"""
	from bench.app import get_app, install_apps_from_path
	from bench.config import redis
	from bench.config.common_site_config import make_config
	from bench.config.procfile import setup_procfile
	from bench.patches import set_all_patches_executed

	if os.path.exists(path) and not ignore_exist:
		log('Path {path} already exists!'.format(path=path))
		sys.exit(0)
	elif not os.path.exists(path):
		# only create dir if it does not exist
		os.makedirs(path)

	for dirname in folders_in_bench:
		try:
			os.makedirs(os.path.join(path, dirname))
		except OSError as e:
			if e.errno == errno.EEXIST:
				pass

	setup_logging(bench_path=path)

	setup_env(bench_path=path, python=python)

	make_config(path)

	if clone_from:
		clone_apps_from(bench_path=path, clone_from=clone_from, update_app=not clone_without_update)
	else:
		if not frappe_path:
			frappe_path = 'https://github.com/frappe/frappe.git'

		get_app(frappe_path, branch=frappe_branch, bench_path=path, skip_assets=True, verbose=verbose)

		if apps_path:
			install_apps_from_path(apps_path, bench_path=path)


	bench.set_frappe_version(bench_path=path)
	if bench.FRAPPE_VERSION > 5:
		if not skip_assets:
			update_node_packages(bench_path=path)

	set_all_patches_executed(bench_path=path)
	if not skip_assets:
		build_assets(bench_path=path)

	if not skip_redis_config_generation:
		redis.generate_config(path)

	if not no_procfile:
		setup_procfile(path, skip_redis=skip_redis_config_generation)
	if not no_backups:
		setup_backups(bench_path=path)

	copy_patches_txt(path)


def update(pull=False, apps=None, patch=False, build=False, requirements=False, backup=True, force=False, reset=False,
	restart_supervisor=False, restart_systemd=False):
	"""command: bench update"""
	from bench import patches
	from bench.app import is_version_upgrade, pull_apps, validate_branch
	from bench.config.common_site_config import get_config, update_config

	bench_path = os.path.abspath(".")
	patches.run(bench_path=bench_path)
	conf = get_config(bench_path)

	if apps and not pull:
		apps = []

	clear_command_cache(bench_path='.')

	if conf.get('release_bench'):
		print('Release bench detected, cannot update!')
		sys.exit(1)

	if not (pull or patch or build or requirements):
		pull, patch, build, requirements = True, True, True, True

	validate_branch()
	version_upgrade = is_version_upgrade()

	if version_upgrade[0]:
		if force:
			print("Force flag has been used for a major version change in Frappe and it's apps. \nThis will take significant time to migrate and might break custom apps.")
		else:
			print("This update will cause a major version change in Frappe/ERPNext from {0} to {1}. \nThis would take significant time to migrate and might break custom apps.".format(*version_upgrade[1:]))
			click.confirm('Do you want to continue?', abort=True)

	if version_upgrade[0] or (not version_upgrade[0] and force):
		validate_upgrade(version_upgrade[1], version_upgrade[2], bench_path=bench_path)

	conf.update({ "maintenance_mode": 1, "pause_scheduler": 1 })
	update_config(conf, bench_path=bench_path)

	if backup:
		print('Backing up sites...')
		backup_all_sites(bench_path=bench_path)

	if apps:
		apps = [app.strip() for app in re.split(",| ", apps) if app]

	if pull:
		pull_apps(apps=apps, bench_path=bench_path, reset=reset)

	if requirements:
		update_requirements(bench_path=bench_path)
		update_node_packages(bench_path=bench_path)

	if patch:
		print('Patching sites...')
		patch_sites(bench_path=bench_path)

	if build:
		build_assets(bench_path=bench_path)

	if version_upgrade[0] or (not version_upgrade[0] and force):
		post_upgrade(version_upgrade[1], version_upgrade[2], bench_path=bench_path)

	if restart_supervisor or conf.get('restart_supervisor_on_update'):
		restart_supervisor_processes(bench_path=bench_path)

	if restart_systemd or conf.get('restart_systemd_on_update'):
		restart_systemd_processes(bench_path=bench_path)

	conf.update({ "maintenance_mode": 0, "pause_scheduler": 0 })
	update_config(conf, bench_path=bench_path)

	print("_" * 80 + "\nBench: Deployment tool for Frappe and Frappe Applications (https://frappe.io/bench).\nOpen source depends on your contributions, so do give back by submitting bug reports, patches and fixes and be a part of the community :)")


def copy_patches_txt(bench_path):
	shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'patches', 'patches.txt'),
		os.path.join(bench_path, 'patches.txt'))


def clone_apps_from(bench_path, clone_from, update_app=True):
	from .app import install_app
	print('Copying apps from {0}...'.format(clone_from))
	subprocess.check_output(['cp', '-R', os.path.join(clone_from, 'apps'), bench_path])

	node_modules_path = os.path.join(clone_from, 'node_modules')
	if os.path.exists(node_modules_path):
		print('Copying node_modules from {0}...'.format(clone_from))
		subprocess.check_output(['cp', '-R', node_modules_path, bench_path])

	def setup_app(app):
		# run git reset --hard in each branch, pull latest updates and install_app
		app_path = os.path.join(bench_path, 'apps', app)

		# remove .egg-ino
		subprocess.check_output(['rm', '-rf', app + '.egg-info'], cwd=app_path)

		if update_app and os.path.exists(os.path.join(app_path, '.git')):
			remotes = subprocess.check_output(['git', 'remote'], cwd=app_path).strip().split()
			if 'upstream' in remotes:
				remote = 'upstream'
			else:
				remote = remotes[0]
			print('Cleaning up {0}'.format(app))
			branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=app_path).strip()
			subprocess.check_output(['git', 'reset', '--hard'], cwd=app_path)
			subprocess.check_output(['git', 'pull', '--rebase', remote, branch], cwd=app_path)

		install_app(app, bench_path, restart_bench=False)

	with open(os.path.join(clone_from, 'sites', 'apps.txt'), 'r') as f:
		apps = f.read().splitlines()

	for app in apps:
		setup_app(app)


def exec_cmd(cmd, cwd='.'):
	import shlex
	print("{0}$ {1}{2}".format(color.silver, cmd, color.nc))
	cwd_info = "cd {0} && ".format(cwd) if cwd != "." else ""
	cmd_log = "{0}{1}".format(cwd_info, cmd)
	logger.debug(cmd_log)
	cmd = shlex.split(cmd)
	return_code = subprocess.call(cmd, cwd=cwd, universal_newlines=True)
	if return_code:
		logger.warning("{0} executed with exit code {1}".format(cmd_log, return_code))


def which(executable, raise_err = False):
	exec_ = find_executable(executable)

	if not exec_ and raise_err:
		raise ValueError('{executable} not found.'.format(
			executable = executable
		))

	return exec_


def get_venv_path():
	venv = which('virtualenv')

	if not venv:
		current_python = sys.executable
		with open(os.devnull, "wb") as devnull:
			is_venv_installed = not subprocess.call([current_python, "-m", "venv", "--help"], stdout=devnull)
		if is_venv_installed:
			venv = "{} -m venv".format(current_python)

	return venv or log("virtualenv cannot be found", level=2)

def setup_env(bench_path='.', python='python3'):
	frappe = os.path.join(bench_path, "apps", "frappe")
	pip = os.path.join(bench_path, "env", "bin", "pip")
	virtualenv = get_venv_path()

	exec_cmd('{} -q env -p {}'.format(virtualenv, python), cwd=bench_path)

	if os.path.exists(frappe):
		exec_cmd('{} install -q -U -e {}'.format(pip, frappe), cwd=bench_path)


def setup_socketio(bench_path='.'):
	exec_cmd("npm install socket.io redis express superagent cookie babel-core less chokidar \
		babel-cli babel-preset-es2015 babel-preset-es2016 babel-preset-es2017 babel-preset-babili", cwd=bench_path)


def patch_sites(bench_path='.'):
	bench.set_frappe_version(bench_path=bench_path)

	try:
		if bench.FRAPPE_VERSION == 4:
			exec_cmd("{frappe} --latest all".format(frappe=get_frappe(bench_path=bench_path)), cwd=os.path.join(bench_path, 'sites'))
		else:
			run_frappe_cmd('--site', 'all', 'migrate', bench_path=bench_path)
	except subprocess.CalledProcessError:
		raise PatchError


def build_assets(bench_path='.', app=None):
	bench.set_frappe_version(bench_path=bench_path)

	if bench.FRAPPE_VERSION == 4:
		exec_cmd("{frappe} --build".format(frappe=get_frappe(bench_path=bench_path)), cwd=os.path.join(bench_path, 'sites'))
	else:
		command = 'bench build'
		if app:
			command += ' --app {}'.format(app)
		exec_cmd(command, cwd=bench_path)


def get_sites(bench_path='.'):
	sites_path = os.path.join(bench_path, 'sites')
	sites = (site for site in os.listdir(sites_path) if os.path.exists(os.path.join(sites_path, site, 'site_config.json')))
	return sites


def setup_backups(bench_path='.'):
	from bench.config.common_site_config import get_config
	logger.log('setting up backups')

	bench_dir = os.path.abspath(bench_path)
	user = get_config(bench_path=bench_dir).get('frappe_user')
	logfile = os.path.join(bench_dir, 'logs', 'backup.log')
	bench.set_frappe_version(bench_path=bench_path)
	system_crontab = CronTab(user=user)

	if bench.FRAPPE_VERSION == 4:
		backup_command = "cd {sites_dir} && {frappe} --backup all".format(frappe=get_frappe(bench_path=bench_path),)
	else:
		backup_command = "cd {bench_dir} && {bench} --verbose --site all backup".format(bench_dir=bench_dir, bench=sys.argv[0])

	job_command = "{backup_command} >> {logfile} 2>&1".format(backup_command=backup_command, logfile=logfile)

	if job_command not in str(system_crontab):
		job = system_crontab.new(command=job_command, comment="bench auto backups set for every 6 hours")
		job.every(6).hours()
		system_crontab.write()


def setup_sudoers(user):
	if not os.path.exists('/etc/sudoers.d'):
		os.makedirs('/etc/sudoers.d')

		set_permissions = False
		if not os.path.exists('/etc/sudoers'):
			set_permissions = True

		with open('/etc/sudoers', 'a') as f:
			f.write('\n#includedir /etc/sudoers.d\n')

		if set_permissions:
			os.chmod('/etc/sudoers', 0o440)

	template = bench.config.env.get_template('frappe_sudoers')
	frappe_sudoers = template.render(**{
		'user': user,
		'service': find_executable('service'),
		'systemctl': find_executable('systemctl'),
		'nginx': find_executable('nginx'),
	})
	frappe_sudoers = safe_decode(frappe_sudoers)

	with open(sudoers_file, 'w') as f:
		f.write(frappe_sudoers)

	os.chmod(sudoers_file, 0o440)
	log("Sudoers was set up for user {}".format(user), level=1)


def setup_logging(bench_path='.'):
	LOG_LEVEL = 15
	logging.addLevelName(LOG_LEVEL, "LOG")
	def logv(self, message, *args, **kws):
		if self.isEnabledFor(LOG_LEVEL):
			self._log(LOG_LEVEL, message, args, **kws)
	logging.Logger.log = logv

	if os.path.exists(os.path.join(bench_path, 'logs')):
		logger = logging.getLogger(bench.PROJECT_NAME)
		log_file = os.path.join(bench_path, 'logs', 'bench.log')
		formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
		hdlr = logging.FileHandler(log_file)
		hdlr.setFormatter(formatter)
		logger.addHandler(hdlr)
		logger.setLevel(logging.DEBUG)

		return logger


def get_process_manager():
	for proc_man in ['honcho', 'foreman', 'forego']:
		proc_man_path = find_executable(proc_man)
		if proc_man_path:
			return proc_man_path


def start(no_dev=False, concurrency=None, procfile=None, no_prefix=False):
	program = get_process_manager()
	if not program:
		raise Exception("No process manager found")
	os.environ['PYTHONUNBUFFERED'] = "true"
	if not no_dev:
		os.environ['DEV_SERVER'] = "true"

	command = [program, 'start']
	if concurrency:
		command.extend(['-c', concurrency])

	if procfile:
		command.extend(['-f', procfile])

	if no_prefix:
		command.extend(['--no-prefix'])
		
	os.execv(program, command)


def get_git_version():
	'''returns git version from `git --version`
	extracts version number from string `get version 1.9.1` etc'''
	version = get_cmd_output("git --version")
	version = safe_decode(version)
	version = version.strip().split()[2]
	version = '.'.join(version.split('.')[0:2])
	return float(version)


def check_git_for_shallow_clone():
	from .config.common_site_config import get_config
	config = get_config('.')

	if config:
		if config.get('release_bench'):
			return False

		if not config.get('shallow_clone'):
			return False

	git_version = get_git_version()
	if git_version > 1.9:
		return True


def get_cmd_output(cmd, cwd='.', _raise=True):
	output = ""
	try:
		output = subprocess.check_output(cmd, cwd=cwd, shell=True, stderr=subprocess.PIPE).strip()
	except subprocess.CalledProcessError as e:
		if e.output:
			output = e.output
		elif _raise:
			raise
	return safe_decode(output)


def restart_supervisor_processes(bench_path='.', web_workers=False):
	from .config.common_site_config import get_config
	conf = get_config(bench_path=bench_path)
	bench_name = get_bench_name(bench_path)

	cmd = conf.get('supervisor_restart_cmd')
	if cmd:
		exec_cmd(cmd, cwd=bench_path)

	else:
		supervisor_status = get_cmd_output('supervisorctl status', cwd=bench_path)
		supervisor_status = safe_decode(supervisor_status)

		if web_workers and '{bench_name}-web:'.format(bench_name=bench_name) in supervisor_status:
			group = '{bench_name}-web:	'.format(bench_name=bench_name)

		elif '{bench_name}-workers:'.format(bench_name=bench_name) in supervisor_status:
			group = '{bench_name}-workers: {bench_name}-web:'.format(bench_name=bench_name)

		# backward compatibility
		elif '{bench_name}-processes:'.format(bench_name=bench_name) in supervisor_status:
			group = '{bench_name}-processes:'.format(bench_name=bench_name)

		# backward compatibility
		else:
			group = 'frappe:'

		exec_cmd('supervisorctl restart {group}'.format(group=group), cwd=bench_path)


def restart_systemd_processes(bench_path='.', web_workers=False):
	bench_name = get_bench_name(bench_path)
	exec_cmd('sudo systemctl stop -- $(systemctl show -p Requires {bench_name}.target | cut -d= -f2)'.format(bench_name=bench_name))
	exec_cmd('sudo systemctl start -- $(systemctl show -p Requires {bench_name}.target | cut -d= -f2)'.format(bench_name=bench_name))


def set_default_site(site, bench_path='.'):
	if site not in get_sites(bench_path=bench_path):
		raise Exception("Site not in bench")
	exec_cmd("{frappe} --use {site}".format(frappe=get_frappe(bench_path=bench_path), site=site),
			cwd=os.path.join(bench_path, 'sites'))


def update_env_pip(bench_path):
	env_pip = os.path.join(bench_path, 'env', 'bin', 'pip')
	exec_cmd("{pip} install -q -U pip".format(pip=env_pip))


def update_requirements(bench_path='.'):
	from bench.app import get_apps, install_app
	print('Installing applications...')

	update_env_pip(bench_path)

	for app in get_apps():
		install_app(app, bench_path=bench_path, skip_assets=True, restart_bench=False)


def update_python_packages(bench_path='.'):
	from bench.app import get_apps
	pip_path = os.path.join(bench_path, "env", "bin", "pip")
	print('Updating Python libraries...')

	update_env_pip(bench_path)
	for app in get_apps():
		print('\n{0}Installing python dependencies for {1}{2}'.format(color.yellow, app, color.nc))
		app_path = os.path.join(bench_path, "apps", app)
		exec_cmd("{0} install -q -U -e {1}".format(pip_path, app_path), cwd=bench_path)


def update_node_packages(bench_path='.'):
	print('Updating node packages...')
	from bench.app import get_develop_version
	from distutils.version import LooseVersion
	v = LooseVersion(get_develop_version('frappe', bench_path = bench_path))

	# After rollup was merged, frappe_version = 10.1
	# if develop_verion is 11 and up, only then install yarn
	if v < LooseVersion('11.x.x-develop'):
		update_npm_packages(bench_path)
	else:
		update_yarn_packages(bench_path)


def update_yarn_packages(bench_path='.'):
	apps_dir = os.path.join(bench_path, 'apps')

	if not find_executable('yarn'):
		print("Please install yarn using below command and try again.")
		print("`npm install -g yarn`")
		return

	for app in os.listdir(apps_dir):
		app_path = os.path.join(apps_dir, app)
		if os.path.exists(os.path.join(app_path, 'package.json')):
			print('\n{0}Installing node dependencies for {1}{2}'.format(color.yellow, app, color.nc))
			exec_cmd('yarn install', cwd=app_path)


def update_npm_packages(bench_path='.'):
	apps_dir = os.path.join(bench_path, 'apps')
	package_json = {}

	for app in os.listdir(apps_dir):
		package_json_path = os.path.join(apps_dir, app, 'package.json')

		if os.path.exists(package_json_path):
			with open(package_json_path, "r") as f:
				app_package_json = json.loads(f.read())
				# package.json is usually a dict in a dict
				for key, value in iteritems(app_package_json):
					if not key in package_json:
						package_json[key] = value
					else:
						if isinstance(value, dict):
							package_json[key].update(value)
						elif isinstance(value, list):
							package_json[key].extend(value)
						else:
							package_json[key] = value

	if package_json is {}:
		with open(os.path.join(os.path.dirname(__file__), 'package.json'), 'r') as f:
			package_json = json.loads(f.read())

	with open(os.path.join(bench_path, 'package.json'), 'w') as f:
		f.write(json.dumps(package_json, indent=1, sort_keys=True))

	exec_cmd('npm install', cwd=bench_path)


def backup_site(site, bench_path='.'):
	bench.set_frappe_version(bench_path=bench_path)

	if bench.FRAPPE_VERSION == 4:
		exec_cmd("{frappe} --backup {site}".format(frappe=get_frappe(bench_path=bench_path), site=site),
				cwd=os.path.join(bench_path, 'sites'))
	else:
		run_frappe_cmd('--site', site, 'backup', bench_path=bench_path)


def backup_all_sites(bench_path='.'):
	for site in get_sites(bench_path=bench_path):
		backup_site(site, bench_path=bench_path)


def is_root():
	if os.getuid() == 0:
		return True
	return False


def set_mariadb_host(host, bench_path='.'):
	update_common_site_config({'db_host': host}, bench_path=bench_path)


def set_redis_cache_host(host, bench_path='.'):
	update_common_site_config({'redis_cache': "redis://{}".format(host)}, bench_path=bench_path)


def set_redis_queue_host(host, bench_path='.'):
	update_common_site_config({'redis_queue': "redis://{}".format(host)}, bench_path=bench_path)


def set_redis_socketio_host(host, bench_path='.'):
	update_common_site_config({'redis_socketio': "redis://{}".format(host)}, bench_path=bench_path)


def update_common_site_config(ddict, bench_path='.'):
	update_json_file(os.path.join(bench_path, 'sites', 'common_site_config.json'), ddict)


def update_json_file(filename, ddict):
	if os.path.exists(filename):
		with open(filename, 'r') as f:
			content = json.load(f)

	else:
		content = {}

	content.update(ddict)
	with open(filename, 'w') as f:
		json.dump(content, f, indent=1, sort_keys=True)


def drop_privileges(uid_name='nobody', gid_name='nogroup'):
	# from http://stackoverflow.com/a/2699996
	if os.getuid() != 0:
		# We're not root so, like, whatever dude
		return

	# Get the uid/gid from the name
	running_uid = pwd.getpwnam(uid_name).pw_uid
	running_gid = grp.getgrnam(gid_name).gr_gid

	# Remove group privileges
	os.setgroups([])

	# Try setting the new uid/gid
	os.setgid(running_gid)
	os.setuid(running_uid)

	# Ensure a very conservative umask
	os.umask(0o22)


def fix_prod_setup_perms(bench_path='.', frappe_user=None):
	from .config.common_site_config import get_config

	if not frappe_user:
		frappe_user = get_config(bench_path).get('frappe_user')

	if not frappe_user:
		print("frappe user not set")
		sys.exit(1)

	globs = ["logs/*", "config/*"]
	for glob_name in globs:
		for path in glob.glob(glob_name):
			uid = pwd.getpwnam(frappe_user).pw_uid
			gid = grp.getgrnam(frappe_user).gr_gid
			os.chown(path, uid, gid)


def get_current_frappe_version(bench_path='.'):
	from .app import get_current_frappe_version as fv
	return fv(bench_path=bench_path)


def run_frappe_cmd(*args, **kwargs):
	from .cli import from_command_line

	bench_path = kwargs.get('bench_path', '.')
	f = get_env_cmd('python', bench_path=bench_path)
	sites_dir = os.path.join(bench_path, 'sites')

	is_async = False if from_command_line else True
	if is_async:
		stderr = stdout = subprocess.PIPE
	else:
		stderr = stdout = None

	p = subprocess.Popen((f, '-m', 'frappe.utils.bench_helper', 'frappe') + args,
		cwd=sites_dir, stdout=stdout, stderr=stderr)

	if is_async:
		return_code = print_output(p)
	else:
		return_code = p.wait()

	if return_code > 0:
		sys.exit(return_code)


def validate_upgrade(from_ver, to_ver, bench_path='.'):
	if to_ver >= 6:
		if not find_executable('npm') and not (find_executable('node') or find_executable('nodejs')):
			raise Exception("Please install nodejs and npm")


def post_upgrade(from_ver, to_ver, bench_path='.'):
	from .config.common_site_config import get_config
	from .config import redis
	from .config.supervisor import generate_supervisor_config
	from .config.nginx import make_nginx_conf
	conf = get_config(bench_path=bench_path)
	print("-" * 80 + "Your bench was upgraded to version {0}".format(to_ver))

	if conf.get('restart_supervisor_on_update'):
		redis.generate_config(bench_path=bench_path)
		generate_supervisor_config(bench_path=bench_path)
		make_nginx_conf(bench_path=bench_path)

		if from_ver == 4 and to_ver == 5:
			setup_backups(bench_path=bench_path)

		if from_ver <= 5 and to_ver == 6:
			setup_socketio(bench_path=bench_path)

		message = """
As you have setup your bench for production, you will have to reload configuration for nginx and supervisor. To complete the migration, please run the following commands
sudo service nginx restart
sudo supervisorctl reload
		""".strip()
		print(message)


def update_translations_p(args):
	try:
		update_translations(*args)
	except requests.exceptions.HTTPError:
		print('Download failed for', args[0], args[1])


def download_translations_p():
	pool = multiprocessing.Pool(multiprocessing.cpu_count())

	langs = get_langs()
	apps = ('frappe', 'erpnext')
	args = list(itertools.product(apps, langs))

	pool.map(update_translations_p, args)


def download_translations():
	langs = get_langs()
	apps = ('frappe', 'erpnext')
	for app, lang in itertools.product(apps, langs):
		update_translations(app, lang)


def get_langs():
	lang_file = 'apps/frappe/frappe/geo/languages.json'
	with open(lang_file) as f:
		langs = json.loads(f.read())
	return [d['code'] for d in langs]


def update_translations(app, lang):
	translations_dir = os.path.join('apps', app, app, 'translations')
	csv_file = os.path.join(translations_dir, lang + '.csv')
	url = "https://translate.erpnext.com/files/{}-{}.csv".format(app, lang)
	r = requests.get(url, stream=True)
	r.raise_for_status()

	with open(csv_file, 'wb') as f:
		for chunk in r.iter_content(chunk_size=1024):
			# filter out keep-alive new chunks
			if chunk:
				f.write(chunk)
				f.flush()

	print('downloaded for', app, lang)


def print_output(p):
	while p.poll() is None:
		readx = select.select([p.stdout.fileno(), p.stderr.fileno()], [], [])[0]
		send_buffer = []
		for fd in readx:
			if fd == p.stdout.fileno():
				while 1:
					buf = p.stdout.read(1)
					if not len(buf):
						break
					if buf == '\r' or buf == '\n':
						send_buffer.append(buf)
						log_line(''.join(send_buffer), 'stdout')
						send_buffer = []
					else:
						send_buffer.append(buf)

			if fd == p.stderr.fileno():
				log_line(p.stderr.readline(), 'stderr')
	return p.poll()


def log_line(data, stream):
	if stream == 'stderr':
		return sys.stderr.write(data)
	return sys.stdout.write(data)


def get_bench_name(bench_path):
	return os.path.basename(os.path.abspath(bench_path))


def setup_fonts():
	fonts_path = os.path.join('/tmp', 'fonts')

	if os.path.exists('/etc/fonts_backup'):
		return

	exec_cmd("git clone https://github.com/frappe/fonts.git", cwd='/tmp')
	os.rename('/etc/fonts', '/etc/fonts_backup')
	os.rename('/usr/share/fonts', '/usr/share/fonts_backup')
	os.rename(os.path.join(fonts_path, 'etc_fonts'), '/etc/fonts')
	os.rename(os.path.join(fonts_path, 'usr_share_fonts'), '/usr/share/fonts')
	shutil.rmtree(fonts_path)
	exec_cmd("fc-cache -fv")


def set_git_remote_url(git_url, bench_path='.'):
	"Set app remote git url"
	app = git_url.rsplit('/', 1)[1].rsplit('.', 1)[0]

	if app not in bench.app.get_apps(bench_path):
		print("No app named {0}".format(app))
		sys.exit(1)

	app_dir = bench.app.get_repo_dir(app, bench_path=bench_path)
	if os.path.exists(os.path.join(app_dir, '.git')):
		exec_cmd("git remote set-url upstream {}".format(git_url), cwd=app_dir)


def run_playbook(playbook_name, extra_vars=None, tag=None):
	if not find_executable('ansible'):
		print("Ansible is needed to run this command, please install it using 'pip install ansible'")
		sys.exit(1)
	args = ['ansible-playbook', '-c', 'local', playbook_name, '-vvvv']

	if extra_vars:
		args.extend(['-e', json.dumps(extra_vars)])

	if tag:
		args.extend(['-t', tag])

	subprocess.check_call(args, cwd=os.path.join(bench.__path__[0], 'playbooks'))


def find_benches(directory=None):
	if not directory:
		directory = os.path.expanduser("~")
	elif os.path.exists(directory):
		directory = os.path.abspath(directory)
	else:
		log("Directory doesn't exist", level=2)
		sys.exit(1)

	if is_bench_directory(directory):
		if os.path.curdir == directory:
			print("You are in a bench directory!")
		else:
			print("{0} is a bench directory!".format(directory))
		return

	benches = []
	for sub in os.listdir(directory):
		sub = os.path.join(directory, sub)
		if os.path.isdir(sub) and not os.path.islink(sub):
			if is_bench_directory(sub):
				print("{} found!".format(sub))
				benches.append(sub)
			else:
				benches.extend(find_benches(sub))

	return benches


def migrate_env(python, backup=False):
	from bench.config.common_site_config import get_config
	from bench.app import get_apps

	nvenv = 'env'
	path = os.getcwd()
	python = which(python)
	virtualenv = which('virtualenv')
	pvenv = os.path.join(path, nvenv)
	pip = os.path.join(pvenv, 'bin', 'pip')

	# Clear Cache before Bench Dies.
	try:
		config = get_config(bench_path=os.getcwd())
		rredis = urlparse(config['redis_cache'])

		redis  = '{redis} -p {port}'.format(redis=which('redis-cli'), port=rredis.port)

		logger.log('Clearing Redis Cache...')
		exec_cmd('{redis} FLUSHALL'.format(redis = redis))
		logger.log('Clearing Redis DataBase...')
		exec_cmd('{redis} FLUSHDB'.format(redis = redis))
	except:
		logger.warning('Please ensure Redis Connections are running or Daemonized.')

	# Backup venv: restore using `virtualenv --relocatable` if needed
	if backup:
		parch = os.path.join(path, 'archived_envs')
		if not os.path.exists(parch):
			os.mkdir(parch)

		source = os.path.join(path, 'env')
		target = parch

		logger.log('Backing up Virtual Environment')
		stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
		dest = os.path.join(path, str(stamp))

		os.rename(source, dest)
		shutil.move(dest, target)

	# Create virtualenv using specified python
	venv_creation, packages_setup = 1, 1
	try:
		logger.log('Setting up a New Virtual {} Environment'.format(python))
		venv_creation = exec_cmd('{virtualenv} --python {python} {pvenv}'.format(virtualenv=virtualenv, python=python, pvenv=pvenv))

		apps = ' '.join(["-e {}".format(os.path.join("apps", app)) for app in get_apps()])
		packages_setup = exec_cmd('{0} install -q -U {1}'.format(pip, apps))

		logger.log('Migration Successful to {}'.format(python))
	except:
		if venv_creation or packages_setup:
			logger.warning('Migration Error')


def is_dist_editable(dist):
	"""Is distribution an editable install?"""
	for path_item in sys.path:
		egg_link = os.path.join(path_item, dist + '.egg-link')
		if os.path.isfile(egg_link):
			return True
	return False


def find_parent_bench(path):
	"""Checks if parent directories are benches"""
	if is_bench_directory(directory=path):
		return path

	home_path = os.path.expanduser("~")
	root_path = os.path.abspath(os.sep)

	if path not in {home_path, root_path}:
		# NOTE: the os.path.split assumes that given path is absolute
		parent_dir = os.path.split(path)[0]
		return find_parent_bench(parent_dir)


def generate_command_cache(bench_path='.'):
	"""Caches all available commands (even custom apps) via Frappe
	Default caching behaviour: generated the first time any command (for a specific bench directory)
	"""

	python = get_env_cmd('python', bench_path=bench_path)
	sites_path = os.path.join(bench_path, 'sites')

	if os.path.exists(bench_cache_file):
		os.remove(bench_cache_file)

	try:
		output = get_cmd_output("{0} -m frappe.utils.bench_helper get-frappe-commands".format(python), cwd=sites_path)
		with open(bench_cache_file, 'w') as f:
			json.dump(eval(output), f)
		return json.loads(output)

	except subprocess.CalledProcessError as e:
		if hasattr(e, "stderr"):
			print(e.stderr.decode('utf-8'))


def clear_command_cache(bench_path='.'):
	"""Clears commands cached
	Default invalidation behaviour: destroyed on each run of `bench update`
	"""

	if os.path.exists(bench_cache_file):
		os.remove(bench_cache_file)
	else:
		print("Bench command cache doesn't exist in this folder!")
