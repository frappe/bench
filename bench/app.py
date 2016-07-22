import os
from .utils import (exec_cmd, get_frappe, check_git_for_shallow_clone, build_assets,
	restart_supervisor_processes, get_cmd_output, run_frappe_cmd, CommandFailedError)
from .config.common_site_config import get_config

import logging
import requests
import semantic_version
import json
import re
import subprocess
import bench
import sys
import shutil

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

def get_app(git_url, branch=None, bench_path='.', build_asset_files=True, verbose=False):
	#Gets repo name from URL
	repo_name = git_url.rsplit('/', 1)[1].rsplit('.', 1)[0]
	logger.info('getting app {}'.format(repo_name))
	shallow_clone = '--depth 1' if check_git_for_shallow_clone() else ''
	branch = '--branch {branch}'.format(branch=branch) if branch else ''

	exec_cmd("git clone {git_url} {branch} {shallow_clone} --origin upstream".format(
				git_url=git_url,
				shallow_clone=shallow_clone,
				branch=branch),
			cwd=os.path.join(bench_path, 'apps'))

	#Retrieves app name from setup.py
	app_path = os.path.join(bench_path, 'apps', repo_name, 'setup.py')
	with open(app_path, 'rb') as f:
		app_name = re.search(r'name\s*=\s*[\'"](.*)[\'"]', f.read().decode('utf-8')).group(1)
		if repo_name != app_name:
			apps_path = os.path.join(os.path.abspath(bench_path), 'apps')
			os.rename(os.path.join(apps_path, repo_name), os.path.join(apps_path, app_name))

	print 'installing', app_name
	install_app(app=app_name, bench_path=bench_path, verbose=verbose)

	if build_asset_files:
		build_assets(bench_path=bench_path)
	conf = get_config(bench_path=bench_path)
	if conf.get('restart_supervisor_on_update'):
		restart_supervisor_processes(bench_path=bench_path)

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

def install_app(app, bench_path='.', verbose=False):
	logger.info('installing {}'.format(app))
	# find_links = '--find-links={}'.format(conf.get('wheel_cache_dir')) if conf.get('wheel_cache_dir') else ''
	find_links = ''
	exec_cmd("{pip} install {quiet} {find_links} -e {app}".format(
				pip=os.path.join(bench_path, 'env', 'bin', 'pip'),
				quiet="-q" if not verbose else "",
				app=os.path.join(bench_path, 'apps', app),
				find_links=find_links))
	add_to_appstxt(app, bench_path=bench_path)

def remove_app(app, bench_path='.'):
	if not app in get_apps(bench_path):
		print "No app named {0}".format(app)
		sys.exit(1)

	app_path = os.path.join(bench_path, 'apps', app)
	site_path = os.path.join(bench_path, 'sites')
	pip = os.path.join(bench_path, 'env', 'bin', 'pip')

	for site in os.listdir(site_path):
		req_file = os.path.join(site_path, site, 'site_config.json')
		if os.path.exists(req_file):
			out = subprocess.check_output(["bench", "--site", site, "list-apps"], cwd=bench_path)
			if re.search(r'\b' + app + r'\b', out):
				print "Cannot remove, app is installed on site: {0}".format(site)
				sys.exit(1)

	exec_cmd(["{0} uninstall -y {1}".format(pip, app_path)])
	remove_from_appstxt(app, bench_path)
	shutil.rmtree(app_path)
	run_frappe_cmd("build", bench_path=bench_path)
	if get_config(bench_path).get('restart_supervisor_on_update'):
		restart_supervisor_processes(bench_path=bench_path)


def pull_all_apps(bench_path='.'):
	rebase = '--rebase' if get_config(bench_path).get('rebase_on_pull') else ''

	for app in get_apps(bench_path=bench_path):
		app_dir = get_repo_dir(app, bench_path=bench_path)
		if os.path.exists(os.path.join(app_dir, '.git')):
			contents = subprocess.check_output(['git', 'remote', '-v'], cwd=app_dir,
				stderr=subprocess.STDOUT)

			if re.findall('upstream[\s]+', contents):
				remote = 'upstream'
			else:
				# get the first remote
				remote = contents.splitlines()[0].split()[0]

			logger.info('pulling {0}'.format(app))
			exec_cmd("git pull {rebase} {remote} {branch}".format(rebase=rebase,
				remote=remote, branch=get_current_branch(app, bench_path=bench_path)), cwd=app_dir)
			exec_cmd('find . -name "*.pyc" -delete', cwd=app_dir)


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
	return get_cmd_output("basename $(git symbolic-ref -q HEAD)", cwd=repo_dir)

def use_rq(bench_path):
	bench_path = os.path.abspath(bench_path)
	celery_app = os.path.join(bench_path, 'apps', 'frappe', 'frappe', 'celery_app.py')
	return not os.path.exists(celery_app)

def fetch_upstream(app, bench_path='.'):
	repo_dir = get_repo_dir(app, bench_path=bench_path)
	return subprocess.call(["git", "fetch", "upstream"], cwd=repo_dir)

def get_current_version(app, bench_path='.'):
	repo_dir = get_repo_dir(app, bench_path=bench_path)
	try:
		with open(os.path.join(repo_dir, os.path.basename(repo_dir), '__init__.py')) as f:
			return get_version_from_string(f.read())

	except AttributeError:
		# backward compatibility
		with open(os.path.join(repo_dir, 'setup.py')) as f:
			return get_version_from_string(f.read(), field='version')

def get_upstream_version(app, branch=None, bench_path='.'):
	repo_dir = get_repo_dir(app, bench_path=bench_path)
	if not branch:
		branch = get_current_branch(app, bench_path=bench_path)
	try:
		contents = subprocess.check_output(['git', 'show', 'upstream/{branch}:{app}/__init__.py'.format(branch=branch, app=app)], cwd=repo_dir, stderr=subprocess.STDOUT)
	except subprocess.CalledProcessError, e:
		if "Invalid object" in e.output:
			return None
		else:
			raise
	return get_version_from_string(contents)

def get_upstream_url(app, bench_path='.'):
	repo_dir = get_repo_dir(app, bench_path=bench_path)
	return subprocess.check_output(['git', 'config', '--get', 'remote.upstream.url'], cwd=repo_dir).strip()

def get_repo_dir(app, bench_path='.'):
	return os.path.join(bench_path, 'apps', app)

def switch_branch(branch, apps=None, bench_path='.', upgrade=False, check_upgrade=True):
	from .utils import update_requirements, backup_all_sites, patch_sites, build_assets, pre_upgrade, post_upgrade
	import utils
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
				print "Switching for "+app
				unshallow = "--unshallow" if os.path.exists(os.path.join(app_dir, ".git", "shallow")) else ""
				exec_cmd("git config --unset-all remote.upstream.fetch", cwd=app_dir)
				exec_cmd("git config --add remote.upstream.fetch '+refs/heads/*:refs/remotes/upstream/*'", cwd=app_dir)
				exec_cmd("git fetch upstream {unshallow}".format(unshallow=unshallow), cwd=app_dir)
				exec_cmd("git checkout {branch}".format(branch=branch), cwd=app_dir)
				exec_cmd("git merge upstream/{branch}".format(branch=branch), cwd=app_dir)
				switched_apps.append(app)
			except CommandFailedError:
				print "Error switching to branch {0} for {1}".format(branch, app)
			except InvalidRemoteException:
				print "Remote does not exist for app "+app
			except InvalidBranchException:
				print "Branch {0} does not exist in Upstream for {1}".format(branch, app)

	if switched_apps:
		print "Successfully switched branches for:\n" + "\n".join(switched_apps)

	if version_upgrade[0] and upgrade:
		update_requirements()
		pre_upgrade(version_upgrade[1], version_upgrade[2])
		reload(utils)
		backup_all_sites()
		patch_sites()
		build_assets()
		post_upgrade(version_upgrade[1], version_upgrade[2])

def switch_to_branch(branch=None, apps=None, bench_path='.', upgrade=False):
	switch_branch(branch, apps=apps, bench_path=bench_path, upgrade=upgrade)

def switch_to_master(apps=None, bench_path='.', upgrade=False):
	switch_branch('master', apps=apps, bench_path=bench_path, upgrade=upgrade)

def switch_to_develop(apps=None, bench_path='.', upgrade=False):
	switch_branch('develop', apps=apps, bench_path=bench_path, upgrade=upgrade)

def switch_to_v4(apps=None, bench_path='.', upgrade=False):
	switch_branch('v4.x.x', apps=apps, bench_path=bench_path, upgrade=upgrade)

def switch_to_v5(apps=None, bench_path='.', upgrade=False):
	switch_branch('v5.x.x', apps=apps, bench_path=bench_path, upgrade=upgrade)

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
	else:
		with open(path) as f:
			return json.load(f)
