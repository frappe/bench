# imports - standard imports
import json
import logging
import os
import re
import shutil
import subprocess
import sys

# imports - third party imports
import click

# imports - module imports
import bench
from bench.bench import Bench
from bench.utils import exec_cmd, is_bench_directory, run_frappe_cmd, is_git_url, fetch_details_from_tag
from bench.utils.app import get_app_name
from bench.utils.bench import get_env_cmd, build_assets, restart_supervisor_processes, restart_systemd_processes

logger = logging.getLogger(bench.PROJECT_NAME)


class AppMeta:
	def __init__(self, name: str, branch : str = None):
		"""
		name (str): This could look something like
			1. https://github.com/frappe/healthcare.git
			2. git@github.com:frappe/healthcare.git
			3. frappe/healthcare@develop
			4. healthcare
			5. healthcare@develop, healthcare@v13.12.1

		References for Version Identifiers:
		 * https://www.python.org/dev/peps/pep-0440/#version-specifiers
		 * https://docs.npmjs.com/about-semantic-versioning

		class Healthcare(AppConfig):
			dependencies = [{"frappe/erpnext": "~13.17.0"}]
		"""
		self.name = name
		self.remote_server = "github.com"
		self.on_disk = False
		self.use_ssh = False
		self.branch = branch
		self.setup_details()

	def setup_details(self):
		# fetch meta for repo on mounted disk
		if os.path.exists(self.name):
			self.on_disk = True
			self._setup_details_from_mounted_disk()

		# fetch meta for repo from remote git server - traditional get-app url
		elif is_git_url(self.name):
			self._setup_details_from_git_url()

		# fetch meta from new styled name tags & first party apps on github
		else:
			self._setup_details_from_name_tag()

	def _setup_details_from_name_tag(self):
		self.org, self.repo, self.tag = fetch_details_from_tag(self.name)

	def _setup_details_from_mounted_disk(self):
		self.org, self.repo, self.tag = os.path.split(self.name)[-2:] + (self.branch,)

	def _setup_details_from_git_url(self):
		return self.__setup_details_from_git()

	def __setup_details_from_git(self):
		if self.use_ssh:
			self.org, _repo = self.name.split(":")[1].split("/")
		else:
			self.org, _repo = self.name.split("/")[-2:]

		self.tag = self.branch
		self.repo = _repo.split(".")[0]

	@property
	def url(self):
		if self.on_disk:
			return os.path.abspath(self.name)

		if self.use_ssh:
			return self.get_ssh_url()

		return self.get_http_url()

	def get_http_url(self):
		return f"https://{self.remote_server}/{self.org}/{self.repo}.git"

	def get_ssh_url(self):
		return f"git@{self.remote_server}:{self.org}/{self.repo}.git"


class App(AppMeta):
	def __init__(self, name: str, branch : str = None, bench=None):
		super().__init__(name, branch)
		self.bench = bench


def add_to_appstxt(app, bench_path='.'):
	apps = Bench(bench_path).apps

	if app not in apps:
		apps.append(app)
		return write_appstxt(apps, bench_path=bench_path)

def remove_from_appstxt(app, bench_path='.'):
	apps = Bench(bench_path).apps

	if app in apps:
		apps.remove(app)
		return write_appstxt(apps, bench_path=bench_path)

def write_appstxt(apps, bench_path='.'):
	with open(os.path.join(bench_path, 'sites', 'apps.txt'), 'w') as f:
		return f.write('\n'.join(apps))

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

def generate_bench_name(git_url, bench_path):
	if os.path.exists(git_url):
		guessed_app_name = os.path.basename(git_url)
	else:
		app = App(git_url)
		guessed_app_name = f"{app.org}_{app.repo}"

	return os.path.join(bench_path, f"{guessed_app_name}-bench")

def setup_app_dependencies(repo_name, bench_path='.', branch=None):
	# branch kwarg is somewhat of a hack here; since we're assuming the same branches for all apps
	# for eg: if you're installing erpnext@develop, you'll want frappe@develop and healthcare@develop too
	import glob

	apps_path = os.path.join(os.path.abspath(bench_path), 'apps')
	files = glob.glob(os.path.join(apps_path, repo_name, '**', 'hooks.py'))

	if files:
		lines = [x for x in open(files[0]).read().split('\n') if x.strip().startswith('required_apps')]
		if lines:
			required_apps = eval(lines[0].strip('required_apps').strip().lstrip('=').strip())
			# TODO: when the time comes, add version check here
			for app in required_apps:
				if app not in Bench(bench_path).apps:
					get_app(app, bench_path=bench_path, branch=branch)

def get_app(git_url, branch=None, bench_path='.', skip_assets=False, verbose=False, overwrite=False):
	"""bench get-app clones a Frappe App from remote (GitHub or any other git server),
	and installs it on the current bench. This also resolves dependencies based on the
	apps' required_apps defined in the hooks.py file.

	If the bench_path is not a bench directory, a new bench is created named using the
	git_url parameter.
	"""
	app = App(git_url, branch=branch)
	git_url = app.url
	repo_name = app.repo
	branch = app.tag

	if not is_bench_directory(bench_path):
		bench_path = generate_bench_name(git_url, bench_path)
		from bench.commands.make import init
		click.get_current_context().invoke(init, path=bench_path, frappe_branch=branch)

	cloned_path = os.path.join(bench_path, 'apps', repo_name)
	dir_already_exists = os.path.isdir(cloned_path)
	to_clone = not dir_already_exists
	to_resolve_dependencies = True
	to_install = True

	if dir_already_exists:
		# application directory already exists
		# prompt user to overwrite it
		if overwrite or click.confirm(
			f"A directory for the application '{repo_name}' already exists."
			"Do you want to continue and overwrite it?"
		):
			import shutil
			shutil.rmtree(cloned_path)
			to_clone = True
		elif click.confirm("Do you want to reinstall the existing application?", abort=True):
			pass

	if to_clone:
		fetch_txt = f"Getting {repo_name}"
		click.secho(fetch_txt, fg="yellow")
		logger.log(fetch_txt)

		git_branch = f'--branch {app.tag}' if app.tag else ''
		shallow_clone = '--depth 1' if check_git_for_shallow_clone() else ''
		exec_cmd(
			f"git clone {git_url} {git_branch} {shallow_clone} --origin upstream",
			cwd=os.path.join(bench_path, 'apps')
		)

	if to_resolve_dependencies:
		setup_app_dependencies(
			repo_name=repo_name, bench_path=bench_path, branch=branch
		)

	if to_install:
		app_name = get_app_name(bench_path, repo_name)
		install_app(
			app=app_name, bench_path=bench_path, verbose=verbose, skip_assets=skip_assets
		)

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
	from bench.utils import get_env_cmd

	install_text = f'Installing {app}'
	click.secho(install_text, fg="yellow")
	logger.log(install_text)

	python_path = get_env_cmd("python", bench_path=bench_path)
	quiet_flag = "-q" if not verbose else ""
	app_path = os.path.join(bench_path, "apps", app)
	cache_flag = "--no-cache-dir" if no_cache else ""

	exec_cmd(f"{python_path} -m pip install {quiet_flag} -U -e {app_path} {cache_flag}")

	if os.path.exists(os.path.join(app_path, 'package.json')):
		exec_cmd("yarn install", cwd=app_path)

	add_to_appstxt(app, bench_path=bench_path)

	conf = Bench(bench_path).conf

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

	bench = Bench(bench_path)
	app_path = os.path.join(bench_path, 'apps', app)
	py = os.path.join(bench_path, 'env', 'bin', 'python')

	# validate app removal
	if app not in bench.apps:
		print(f"No app named {app}")
		sys.exit(1)

	validate_app_installed_on_sites(app, bench_path=bench_path)

	# remove app from bench
	exec_cmd("{0} -m pip uninstall -y {1}".format(py, app), cwd=bench_path)
	remove_from_appstxt(app, bench_path)
	shutil.rmtree(app_path)

	# re-build assets and restart processes
	run_frappe_cmd("build", bench_path=bench_path)

	if bench.conf.get('restart_supervisor_on_update'):
		restart_supervisor_processes(bench_path=bench_path)
	if bench.conf.get('restart_systemd_on_update'):
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
	bench = Bench(bench_path)
	rebase = '--rebase' if bench.conf.get('rebase_on_pull') else ''
	apps = apps or bench.apps

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

			if not bench.conf.get('shallow_clone') or not reset:
				is_shallow = os.path.exists(os.path.join(app_dir, ".git", "shallow"))
				if is_shallow:
					s = " to safely pull remote changes." if not reset else ""
					print(f"Unshallowing {app}{s}")
					bench.run(f"git fetch {remote} --unshallow", cwd=app_dir)

			branch = get_current_branch(app, bench_path=bench_path)
			logger.log(f'pulling {app}')
			if reset:
				reset_cmd = f"git reset --hard {remote}/{branch}"
				if bench.conf.get('shallow_clone'):
					bench.run(f"git fetch --depth=1 --no-tags {remote} {branch}", cwd=app_dir)
					bench.run(reset_cmd, cwd=app_dir)
					bench.run("git reflog expire --all", cwd=app_dir)
					bench.run("git gc --prune=all", cwd=app_dir)
				else:
					bench.run("git fetch --all", cwd=app_dir)
					bench.run(reset_cmd, cwd=app_dir)
			else:
				bench.run(f"git pull {rebase} {remote} {branch}", cwd=app_dir)
			bench.run('find . -name "*.pyc" -delete', cwd=app_dir)


def use_rq(bench_path):
	bench_path = os.path.abspath(bench_path)
	celery_app = os.path.join(bench_path, 'apps', 'frappe', 'frappe', 'celery_app.py')
	return not os.path.exists(celery_app)

def get_repo_dir(app, bench_path='.'):
	return os.path.join(bench_path, 'apps', app)

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
