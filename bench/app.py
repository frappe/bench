import os
from .utils import (exec_cmd, get_frappe, check_git_for_shallow_clone, build_assets, 
	restart_supervisor_processes, get_cmd_output, run_frappe_cmd)
from .config.common_site_config import get_config

import logging
import requests
import semantic_version
import json
import re
import subprocess

logging.basicConfig(level="DEBUG")
logger = logging.getLogger(__name__)

class MajorVersionUpgradeException(Exception):
	def __init__(self, message, upstream_version, local_version):
		super(MajorVersionUpgradeException, self).__init__(message)
		self.upstream_version = upstream_version
		self.local_version = local_version

def get_apps(bench='.'):
	try:
		with open(os.path.join(bench, 'sites', 'apps.txt')) as f:
			return f.read().strip().split('\n')
	except IOError:
		return []

def add_to_appstxt(app, bench='.'):
	apps = get_apps(bench=bench)
	if app not in apps:
		apps.append(app)
		return write_appstxt(apps, bench=bench)

def remove_from_appstxt(app, bench='.'):
	apps = get_apps(bench=bench)
	if app in apps:
		apps.remove(app)
		return write_appstxt(apps, bench=bench)

def write_appstxt(apps, bench='.'):
	with open(os.path.join(bench, 'sites', 'apps.txt'), 'w') as f:
		return f.write('\n'.join(apps))

def get_app(app, git_url, branch=None, bench='.', build_asset_files=True, verbose=False):
	logger.info('getting app {}'.format(app))
	shallow_clone = '--depth 1' if check_git_for_shallow_clone() else ''
	branch = '--branch {branch}'.format(branch=branch) if branch else ''
	exec_cmd("git clone {git_url} {branch} {shallow_clone} --origin upstream {app}".format(
				git_url=git_url,
				app=app,
				shallow_clone=shallow_clone,
				branch=branch),
			cwd=os.path.join(bench, 'apps'))
	print 'installing', app
	install_app(app, bench=bench, verbose=verbose)
	if build_asset_files:
		build_assets(bench=bench)
	conf = get_config(bench=bench)
	if conf.get('restart_supervisor_on_update'):
		restart_supervisor_processes(bench=bench)

def new_app(app, bench='.'):
	app = app.lower().replace(" ", "_")
	logger.info('creating new app {}'.format(app))
	apps = os.path.abspath(os.path.join(bench, 'apps'))
	if FRAPPE_VERSION == 4:
		exec_cmd("{frappe} --make_app {apps} {app}".format(frappe=get_frappe(bench=bench),
			apps=apps, app=app))
	else:
		run_frappe_cmd('make-app', apps, app, bench=bench)
	install_app(app, bench=bench)

def install_app(app, bench='.', verbose=False):
	logger.info('installing {}'.format(app))
	# find_links = '--find-links={}'.format(conf.get('wheel_cache_dir')) if conf.get('wheel_cache_dir') else ''
	find_links = ''
	exec_cmd("{pip} install {quiet} {find_links} -e {app}".format(
				pip=os.path.join(bench, 'env', 'bin', 'pip'),
				quiet="-q" if not verbose else "",
				app=os.path.join(bench, 'apps', app),
				find_links=find_links))
	add_to_appstxt(app, bench=bench)

def pull_all_apps(bench='.'):
	rebase = '--rebase' if get_config(bench).get('rebase_on_pull') else ''

	for app in get_apps(bench=bench):
		app_dir = get_repo_dir(app, bench=bench)
		if os.path.exists(os.path.join(app_dir, '.git')):
			logger.info('pulling {0}'.format(app))
			exec_cmd("git pull {rebase} upstream {branch}".format(rebase=rebase, branch=get_current_branch(app, bench=bench)), cwd=app_dir)

def is_version_upgrade(bench='.', branch=None):
	fetch_upstream('frappe', bench=bench)
	upstream_version = get_upstream_version('frappe', bench=bench, branch=branch)

	if not upstream_version:
		raise Exception("Current branch of 'frappe' not in upstream")

	local_version = get_major_version(get_current_version('frappe', bench=bench))
	upstream_version = get_major_version(upstream_version)

	if upstream_version - local_version > 0:
		return (True, local_version, upstream_version)

	return (False, local_version, upstream_version)

def get_current_frappe_version(bench='.'):
	try:
		return get_major_version(get_current_version('frappe', bench=bench))
	except IOError:
		return ''

def get_current_branch(app, bench='.'):
	repo_dir = get_repo_dir(app, bench=bench)
	return get_cmd_output("basename $(git symbolic-ref -q HEAD)", cwd=repo_dir)

def fetch_upstream(app, bench='.'):
	repo_dir = get_repo_dir(app, bench=bench)
	return exec_cmd("git fetch upstream", cwd=repo_dir)

def get_current_version(app, bench='.'):
	repo_dir = get_repo_dir(app, bench=bench)
	with open(os.path.join(repo_dir, 'setup.py')) as f:
		return get_version_from_string(f.read())

def get_upstream_version(app, branch=None, bench='.'):
	repo_dir = get_repo_dir(app, bench=bench)
	if not branch:
		branch = get_current_branch(app, bench=bench)
	try:
		contents = subprocess.check_output(['git', 'show', 'upstream/{branch}:setup.py'.format(branch=branch)], cwd=repo_dir, stderr=subprocess.STDOUT)
	except subprocess.CalledProcessError, e:
		if "Invalid object" in e.output:
			return None
		else:
			raise
	return get_version_from_string(contents)

def get_upstream_url(app, bench='.'):
	repo_dir = get_repo_dir(app, bench=bench)
	return subprocess.check_output(['git', 'config', '--get', 'remote.upstream.url'], cwd=repo_dir).strip()

def get_repo_dir(app, bench='.'):
	return os.path.join(bench, 'apps', app)

def switch_branch(branch, apps=None, bench='.', upgrade=False):
	from .utils import update_requirements, backup_all_sites, patch_sites, build_assets, pre_upgrade, post_upgrade
	import utils
	apps_dir = os.path.join(bench, 'apps')
	version_upgrade = is_version_upgrade(bench=bench, branch=branch)
	if version_upgrade[0] and not upgrade:
		raise MajorVersionUpgradeException("Switching to {0} will cause upgrade from {1} to {2}. Pass --upgrade to confirm".format(branch, version_upgrade[1], version_upgrade[2]), version_upgrade[1], version_upgrade[2])

	if not apps:
		apps = ['frappe', 'erpnext']
		if branch=="v4.x.x":
			apps.append('shopping_cart')

	for app in apps:
		app_dir = os.path.join(apps_dir, app)
		if os.path.exists(app_dir):
			unshallow = "--unshallow" if os.path.exists(os.path.join(app_dir, ".git", "shallow")) else ""
			exec_cmd("git config --unset-all remote.upstream.fetch", cwd=app_dir)
			exec_cmd("git config --add remote.upstream.fetch '+refs/heads/*:refs/remotes/upstream/*'", cwd=app_dir)
			exec_cmd("git fetch upstream {unshallow}".format(unshallow=unshallow), cwd=app_dir)
			exec_cmd("git checkout {branch}".format(branch=branch), cwd=app_dir)
			exec_cmd("git merge upstream/{branch}".format(branch=branch), cwd=app_dir)

	if version_upgrade[0] and upgrade:
		update_requirements()
		pre_upgrade(version_upgrade[1], version_upgrade[2])
		reload(utils)
		backup_all_sites()
		patch_sites()
		build_assets()
		post_upgrade(version_upgrade[1], version_upgrade[2])

def switch_to_master(apps=None, bench='.', upgrade=False):
	switch_branch('master', apps=apps, bench=bench, upgrade=upgrade)

def switch_to_develop(apps=None, bench='.', upgrade=False):
	switch_branch('develop', apps=apps, bench=bench, upgrade=upgrade)

def switch_to_v4(apps=None, bench='.', upgrade=False):
	switch_branch('v4.x.x', apps=apps, bench=bench, upgrade=upgrade)

def switch_to_v5(apps=None, bench='.', upgrade=False):
	switch_branch('v5.x.x', apps=apps, bench=bench, upgrade=upgrade)

def get_version_from_string(contents):
	match = re.search(r"^(\s*%s\s*=\s*['\\\"])(.+?)(['\"])(?sm)" % 'version',
			contents)
	return match.group(2)

def get_major_version(version):
	return semantic_version.Version(version).major

def install_apps_from_path(path, bench='.'):
	apps = get_apps_json(path)
	for app in apps:
		get_app(app['name'], app['url'], branch=app.get('branch'), bench=bench, build_asset_files=False)

def get_apps_json(path):
	if path.startswith('http'):
		r = requests.get(path)
		return r.json()
	else:
		with open(path) as f:
			return json.load(f)

FRAPPE_VERSION = get_current_frappe_version()
