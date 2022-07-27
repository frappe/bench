# imports - standard imports
import functools
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import typing
from collections import OrderedDict
from datetime import date
from urllib.parse import urlparse

# imports - third party imports
import click
from git import Repo

# imports - module imports
import bench
from bench.exceptions import NotInBenchDirectoryError
from bench.utils import (
	UNSET_ARG,
	fetch_details_from_tag,
	get_available_folder_name,
	is_bench_directory,
	is_git_url,
	is_valid_frappe_branch,
	log,
	run_frappe_cmd,
)
from bench.utils.bench import build_assets, install_python_dev_dependencies
from bench.utils.render import step

if typing.TYPE_CHECKING:
	from bench.bench import Bench


logger = logging.getLogger(bench.PROJECT_NAME)


class AppMeta:
	def __init__(self, name: str, branch: str = None, to_clone: bool = True):
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
		self.name = name.rstrip("/")
		self.remote_server = "github.com"
		self.to_clone = to_clone
		self.on_disk = False
		self.use_ssh = False
		self.from_apps = False
		self.is_url = False
		self.branch = branch
		self.app_name = None
		self.git_repo = None
		self.mount_path = os.path.abspath(
			os.path.join(urlparse(self.name).netloc, urlparse(self.name).path)
		)
		self.setup_details()

	def setup_details(self):
		# fetch meta from installed apps
		if self.bench and os.path.exists(os.path.join(self.bench.name, "apps", self.name)):
			self.mount_path = os.path.join(self.bench.name, "apps", self.name)
			self.from_apps = True
			self._setup_details_from_mounted_disk()

		# fetch meta for repo on mounted disk
		elif os.path.exists(self.mount_path):
			self.on_disk = True
			self._setup_details_from_mounted_disk()

		# fetch meta for repo from remote git server - traditional get-app url
		elif is_git_url(self.name):
			self.is_url = True
			self._setup_details_from_git_url()

		# fetch meta from new styled name tags & first party apps on github
		else:
			self._setup_details_from_name_tag()

		if self.git_repo:
			self.app_name = os.path.basename(os.path.normpath(self.git_repo.working_tree_dir))
		else:
			self.app_name = self.repo

	def _setup_details_from_mounted_disk(self):
		# If app is a git repo
		self.git_repo = Repo(self.mount_path)
		try:
			self._setup_details_from_git_url(self.git_repo.remotes[0].url)
			if not (self.branch or self.tag):
				self.tag = self.branch = self.git_repo.active_branch.name
		except IndexError:
			self.org, self.repo, self.tag = os.path.split(self.mount_path)[-2:] + (self.branch,)
		except TypeError:
			# faced a "a detached symbolic reference as it points" in case you're in the middle of
			# some git shenanigans
			self.tag = self.branch = None

	def _setup_details_from_name_tag(self):
		self.org, self.repo, self.tag = fetch_details_from_tag(self.name)
		self.tag = self.tag or self.branch

	def _setup_details_from_git_url(self, url=None):
		return self.__setup_details_from_git(url)

	def __setup_details_from_git(self, url=None):
		name = url if url else self.name
		if name.startswith("git@") or name.startswith("ssh://"):
			self.use_ssh = True
			_first_part, _second_part = name.rsplit(":", 1)
			self.remote_server = _first_part.split("@")[-1]
			self.org, _repo = _second_part.rsplit("/", 1)
		else:
			protocal = "https://" if "https://" in name else "http://"
			self.remote_server, self.org, _repo = name.replace(protocal, "").rsplit("/", 2)

		self.tag = self.branch
		self.repo = _repo.split(".")[0]

	@property
	def url(self):
		if self.is_url or self.from_apps or self.on_disk:
			return self.name

		if self.use_ssh:
			return self.get_ssh_url()

		return self.get_http_url()

	def get_http_url(self):
		return f"https://{self.remote_server}/{self.org}/{self.repo}.git"

	def get_ssh_url(self):
		return f"git@{self.remote_server}:{self.org}/{self.repo}.git"


@functools.lru_cache(maxsize=None)
class App(AppMeta):
	def __init__(
		self,
		name: str,
		branch: str = None,
		bench: "Bench" = None,
		soft_link: bool = False,
		*args,
		**kwargs,
	):
		self.bench = bench
		self.soft_link = soft_link
		self.required_by = None
		self.local_resolution = []
		super().__init__(name, branch, *args, **kwargs)

	@step(title="Fetching App {repo}", success="App {repo} Fetched")
	def get(self):
		branch = f"--branch {self.tag}" if self.tag else ""
		shallow = "--depth 1" if self.bench.shallow_clone else ""

		if not self.soft_link:
			cmd = "git clone"
			args = f"{self.url} {branch} {shallow} --origin upstream"
		else:
			cmd = "ln -s"
			args = f"{self.name}"

		fetch_txt = f"Getting {self.repo}"
		click.secho(fetch_txt, fg="yellow")
		logger.log(fetch_txt)

		self.bench.run(
			f"{cmd} {args}",
			cwd=os.path.join(self.bench.name, "apps"),
		)

	@step(title="Archiving App {repo}", success="App {repo} Archived")
	def remove(self, no_backup: bool = False):
		active_app_path = os.path.join("apps", self.name)

		if no_backup:
			shutil.rmtree(active_app_path)
			log(f"App deleted from {active_app_path}")
		else:
			archived_path = os.path.join("archived", "apps")
			archived_name = get_available_folder_name(
				f"{self.repo}-{date.today()}", archived_path
			)
			archived_app_path = os.path.join(archived_path, archived_name)

			shutil.move(active_app_path, archived_app_path)
			log(f"App moved from {active_app_path} to {archived_app_path}")

		self.from_apps = False
		self.on_disk = False

	@step(title="Installing App {repo}", success="App {repo} Installed")
	def install(
		self,
		skip_assets=False,
		verbose=False,
		resolved=False,
		restart_bench=True,
		ignore_resolution=False,
	):
		import bench.cli
		from bench.utils.app import get_app_name

		verbose = bench.cli.verbose or verbose
		app_name = get_app_name(self.bench.name, self.app_name)
		if not resolved and self.repo != "frappe" and not ignore_resolution:
			click.secho(
				f"Ignoring dependencies of {self.name}. To install dependencies use --resolve-deps",
				fg="yellow",
			)

		install_app(
			app=app_name,
			tag=self.tag,
			bench_path=self.bench.name,
			verbose=verbose,
			skip_assets=skip_assets,
			restart_bench=restart_bench,
			resolution=self.local_resolution,
		)

	@step(title="Cloning and installing {repo}", success="App {repo} Installed")
	def install_resolved_apps(self, *args, **kwargs):
		self.get()
		self.install(*args, **kwargs, resolved=True)

	@step(title="Uninstalling App {repo}", success="App {repo} Uninstalled")
	def uninstall(self):
		self.bench.run(f"{self.bench.python} -m pip uninstall -y {self.name}")

	def _get_dependencies(self):
		from bench.utils.app import get_required_deps, required_apps_from_hooks

		if self.on_disk:
			required_deps = os.path.join(self.mount_path, self.repo, "hooks.py")
			try:
				return required_apps_from_hooks(required_deps, local=True)
			except IndexError:
				return []
		try:
			required_deps = get_required_deps(self.org, self.repo, self.tag or self.branch)
			return required_apps_from_hooks(required_deps)
		except Exception:
			return []

	def update_app_state(self):
		from bench.bench import Bench

		bench = Bench(self.bench.name)
		bench.apps.sync(
			app_dir=self.app_name,
			app_name=self.name,
			branch=self.tag,
			required=self.local_resolution,
		)


def make_resolution_plan(app: App, bench: "Bench"):
	"""
	decide what apps and versions to install and in what order
	"""
	resolution = OrderedDict()
	resolution[app.repo] = app

	for app_name in app._get_dependencies():
		dep_app = App(app_name, bench=bench)
		is_valid_frappe_branch(dep_app.url, dep_app.branch)
		dep_app.required_by = app.name
		if dep_app.repo in resolution:
			click.secho(f"{dep_app.repo} is already resolved skipping", fg="yellow")
			continue
		resolution[dep_app.repo] = dep_app
		resolution.update(make_resolution_plan(dep_app, bench))
		app.local_resolution = [repo_name for repo_name, _ in reversed(resolution.items())]
	return resolution


def get_excluded_apps(bench_path="."):
	try:
		with open(os.path.join(bench_path, "sites", "excluded_apps.txt")) as f:
			return f.read().strip().split("\n")
	except OSError:
		return []


def add_to_excluded_apps_txt(app, bench_path="."):
	if app == "frappe":
		raise ValueError("Frappe app cannot be excludeed from update")
	if app not in os.listdir("apps"):
		raise ValueError(f"The app {app} does not exist")
	apps = get_excluded_apps(bench_path=bench_path)
	if app not in apps:
		apps.append(app)
		return write_excluded_apps_txt(apps, bench_path=bench_path)


def write_excluded_apps_txt(apps, bench_path="."):
	with open(os.path.join(bench_path, "sites", "excluded_apps.txt"), "w") as f:
		return f.write("\n".join(apps))


def remove_from_excluded_apps_txt(app, bench_path="."):
	apps = get_excluded_apps(bench_path=bench_path)
	if app in apps:
		apps.remove(app)
		return write_excluded_apps_txt(apps, bench_path=bench_path)


def get_app(
	git_url,
	branch=None,
	bench_path=".",
	skip_assets=False,
	verbose=False,
	overwrite=False,
	soft_link=False,
	init_bench=False,
	resolve_deps=False,
):
	"""bench get-app clones a Frappe App from remote (GitHub or any other git server),
	and installs it on the current bench. This also resolves dependencies based on the
	apps' required_apps defined in the hooks.py file.

	If the bench_path is not a bench directory, a new bench is created named using the
	git_url parameter.
	"""
	import bench as _bench
	import bench.cli as bench_cli
	from bench.bench import Bench
	from bench.utils.app import check_existing_dir

	bench = Bench(bench_path)
	app = App(git_url, branch=branch, bench=bench, soft_link=soft_link)
	git_url = app.url
	repo_name = app.repo
	branch = app.tag
	bench_setup = False
	restart_bench = not init_bench
	frappe_path, frappe_branch = None, None

	if resolve_deps:
		resolution = make_resolution_plan(app, bench)
		click.secho("Following apps will be installed", fg="bright_blue")
		for idx, app in enumerate(reversed(resolution.values()), start=1):
			print(
				f"{idx}. {app.name} {f'(required by {app.required_by})' if app.required_by else ''}"
			)

		if "frappe" in resolution:
			# Todo: Make frappe a terminal dependency for all frappe apps.
			frappe_path, frappe_branch = resolution["frappe"].url, resolution["frappe"].tag

	if not is_bench_directory(bench_path):
		if not init_bench:
			raise NotInBenchDirectoryError(
				f"{os.path.realpath(bench_path)} is not a valid bench directory. "
				"Run with --init-bench if you'd like to create a Bench too."
			)

		from bench.utils.system import init

		bench_path = get_available_folder_name(f"{app.repo}-bench", bench_path)
		init(
			path=bench_path,
			frappe_path=frappe_path,
			frappe_branch=frappe_branch or branch,
		)
		os.chdir(bench_path)
		bench_setup = True

	if bench_setup and bench_cli.from_command_line and bench_cli.dynamic_feed:
		_bench.LOG_BUFFER.append(
			{
				"message": f"Fetching App {repo_name}",
				"prefix": click.style("⏼", fg="bright_yellow"),
				"is_parent": True,
				"color": None,
			}
		)

	if resolve_deps:
		install_resolved_deps(
			bench,
			resolution,
			bench_path=bench_path,
			skip_assets=skip_assets,
			verbose=verbose,
		)
		return

	dir_already_exists, cloned_path = check_existing_dir(bench_path, repo_name)
	to_clone = not dir_already_exists

	# application directory already exists
	# prompt user to overwrite it
	if dir_already_exists and (
		overwrite
		or click.confirm(
			f"A directory for the application '{repo_name}' already exists. "
			"Do you want to continue and overwrite it?"
		)
	):
		app.remove()
		to_clone = True

	if to_clone:
		app.get()

	if (
		to_clone
		or overwrite
		or click.confirm("Do you want to reinstall the existing application?")
	):
		app.install(verbose=verbose, skip_assets=skip_assets, restart_bench=restart_bench)


def install_resolved_deps(
	bench,
	resolution,
	bench_path=".",
	skip_assets=False,
	verbose=False,
):
	from bench.utils.app import check_existing_dir

	if "frappe" in resolution:
		# Terminal dependency
		del resolution["frappe"]

	for repo_name, app in reversed(resolution.items()):
		existing_dir, path_to_app = check_existing_dir(bench_path, repo_name)
		if existing_dir:
			is_compatible = False

			try:
				installed_branch = bench.apps.states[repo_name]["resolution"]["branch"].strip()
			except Exception:
				installed_branch = (
					subprocess.check_output(
						"git rev-parse --abbrev-ref HEAD", shell=True, cwd=path_to_app
					)
					.decode("utf-8")
					.rstrip()
				)
			try:
				if app.tag is None:
					current_remote = (
						subprocess.check_output(
							f"git config branch.{installed_branch}.remote", shell=True, cwd=path_to_app
						)
						.decode("utf-8")
						.rstrip()
					)

					default_branch = (
						subprocess.check_output(
							f"git symbolic-ref refs/remotes/{current_remote}/HEAD",
							shell=True,
							cwd=path_to_app,
						)
						.decode("utf-8")
						.rsplit("/")[-1]
						.strip()
					)
					is_compatible = default_branch == installed_branch
				else:
					is_compatible = installed_branch == app.tag
			except Exception:
				is_compatible = False

			prefix = "C" if is_compatible else "Inc"
			click.secho(
				f"{prefix}ompatible version of {repo_name} is already installed",
				fg="green" if is_compatible else "red",
			)
			app.update_app_state()
			if click.confirm(
				f"Do you wish to clone and install the already installed {prefix}ompatible app"
			):
				click.secho(f"Removing installed app {app.name}", fg="yellow")
				shutil.rmtree(path_to_app)
			else:
				continue
		app.install_resolved_apps(skip_assets=skip_assets, verbose=verbose)


def new_app(app, no_git=None, bench_path="."):
	if bench.FRAPPE_VERSION in (0, None):
		raise NotInBenchDirectoryError(
			f"{os.path.realpath(bench_path)} is not a valid bench directory."
		)

	# For backwards compatibility
	app = app.lower().replace(" ", "_").replace("-", "_")
	if app[0].isdigit() or "." in app:
		click.secho(
			"App names cannot start with numbers(digits) or have dot(.) in them", fg="red"
		)
		return

	apps = os.path.abspath(os.path.join(bench_path, "apps"))
	args = ["make-app", apps, app]
	if no_git:
		if bench.FRAPPE_VERSION < 14:
			click.secho("Frappe v14 or greater is needed for '--no-git' flag", fg="red")
			return
		args.append(no_git)

	logger.log(f"creating new app {app}")
	run_frappe_cmd(*args, bench_path=bench_path)
	install_app(app, bench_path=bench_path)


def install_app(
	app,
	tag=None,
	bench_path=".",
	verbose=False,
	no_cache=False,
	restart_bench=True,
	skip_assets=False,
	resolution=UNSET_ARG,
):
	import bench.cli as bench_cli
	from bench.bench import Bench

	install_text = f"Installing {app}"
	click.secho(install_text, fg="yellow")
	logger.log(install_text)

	if resolution == UNSET_ARG:
		resolution = []

	bench = Bench(bench_path)
	conf = bench.conf

	verbose = bench_cli.verbose or verbose
	quiet_flag = "" if verbose else "--quiet"
	cache_flag = "--no-cache-dir" if no_cache else ""

	app_path = os.path.realpath(os.path.join(bench_path, "apps", app))

	bench.run(
		f"{bench.python} -m pip install {quiet_flag} --upgrade -e {app_path} {cache_flag}"
	)

	if conf.get("developer_mode"):
		install_python_dev_dependencies(apps=app, bench_path=bench_path, verbose=verbose)

	if os.path.exists(os.path.join(app_path, "package.json")):
		bench.run("yarn install", cwd=app_path)

	bench.apps.sync(app_name=app, required=resolution, branch=tag, app_dir=app_path)

	if not skip_assets:
		build_assets(bench_path=bench_path, app=app)

	if restart_bench:
		bench.reload()


def pull_apps(apps=None, bench_path=".", reset=False):
	"""Check all apps if there no local changes, pull"""
	from bench.bench import Bench
	from bench.utils.app import get_current_branch, get_remote

	bench = Bench(bench_path)
	rebase = "--rebase" if bench.conf.get("rebase_on_pull") else ""
	apps = apps or bench.apps
	excluded_apps = bench.excluded_apps

	# check for local changes
	if not reset:
		for app in apps:
			if app in excluded_apps:
				print(f"Skipping reset for app {app}")
				continue
			app_dir = get_repo_dir(app, bench_path=bench_path)
			if os.path.exists(os.path.join(app_dir, ".git")):
				out = subprocess.check_output("git status", shell=True, cwd=app_dir)
				out = out.decode("utf-8")
				if not re.search(r"nothing to commit, working (directory|tree) clean", out):
					print(
						f"""

Cannot proceed with update: You have local changes in app "{app}" that are not committed.

Here are your choices:

1. Merge the {app} app manually with "git pull" / "git pull --rebase" and fix conflicts.
1. Temporarily remove your changes with "git stash" or discard them completely
	with "bench update --reset" or for individual repositries "git reset --hard"
2. If your changes are helpful for others, send in a pull request via GitHub and
	wait for them to be merged in the core."""
					)
					sys.exit(1)

	for app in apps:
		if app in excluded_apps:
			print(f"Skipping pull for app {app}")
			continue
		app_dir = get_repo_dir(app, bench_path=bench_path)
		if os.path.exists(os.path.join(app_dir, ".git")):
			remote = get_remote(app)
			if not remote:
				# remote is False, i.e. remote doesn't exist, add the app to excluded_apps.txt
				add_to_excluded_apps_txt(app, bench_path=bench_path)
				print(
					f"Skipping pull for app {app}, since remote doesn't exist, and"
					" adding it to excluded apps"
				)
				continue

			if not bench.conf.get("shallow_clone") or not reset:
				is_shallow = os.path.exists(os.path.join(app_dir, ".git", "shallow"))
				if is_shallow:
					s = " to safely pull remote changes." if not reset else ""
					print(f"Unshallowing {app}{s}")
					bench.run(f"git fetch {remote} --unshallow", cwd=app_dir)

			branch = get_current_branch(app, bench_path=bench_path)
			logger.log(f"pulling {app}")
			if reset:
				reset_cmd = f"git reset --hard {remote}/{branch}"
				if bench.conf.get("shallow_clone"):
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
	celery_app = os.path.join(bench_path, "apps", "frappe", "frappe", "celery_app.py")
	return not os.path.exists(celery_app)


def get_repo_dir(app, bench_path="."):
	return os.path.join(bench_path, "apps", app)


def install_apps_from_path(path, bench_path="."):
	apps = get_apps_json(path)
	for app in apps:
		get_app(
			app["url"],
			branch=app.get("branch"),
			bench_path=bench_path,
			skip_assets=True,
		)


def get_apps_json(path):
	import requests

	if path.startswith("http"):
		r = requests.get(path)
		return r.json()

	with open(path) as f:
		return json.load(f)
