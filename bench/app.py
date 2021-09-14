# imports - standard imports
import json
from json.decoder import JSONDecodeError
import logging
import os
import re
import subprocess
import sys

# imports - third party imports
import click
from setuptools.config import read_configuration

# imports - module imports
import bench
from bench.utils import color, CommandFailedError, build_assets, check_git_for_shallow_clone, exec_cmd, get_cmd_output, get_frappe, restart_supervisor_processes, restart_systemd_processes, run_frappe_cmd


logger = logging.getLogger(bench.PROJECT_NAME)


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

def is_git_url(url):
	# modified to allow without the tailing .git from https://github.com/jonschlinkert/is-git-url.git
	pattern = r"(?:git|ssh|https?|git@[-\w.]+):(\/\/)?(.*?)(\.git)?(\/?|\#[-\d\w._]+?)$"
	return bool(re.match(pattern, url))

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
		raise ValueError(f'The app {app} does not exist')
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

def get_app(git_url, branch=None, bench_path='.', skip_assets=False, verbose=False, restart_bench=True, overwrite=False):
	import requests
	import shutil

	if not os.path.exists(git_url):
		if not is_git_url(git_url):
			orgs = ['frappe', 'erpnext']
			for org in orgs:
				url = f'https://api.github.com/repos/{org}/{git_url}'
				res = requests.get(url)
				if res.ok:
					data = res.json()
					if 'name' in data:
						if git_url == data['name']:
							git_url = f'https://github.com/{org}/{git_url}'
							break
				else:
					bench.utils.log(f"App {git_url} not found", level=2)
					sys.exit(1)

		# Gets repo name from URL
		repo_name = git_url.rstrip('/').rsplit('/', 1)[1].rsplit('.', 1)[0]
		shallow_clone = '--depth 1' if check_git_for_shallow_clone() else ''
		branch = f'--branch {branch}' if branch else ''
	else:
		git_url = os.path.abspath(git_url)
		_, repo_name = os.path.split(git_url)
		shallow_clone = ''
		branch = f'--branch {branch}' if branch else ''

	if os.path.isdir(os.path.join(bench_path, 'apps', repo_name)):
		# application directory already exists
		# prompt user to overwrite it
		if overwrite or click.confirm(f'''A directory for the application "{repo_name}" already exists.
Do you want to continue and overwrite it?'''):
			shutil.rmtree(os.path.join(bench_path, 'apps', repo_name))
		elif click.confirm('''Do you want to reinstall the existing application?''', abort=True):
			app_name = get_app_name(bench_path, repo_name)
			install_app(app=app_name, bench_path=bench_path, verbose=verbose, skip_assets=skip_assets)
			sys.exit()

	print(f'\n{color.yellow}Getting {repo_name}{color.nc}')
	logger.log(f'Getting app {repo_name}')
	exec_cmd(f"git clone {git_url} {branch} {shallow_clone} --origin upstream",
		cwd=os.path.join(bench_path, 'apps'))

	app_name = get_app_name(bench_path, repo_name)
	install_app(app=app_name, bench_path=bench_path, verbose=verbose, skip_assets=skip_assets)


def get_app_name(bench_path, repo_name):
	app_name = None
	apps_path = os.path.join(os.path.abspath(bench_path), 'apps')
	config_path = os.path.join(apps_path, repo_name, 'setup.cfg')
	if os.path.exists(config_path):
		config = read_configuration(config_path)
		app_name = config.get('metadata', {}).get('name')

	if not app_name:
		# retrieve app name from setup.py as fallback
		app_path = os.path.join(apps_path, repo_name, 'setup.py')
		with open(app_path, 'rb') as f:
			app_name = re.search(r'name\s*=\s*[\'"](.*)[\'"]', f.read().decode('utf-8')).group(1)

	if app_name and repo_name != app_name:
		os.rename(os.path.join(apps_path, repo_name), os.path.join(apps_path, app_name))
		return app_name

	return repo_name


def new_app(app, bench_path='.'):
	# For backwards compatibility
	app = app.lower().replace(" ", "_").replace("-", "_")
	logger.log(f'creating new app {app}')
	apps = os.path.abspath(os.path.join(bench_path, 'apps'))
	run_frappe_cmd('make-app', apps, app, bench_path=bench_path)
	install_app(app, bench_path=bench_path)


def install_app(app, bench_path=".", verbose=False, no_cache=False, restart_bench=True, skip_assets=False):
	from bench.config.common_site_config import get_config

	print(f'\n{color.yellow}Installing {app}{color.nc}')
	logger.log(f"installing {app}")

	python_path = os.path.join(bench_path, "env", "bin", "python")
	quiet_flag = "-q" if not verbose else ""
	app_path = os.path.join(bench_path, "apps", app)
	cache_flag = "--no-cache-dir" if no_cache else ""

	exec_cmd(f"{python_path} -m pip install {quiet_flag} -U -e {app_path} {cache_flag}")

	if os.path.exists(os.path.join(app_path, 'package.json')):
		exec_cmd("yarn install", cwd=app_path)

	add_to_appstxt(app, bench_path=bench_path)

	conf = get_config(bench_path=bench_path)

	if conf.get("developer_mode"):
		from bench.utils import install_python_dev_dependencies
		install_python_dev_dependencies(apps=app)

	if not skip_assets:
		build_assets(bench_path=bench_path, app=app)

	if restart_bench:
		if conf.get('restart_supervisor_on_update'):
			restart_supervisor_processes(bench_path=bench_path)
		if conf.get('restart_systemd_on_update'):
			restart_systemd_processes(bench_path=bench_path)


def remove_app(app, bench_path='.'):
	import shutil
	from bench.config.common_site_config import get_config

	app_path = os.path.join(bench_path, 'apps', app)
	py = os.path.join(bench_path, 'env', 'bin', 'python')

	# validate app removal
	if app not in get_apps(bench_path):
		print(f"No app named {app}")
		sys.exit(1)

	validate_app_installed_on_sites(app, bench_path=bench_path)

	# remove app from bench
	exec_cmd("{0} -m pip uninstall -y {1}".format(py, app), cwd=bench_path)
	remove_from_appstxt(app, bench_path)
	shutil.rmtree(app_path)

	# re-build assets and restart processes
	run_frappe_cmd("build", bench_path=bench_path)
	if get_config(bench_path).get('restart_supervisor_on_update'):
		restart_supervisor_processes(bench_path=bench_path)
	if get_config(bench_path).get('restart_systemd_on_update'):
		restart_systemd_processes(bench_path=bench_path)


def validate_app_installed_on_sites(app, bench_path="."):
	print("Checking if app installed on active sites...")
	ret = check_app_installed(app, bench_path=bench_path)

	if ret is None:
		check_app_installed_legacy(app, bench_path=bench_path)
	else:
		return ret


def check_app_installed(app, bench_path="."):
	try:
		out = subprocess.check_output(
			["bench", "--site", "all", "list-apps", "--format", "json"],
			stderr=open(os.devnull, "wb"),
			cwd=bench_path,
		).decode('utf-8')
	except subprocess.CalledProcessError:
		return None

	try:
		apps_sites_dict = json.loads(out)
	except JSONDecodeError:
		return None

	for site, apps in apps_sites_dict.items():
		if app in apps:
			print("Cannot remove, app is installed on site: {0}".format(site))
			sys.exit(1)


def check_app_installed_legacy(app, bench_path="."):
	site_path = os.path.join(bench_path, 'sites')

	for site in os.listdir(site_path):
		req_file = os.path.join(site_path, site, 'site_config.json')
		if os.path.exists(req_file):
			out = subprocess.check_output(["bench", "--site", site, "list-apps"], cwd=bench_path).decode('utf-8')
			if re.search(r'\b' + app + r'\b', out):
				print(f"Cannot remove, app is installed on site: {site}")
				sys.exit(1)


def pull_apps(apps=None, bench_path='.', reset=False):
	'''Check all apps if there no local changes, pull'''
	from bench.config.common_site_config import get_config

	rebase = '--rebase' if get_config(bench_path).get('rebase_on_pull') else ''

	apps = apps or get_apps(bench_path=bench_path)
	# check for local changes
	if not reset:
		for app in apps:
			excluded_apps = get_excluded_apps()
			if app in excluded_apps:
				print(f"Skipping reset for app {app}")
				continue
			app_dir = get_repo_dir(app, bench_path=bench_path)
			if os.path.exists(os.path.join(app_dir, '.git')):
				out = subprocess.check_output('git status', shell=True, cwd=app_dir)
				out = out.decode('utf-8')
				if not re.search(r'nothing to commit, working (directory|tree) clean', out):
					print(f'''

Cannot proceed with update: You have local changes in app "{app}" that are not committed.

Here are your choices:

1. Merge the {app} app manually with "git pull" / "git pull --rebase" and fix conflicts.
1. Temporarily remove your changes with "git stash" or discard them completely
	with "bench update --reset" or for individual repositries "git reset --hard"
2. If your changes are helpful for others, send in a pull request via GitHub and
	wait for them to be merged in the core.''')
					sys.exit(1)

	excluded_apps = get_excluded_apps()
	for app in apps:
		if app in excluded_apps:
			print(f"Skipping pull for app {app}")
			continue
		app_dir = get_repo_dir(app, bench_path=bench_path)
		if os.path.exists(os.path.join(app_dir, '.git')):
			remote = get_remote(app)
			if not remote:
				# remote is False, i.e. remote doesn't exist, add the app to excluded_apps.txt
				add_to_excluded_apps_txt(app, bench_path=bench_path)
				print(f"Skipping pull for app {app}, since remote doesn't exist, and adding it to excluded apps")
				continue

			if not get_config(bench_path).get('shallow_clone') or not reset:
				is_shallow = os.path.exists(os.path.join(app_dir, ".git", "shallow"))
				if is_shallow:
					s = " to safely pull remote changes." if not reset else ""
					print(f"Unshallowing {app}{s}")
					exec_cmd(f"git fetch {remote} --unshallow", cwd=app_dir)

			branch = get_current_branch(app, bench_path=bench_path)
			logger.log(f'pulling {app}')
			if reset:
				reset_cmd = f"git reset --hard {remote}/{branch}"
				if get_config(bench_path).get('shallow_clone'):
					exec_cmd(f"git fetch --depth=1 --no-tags {remote} {branch}",
						cwd=app_dir)
					exec_cmd(reset_cmd, cwd=app_dir)
					exec_cmd("git reflog expire --all", cwd=app_dir)
					exec_cmd("git gc --prune=all", cwd=app_dir)
				else:
					exec_cmd("git fetch --all", cwd=app_dir)
					exec_cmd(reset_cmd, cwd=app_dir)
			else:
				exec_cmd(f"git pull {rebase} {remote} {branch}", cwd=app_dir)
			exec_cmd('find . -name "*.pyc" -delete', cwd=app_dir)


def is_version_upgrade(app='frappe', bench_path='.', branch=None):
	upstream_version = get_upstream_version(app=app, branch=branch, bench_path=bench_path)

	if not upstream_version:
		raise InvalidBranchException(f'Specified branch of app {app} is not in upstream remote')

	local_version = get_major_version(get_current_version(app, bench_path=bench_path))
	upstream_version = get_major_version(upstream_version)

	if upstream_version > local_version:
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

def get_remote(app, bench_path='.'):
	repo_dir = get_repo_dir(app, bench_path=bench_path)
	contents = subprocess.check_output(['git', 'remote', '-v'], cwd=repo_dir, stderr=subprocess.STDOUT)
	contents = contents.decode('utf-8')
	if re.findall('upstream[\s]+', contents):
		return 'upstream'
	elif not contents:
		# if contents is an empty string => remote doesn't exist
		return False
	else:
		# get the first remote
		return contents.splitlines()[0].split()[0]

def use_rq(bench_path):
	bench_path = os.path.abspath(bench_path)
	celery_app = os.path.join(bench_path, 'apps', 'frappe', 'frappe', 'celery_app.py')
	return not os.path.exists(celery_app)

def get_current_version(app, bench_path='.'):
	current_version = None
	repo_dir = get_repo_dir(app, bench_path=bench_path)
	config_path = os.path.join(repo_dir, "setup.cfg")
	init_path = os.path.join(repo_dir, os.path.basename(repo_dir), '__init__.py')
	setup_path = os.path.join(repo_dir, 'setup.py')

	try:
		if os.path.exists(config_path):
			config = read_configuration(config_path)
			current_version = config.get("metadata", {}).get("version")
		if not current_version:
			with open(init_path) as f:
				current_version = get_version_from_string(f.read())

	except AttributeError:
		# backward compatibility
		with open(setup_path) as f:
			current_version = get_version_from_string(f.read(), field='version')

	return current_version

def get_develop_version(app, bench_path='.'):
	repo_dir = get_repo_dir(app, bench_path=bench_path)
	with open(os.path.join(repo_dir, os.path.basename(repo_dir), 'hooks.py')) as f:
		return get_version_from_string(f.read(), field='develop_version')

def get_upstream_version(app, branch=None, bench_path='.'):
	repo_dir = get_repo_dir(app, bench_path=bench_path)
	if not branch:
		branch = get_current_branch(app, bench_path=bench_path)

	try:
		subprocess.call(f'git fetch --depth=1 --no-tags upstream {branch}', shell=True, cwd=repo_dir)
	except CommandFailedError:
		raise InvalidRemoteException(f'Failed to fetch from remote named upstream for {app}')

	try:
		contents = subprocess.check_output(f'git show upstream/{branch}:{app}/__init__.py',
			shell=True, cwd=repo_dir, stderr=subprocess.STDOUT)
		contents = contents.decode('utf-8')
	except subprocess.CalledProcessError as e:
		if b"Invalid object" in e.output:
			return None
		else:
			raise
	return get_version_from_string(contents)

def get_repo_dir(app, bench_path='.'):
	return os.path.join(bench_path, 'apps', app)

def switch_branch(branch, apps=None, bench_path='.', upgrade=False, check_upgrade=True):
	import git
	import importlib
	from bench.utils import update_requirements, update_node_packages, backup_all_sites, patch_sites, build_assets, post_upgrade

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

		if not os.path.exists(app_dir):
			bench.utils.log(f"{app} does not exist!", level=2)
			continue

		repo = git.Repo(app_dir)
		unshallow_flag = os.path.exists(os.path.join(app_dir, ".git", "shallow"))
		bench.utils.log(f"Fetching upstream {'unshallow ' if unshallow_flag else ''}for {app}")

		bench.utils.exec_cmd("git remote set-branches upstream  '*'", cwd=app_dir)
		bench.utils.exec_cmd(f"git fetch --all{' --unshallow' if unshallow_flag else ''} --quiet", cwd=app_dir)

		if check_upgrade:
			version_upgrade = is_version_upgrade(app=app, bench_path=bench_path, branch=branch)
			if version_upgrade[0] and not upgrade:
				bench.utils.log(f"Switching to {branch} will cause upgrade from {version_upgrade[1]} to {version_upgrade[2]}. Pass --upgrade to confirm", level=2)
				sys.exit(1)

		print("Switching for "+app)
		bench.utils.exec_cmd(f"git checkout -f {branch}", cwd=app_dir)

		if str(repo.active_branch) == branch:
			switched_apps.append(app)
		else:
			bench.utils.log(f"Switching branches failed for: {app}", level=2)

	if switched_apps:
		bench.utils.log("Successfully switched branches for: " + ", ".join(switched_apps), level=1)
		print('Please run `bench update --patch` to be safe from any differences in database schema')

	if version_upgrade[0] and upgrade:
		update_requirements()
		update_node_packages()
		importlib.reload(bench.utils)
		backup_all_sites()
		patch_sites()
		build_assets()
		post_upgrade(version_upgrade[1], version_upgrade[2])


def switch_to_branch(branch=None, apps=None, bench_path='.', upgrade=False):
	switch_branch(branch, apps=apps, bench_path=bench_path, upgrade=upgrade)

def switch_to_develop(apps=None, bench_path='.', upgrade=True):
	switch_branch('develop', apps=apps, bench_path=bench_path, upgrade=upgrade)

def get_version_from_string(contents, field='__version__'):
	match = re.search(r"^(\s*%s\s*=\s*['\\\"])(.+?)(['\"])(?sm)" % field, contents)
	return match.group(2)

def get_major_version(version):
	import semantic_version

	return semantic_version.Version(version).major

def install_apps_from_path(path, bench_path='.'):
	apps = get_apps_json(path)
	for app in apps:
		get_app(app['url'], branch=app.get('branch'), bench_path=bench_path, skip_assets=True)

def get_apps_json(path):
	import requests

	if path.startswith('http'):
		r = requests.get(path)
		return r.json()

	with open(path) as f:
		return json.load(f)

def validate_branch():
	installed_apps = set(get_apps())
	check_apps = set(['frappe', 'erpnext'])
	intersection_apps = installed_apps.intersection(check_apps)

	for app in intersection_apps:
		branch = get_current_branch(app)

		if branch == "master":
			print("""'master' branch is renamed to 'version-11' since 'version-12' release.
As of January 2020, the following branches are
version		Frappe			ERPNext
11		version-11		version-11
12		version-12		version-12
13		version-13		version-13
14		develop			develop

Please switch to new branches to get future updates.
To switch to your required branch, run the following commands: bench switch-to-branch [branch-name]""")

			sys.exit(1)
