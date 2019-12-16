from __future__ import print_function
import os
from .utils import (exec_cmd, get_frappe, check_git_for_shallow_clone, build_assets,
	restart_supervisor_processes, run_frappe_cmd, CommandFailedError,
	restart_systemd_processes)
from .config.common_site_config import get_config
from six.moves import reload_module

import logging
import requests
import semantic_version
import json
import re
import subprocess
import bench
import sys
import shutil
import git

logging.basicConfig(level="DEBUG")
logger = logging.getLogger(__name__)

class InvalidBranchException(Exception): pass
class InvalidRemoteException(Exception): pass

class MajorVersionUpgradeException(Exception):
	def __init__(self, message, upstream_version, local_version):
		super(MajorVersionUpgradeException, self).__init__(message)
		self.upstream_version = upstream_version
		self.local_version = local_version

def get_apps(bench_path='.'):
	try:
		with open(os.path.join(bench_path, 'sites', 'apps.txt')) as f:
			return f.read().strip().split('\n')
	except IOError:
		return []

def add_to_appstxt(app, bench_path='.'):
	apps = get_apps(bench_path=bench_path)
	if app not in apps:
		apps.append(app)
		return write_appstxt(apps, bench_path=bench_path)

def remove_from_appstxt(app, bench_path='.'):
	apps = get_apps(bench_path=bench_path)
	if app in apps:
		apps.remove(app)
		return write_appstxt(apps, bench_path=bench_path)

def write_appstxt(apps, bench_path='.'):
	with open(os.path.join(bench_path, 'sites', 'apps.txt'), 'w') as f:
		return f.write('\n'.join(apps))

def check_url(url, raise_err = True):
	try:
		from urlparse import urlparse
	except ImportError:
		from urllib.parse import urlparse

	parsed = urlparse(url)
	if not parsed.scheme:
		if raise_err:
			raise TypeError('{url} Not a valid URL'.format(url = url))
		else:
			return False

	return True

def get_excluded_apps(bench_path='.'):
	try:
		with open(os.path.join(bench_path, 'sites', 'excluded_apps.txt')) as f:
			return f.read().strip().split('\n')
	except IOError:
		return []

def add_to_excluded_apps_txt(app, bench_path='.'):
	if app == 'frappe':
		raise ValueError('Frappe app cannot be excludeed from update')
	if app not in os.listdir('apps'):
		raise ValueError('The app {} does not exist'.format(app))
	apps = get_excluded_apps(bench_path=bench_path)
	if app not in apps:
		apps.append(app)
		return write_excluded_apps_txt(apps, bench_path=bench_path)

def write_excluded_apps_txt(apps, bench_path='.'):
	with open(os.path.join(bench_path, 'sites', 'excluded_apps.txt'), 'w') as f:
		return f.write('\n'.join(apps))

def remove_from_excluded_apps_txt(app, bench_path='.'):
	apps = get_excluded_apps(bench_path=bench_path)
	if app in apps:
		apps.remove(app)
		return write_excluded_apps_txt(apps, bench_path=bench_path)

def get_app(git_url, branch=None, bench_path='.', build_asset_files=True, verbose=False,
	postprocess = True):
	# from bench.utils import check_url
	try:
		from urlparse import urljoin
	except ImportError:
		from urllib.parse import urljoin

	if not check_url(git_url, raise_err = False):
		orgs = ['frappe', 'erpnext']
		for org in orgs:
			url = 'https://api.github.com/repos/{org}/{app}'.format(org = org, app = git_url)
			res = requests.get(url)
			if res.ok:
				data    = res.json()
				if 'name' in data:
					if git_url == data['name']:
						git_url = 'https://github.com/{org}/{app}'.format(org = org, app = git_url)
						break

	#Gets repo name from URL
	repo_name = git_url.rsplit('/', 1)[1].rsplit('.', 1)[0]
	logger.info('Getting app {}'.format(repo_name))
	kwargs = {"origin": "upstream"}
	if check_git_for_shallow_clone():
		kwargs["depth"] = 1
	if branch:
		kwargs["branch"] = branch

	git.Repo.clone_from(git_url, os.path.join(bench_path, "apps/{0}".format(repo_name)), **kwargs)

	#Retrieves app name from setup.py
	app_path = os.path.join(bench_path, 'apps', repo_name, 'setup.py')
	with open(app_path, 'rb') as f:
		app_name = re.search(r'name\s*=\s*[\'"](.*)[\'"]', f.read().decode('utf-8')).group(1)
		if repo_name != app_name:
			apps_path = os.path.join(os.path.abspath(bench_path), 'apps')
			os.rename(os.path.join(apps_path, repo_name), os.path.join(apps_path, app_name))

	print('Installing', app_name)
	install_app(app=app_name, bench_path=bench_path, verbose=verbose)

	if postprocess:

		if build_asset_files:
			build_assets(bench_path=bench_path, app=app_name)
		conf = get_config(bench_path=bench_path)

		if conf.get('restart_supervisor_on_update'):
			restart_supervisor_processes(bench_path=bench_path)
		if conf.get('restart_systemd_on_update'):
			restart_systemd_processes(bench_path=bench_path)

def new_app(app, bench_path='.'):
	# For backwards compatibility
	app = app.lower().replace(" ", "_").replace("-", "_")
	logger.info('creating new app {}'.format(app))
	apps = os.path.abspath(os.path.join(bench_path, 'apps'))
	bench.set_frappe_version(bench_path=bench_path)

	if bench.FRAPPE_VERSION == 4:
		exec_cmd("{frappe} --make_app {apps} {app}".format(frappe=get_frappe(bench_path=bench_path),
			apps=apps, app=app))
	else:
		run_frappe_cmd('make-app', apps, app, bench_path=bench_path)
	install_app(app, bench_path=bench_path)

def install_app(app, bench_path=".", verbose=False, no_cache=False):
	logger.info("installing {}".format(app))

	pip_path = os.path.join(bench_path, "env", "bin", "pip")
	quiet_flag = "-q" if not verbose else ""
	app_path = os.path.join(bench_path, "apps", app)
	cache_flag = "--no-cache-dir" if no_cache else ""

	exec_cmd("{pip} install {quiet} -U -e {app} {no_cache}".format(pip=pip_path, quiet=quiet_flag, app=app_path, no_cache=cache_flag))
	add_to_appstxt(app, bench_path=bench_path)

def remove_app(app, bench_path='.'):
	if not app in get_apps(bench_path):
		print("No app named {0}".format(app))
		sys.exit(1)

	app_path = os.path.join(bench_path, 'apps', app)
	site_path = os.path.join(bench_path, 'sites')
	pip = os.path.join(bench_path, 'env', 'bin', 'pip')

	for site in os.listdir(site_path):
		req_file = os.path.join(site_path, site, 'site_config.json')
		if os.path.exists(req_file):
			out = subprocess.check_output(["bench", "--site", site, "list-apps"], cwd=bench_path).decode('utf-8')
			if re.search(r'\b' + app + r'\b', out):
				print("Cannot remove, app is installed on site: {0}".format(site))
				sys.exit(1)

	exec_cmd(["{0} uninstall -y {1}".format(pip, app)])
	remove_from_appstxt(app, bench_path)
	shutil.rmtree(app_path)
	run_frappe_cmd("build", bench_path=bench_path)
	if get_config(bench_path).get('restart_supervisor_on_update'):
		restart_supervisor_processes(bench_path=bench_path)
	if get_config(bench_path).get('restart_systemd_on_update'):
		restart_systemd_processes(bench_path=bench_path)

def pull_all_apps(bench_path='.', reset=False):
	'''Check all apps if there no local changes, pull'''
	kwargs = {}
	if get_config(bench_path).get("rebase_on_pull"):
		kwargs["rebase"] = True

	# chech for local changes
	if not reset:
		for app in get_apps(bench_path=bench_path):
			excluded_apps = get_excluded_apps()
			if app in excluded_apps:
				print("Skipping reset for app {}".format(app))
				continue
			app_dir = get_repo_dir(app, bench_path=bench_path)
			try:
				repo = git.Repo(app_dir)
				out = repo.git.status()
				if not re.search(r'nothing to commit, working (directory|tree) clean', out):
					print('''

Cannot proceed with update: You have local changes in app "{0}" that are not committed.

Here are your choices:

1. Merge the {0} app manually with "git pull" / "git pull --rebase" and fix conflicts.
1. Temporarily remove your changes with "git stash" or discard them completely
	with "bench update --reset" or for individual repositries "git reset --hard"
2. If your changes are helpful for others, send in a pull request via GitHub and
	wait for them to be merged in the core.'''.format(app))
					sys.exit(1)
			except git.exc.InvalidGitRepositoryError:
				continue

	excluded_apps = get_excluded_apps()
	for app in get_apps(bench_path=bench_path):
		if app in excluded_apps:
			print("Skipping pull for app {}".format(app))
			continue
		app_dir = get_repo_dir(app, bench_path=bench_path)
		try:
			repo = git.Repo(app_dir)
			if not repo.remotes:
				# remote is False, i.e. remote doesn't exist, add the app to excluded_apps.txt
				add_to_excluded_apps_txt(app, bench_path=bench_path)
				print("Skipping pull for app {}, since remote doesn't exist, and adding it to excluded apps".format(app))
				continue
			logger.info('Pulling {0}'.format(app))
			branch = get_current_branch(app, bench_path=bench_path)
			if reset:
				for remote in repo.remotes:
					remote.fetch()
				repo.git.reset("--hard", "{0}/{1}".format(remote, branch))
			else:
				repo.remotes[remote].pull(branch, **kwargs)
			exec_cmd('find . -name "*.pyc" -delete', cwd=app_dir)
		except git.exc.InvalidGitRepositoryError:
			continue


def is_version_upgrade(app='frappe', bench_path='.', branch=None):
	try:
		fetch_upstream(app, bench_path=bench_path)
	except CommandFailedError:
		raise InvalidRemoteException("No remote named upstream for {0}".format(app))

	upstream_version = get_upstream_version(app=app, branch=branch, bench_path=bench_path)

	if not upstream_version:
		raise InvalidBranchException("Specified branch of app {0} is not in upstream".format(app))

	local_version = get_major_version(get_current_version(app, bench_path=bench_path))
	upstream_version = get_major_version(upstream_version)

	if upstream_version - local_version > 0:
		return (True, local_version, upstream_version)

	return (False, local_version, upstream_version)

def get_current_frappe_version(bench_path='.'):
	try:
		return get_major_version(get_current_version('frappe', bench_path=bench_path))
	except IOError:
		return 0

def get_current_branch(app, bench_path='.'):
	repo_dir = get_repo_dir(app, bench_path=bench_path)
	repo = git.Repo(repo_dir)
	return repo.active_branch.name

def get_remote(app, bench_path='.'):
	repo_dir = get_repo_dir(app, bench_path=bench_path)
	try:
		repo = git.Repo(repo_dir)
		remotes = [remote.name for remote in repo.remotes]
		if not remotes:
			return False
		elif "upstream" in remotes:
			return "upstream"
		else:
			return remotes[0]
	except git.exc.InvalidGitRepositoryError:
		pass

def use_rq(bench_path):
	bench_path = os.path.abspath(bench_path)
	celery_app = os.path.join(bench_path, 'apps', 'frappe', 'frappe', 'celery_app.py')
	return not os.path.exists(celery_app)

def fetch_upstream(app, bench_path='.'):
	repo_dir = get_repo_dir(app, bench_path=bench_path)
	repo = git.Repo(repo_dir)
	return repo.remotes["upstream"].fetch()

def get_current_version(app, bench_path='.'):
	repo_dir = get_repo_dir(app, bench_path=bench_path)
	try:
		with open(os.path.join(repo_dir, os.path.basename(repo_dir), '__init__.py')) as f:
			return get_version_from_string(f.read())

	except AttributeError:
		# backward compatibility
		with open(os.path.join(repo_dir, 'setup.py')) as f:
			return get_version_from_string(f.read(), field='version')

def get_develop_version(app, bench_path='.'):
	repo_dir = get_repo_dir(app, bench_path=bench_path)
	with open(os.path.join(repo_dir, os.path.basename(repo_dir), 'hooks.py')) as f:
		return get_version_from_string(f.read(), field='develop_version')

def get_upstream_version(app, branch=None, bench_path='.'):
	repo_dir = get_repo_dir(app, bench_path=bench_path)
	if not branch:
		branch = get_current_branch(app, bench_path=bench_path)
	try:
		repo = git.Repo(repo_dir)
		contents = repo.git.show("upstream/{0}:{1}/__init__.py")
		return get_version_from_string(contents)
	except (git.exc.InvalidGitRepositoryError, git.exc.GitCommandError):
		return None

def get_upstream_url(app, bench_path='.'):
	repo_dir = get_repo_dir(app, bench_path=bench_path)
	try:
		repo = git.Repo(repo_dir)
		return repo.remotes.upstream.url
	except (git.exc.InvalidGitRepositoryError, AttributeError, IndexError):
		# no upstream url found
		return None

def get_repo_dir(app, bench_path='.'):
	return os.path.join(bench_path, 'apps', app)

def switch_branch(branch, apps=None, bench_path='.', upgrade=False, check_upgrade=True):
	from .utils import update_requirements, update_node_packages, backup_all_sites, patch_sites, build_assets, pre_upgrade, post_upgrade
	from . import utils
	apps_dir = os.path.join(bench_path, 'apps')
	version_upgrade = (False,)
	switched_apps = []

	if not apps:
		apps = [name for name in os.listdir(apps_dir)
			if os.path.isdir(os.path.join(apps_dir, name))]
		if branch=="v4.x.x":
			apps.append('shopping_cart')

	for app in apps:
		app_dir = os.path.join(apps_dir, app)
		if os.path.exists(app_dir):
			try:
				if check_upgrade:
					version_upgrade = is_version_upgrade(app=app, bench_path=bench_path, branch=branch)
					if version_upgrade[0] and not upgrade:
						raise MajorVersionUpgradeException("Switching to {0} will cause upgrade from {1} to {2}. Pass --upgrade to confirm".format(branch, version_upgrade[1], version_upgrade[2]), version_upgrade[1], version_upgrade[2])
				print("Switching for " + app)
				repo = git.Repo(app_dir)
				kwargs = {}
				if repo.git.rev_parse("--is-shallow-repository") == "false":
					kwargs["unshallow"] = True
				repo.git.config("--unset-all remotes.upstream.fetch")
				repo.git.config("--add remote.upstream.fetch '+refs/heads/*:refs/remotes/upstream/*'")
				repo.remotes.upstream.fetch(**kwargs)
				repo.git.checkout(branch)
				repo.git.merge("upstream/{0}".format(branch))
				switched_apps.append(app)
			except git.exc.InvalidGitRepositoryError:
				print("{0} does not seem to be a valid git repository".format(app))
			except AttributeError:
				print("upstream is not a valid remote for app: {0}".format(app))
			except git.exc.GitCommandError:
				print("branch {0} does not exist in upstream for app: {1}".format(branch, app))

	if switched_apps:
		print("Successfully switched branches for:")
		print("\n".join(switched_apps))

	if version_upgrade[0] and upgrade:
		update_requirements()
		update_node_packages()
		pre_upgrade(version_upgrade[1], version_upgrade[2])
		reload_module(utils)
		backup_all_sites()
		patch_sites()
		build_assets()
		post_upgrade(version_upgrade[1], version_upgrade[2])

def switch_to_branch(branch=None, apps=None, bench_path='.', upgrade=False):
	switch_branch(branch, apps=apps, bench_path=bench_path, upgrade=upgrade)

def switch_to_master(apps=None, bench_path='.', upgrade=True):
	switch_branch('master', apps=apps, bench_path=bench_path, upgrade=upgrade)

def switch_to_develop(apps=None, bench_path='.', upgrade=True):
	switch_branch('develop', apps=apps, bench_path=bench_path, upgrade=upgrade)

def get_version_from_string(contents, field='__version__'):
	match = re.search(r"^(\s*%s\s*=\s*['\\\"])(.+?)(['\"])(?sm)" % field,
			contents)
	return match.group(2)

def get_major_version(version):
	return semantic_version.Version(version).major

def install_apps_from_path(path, bench_path='.'):
	apps = get_apps_json(path)
	for app in apps:
		get_app(app['url'], branch=app.get('branch'), bench_path=bench_path, build_asset_files=False)

def get_apps_json(path):
	if path.startswith('http'):
		r = requests.get(path)
		return r.json()

	with open(path) as f:
		return json.load(f)

def validate_branch():
	for app in ['frappe', 'erpnext']:
		branch = get_current_branch(app)

		if branch == "master":
			print(''' master branch is renamed to version-11 and develop to version-12. Please switch to new branches to get future updates.

To switch to version 11, run the following commands: bench switch-to-branch version-11''')
			sys.exit(1)
