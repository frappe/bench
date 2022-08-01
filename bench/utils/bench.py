# imports - standard imports
import contextlib
import json
import logging
import os
import re
import subprocess
import sys
from json.decoder import JSONDecodeError

# imports - third party imports
import click

# imports - module imports
import bench
from bench.exceptions import PatchError, ValidationError
from bench.utils import exec_cmd, get_bench_name, get_cmd_output, log, which

logger = logging.getLogger(bench.PROJECT_NAME)


def get_env_cmd(cmd, bench_path="."):
	return os.path.abspath(os.path.join(bench_path, "env", "bin", cmd))


def get_virtualenv_path(verbose=False):
	virtualenv_path = which("virtualenv")

	if not virtualenv_path and verbose:
		log("virtualenv cannot be found", level=2)

	return virtualenv_path


def get_venv_path(verbose=False, python="python3"):
	with open(os.devnull, "wb") as devnull:
		is_venv_installed = not subprocess.call(
			[python, "-m", "venv", "--help"], stdout=devnull
		)
	if is_venv_installed:
		return f"{python} -m venv"
	else:
		log("venv cannot be found", level=2)


def update_node_packages(bench_path=".", apps=None):
	print("Updating node packages...")
	from distutils.version import LooseVersion

	from bench.utils.app import get_develop_version

	v = LooseVersion(get_develop_version("frappe", bench_path=bench_path))

	# After rollup was merged, frappe_version = 10.1
	# if develop_verion is 11 and up, only then install yarn
	if v < LooseVersion("11.x.x-develop"):
		update_npm_packages(bench_path, apps=apps)
	else:
		update_yarn_packages(bench_path, apps=apps)


def install_python_dev_dependencies(bench_path=".", apps=None, verbose=False):
	import bench.cli
	from bench.bench import Bench

	verbose = bench.cli.verbose or verbose
	quiet_flag = "" if verbose else "--quiet"

	bench = Bench(bench_path)

	if isinstance(apps, str):
		apps = [apps]
	elif not apps:
		apps = bench.get_installed_apps()

	for app in apps:
		pyproject_deps = None
		app_path = os.path.join(bench_path, "apps", app)
		pyproject_path = os.path.join(app_path, "pyproject.toml")
		dev_requirements_path = os.path.join(app_path, "dev-requirements.txt")

		if os.path.exists(pyproject_path):
			pyproject_deps = _generate_dev_deps_pattern(pyproject_path)
			if pyproject_deps:
				bench.run(f"{bench.python} -m pip install {quiet_flag} --upgrade {pyproject_deps}")

		if not pyproject_deps and os.path.exists(dev_requirements_path):
			bench.run(
				f"{bench.python} -m pip install {quiet_flag} --upgrade -r {dev_requirements_path}"
			)


def _generate_dev_deps_pattern(pyproject_path):
	try:
		from tomli import loads
	except ImportError:
		from tomllib import loads

	requirements_pattern = ""
	pyroject_config = loads(open(pyproject_path).read())

	with contextlib.suppress(KeyError):
		for pkg, version in pyroject_config["tool"]["bench"]["dev-dependencies"].items():
			op = "==" if "=" not in version else ""
			requirements_pattern += f"{pkg}{op}{version} "
	return requirements_pattern


def update_yarn_packages(bench_path=".", apps=None):
	from bench.bench import Bench

	bench = Bench(bench_path)
	apps = apps or bench.apps
	apps_dir = os.path.join(bench.name, "apps")

	# TODO: Check for stuff like this early on only??
	if not which("yarn"):
		print("Please install yarn using below command and try again.")
		print("`npm install -g yarn`")
		return

	for app in apps:
		app_path = os.path.join(apps_dir, app)
		if os.path.exists(os.path.join(app_path, "package.json")):
			click.secho(f"\nInstalling node dependencies for {app}", fg="yellow")
			bench.run("yarn install", cwd=app_path)


def update_npm_packages(bench_path=".", apps=None):
	apps_dir = os.path.join(bench_path, "apps")
	package_json = {}

	if not apps:
		apps = os.listdir(apps_dir)

	for app in apps:
		package_json_path = os.path.join(apps_dir, app, "package.json")

		if os.path.exists(package_json_path):
			with open(package_json_path) as f:
				app_package_json = json.loads(f.read())
				# package.json is usually a dict in a dict
				for key, value in app_package_json.items():
					if key not in package_json:
						package_json[key] = value
					else:
						if isinstance(value, dict):
							package_json[key].update(value)
						elif isinstance(value, list):
							package_json[key].extend(value)
						else:
							package_json[key] = value

	if package_json is {}:
		with open(os.path.join(os.path.dirname(__file__), "package.json")) as f:
			package_json = json.loads(f.read())

	with open(os.path.join(bench_path, "package.json"), "w") as f:
		f.write(json.dumps(package_json, indent=1, sort_keys=True))

	exec_cmd("npm install", cwd=bench_path)


def migrate_env(python, backup=False):
	import shutil
	from urllib.parse import urlparse

	from bench.bench import Bench

	bench = Bench(".")
	nvenv = "env"
	path = os.getcwd()
	python = which(python)
	virtualenv = which("virtualenv")
	pvenv = os.path.join(path, nvenv)

	# Clear Cache before Bench Dies.
	try:
		config = bench.conf
		rredis = urlparse(config["redis_cache"])
		redis = f"{which('redis-cli')} -p {rredis.port}"

		logger.log("Clearing Redis Cache...")
		exec_cmd(f"{redis} FLUSHALL")
		logger.log("Clearing Redis DataBase...")
		exec_cmd(f"{redis} FLUSHDB")
	except Exception:
		logger.warning("Please ensure Redis Connections are running or Daemonized.")

	# Backup venv: restore using `virtualenv --relocatable` if needed
	if backup:
		from datetime import datetime

		parch = os.path.join(path, "archived", "envs")
		os.makedirs(parch, exist_ok=True)

		source = os.path.join(path, "env")
		target = parch

		logger.log("Backing up Virtual Environment")
		stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		dest = os.path.join(path, str(stamp))

		os.rename(source, dest)
		shutil.move(dest, target)

	# Create virtualenv using specified python
	venv_creation, packages_setup = 1, 1
	try:
		logger.log(f"Setting up a New Virtual {python} Environment")
		venv_creation = exec_cmd(f"{virtualenv} --python {python} {pvenv}")

		apps = " ".join([f"-e {os.path.join('apps', app)}" for app in bench.apps])
		packages_setup = exec_cmd(f"{pvenv} -m pip install --upgrade {apps}")

		logger.log(f"Migration Successful to {python}")
	except Exception:
		if venv_creation or packages_setup:
			logger.warning("Migration Error")


def validate_upgrade(from_ver, to_ver, bench_path="."):
	if to_ver >= 6 and not which("npm") and not which("node") and not which("nodejs"):
		raise Exception("Please install nodejs and npm")


def post_upgrade(from_ver, to_ver, bench_path="."):
	from bench.bench import Bench
	from bench.config import redis
	from bench.config.nginx import make_nginx_conf
	from bench.config.supervisor import generate_supervisor_config

	conf = Bench(bench_path).conf
	print("-" * 80 + f"Your bench was upgraded to version {to_ver}")

	if conf.get("restart_supervisor_on_update"):
		redis.generate_config(bench_path=bench_path)
		generate_supervisor_config(bench_path=bench_path)
		make_nginx_conf(bench_path=bench_path)
		print(
			"As you have setup your bench for production, you will have to reload"
			" configuration for nginx and supervisor. To complete the migration, please"
			" run the following commands:\nsudo service nginx restart\nsudo"
			" supervisorctl reload"
		)


def patch_sites(bench_path="."):
	from bench.bench import Bench
	from bench.utils.system import migrate_site

	bench = Bench(bench_path)

	for site in bench.sites:
		try:
			migrate_site(site, bench_path=bench_path)
		except subprocess.CalledProcessError:
			raise PatchError


def restart_supervisor_processes(bench_path=".", web_workers=False):
	from bench.bench import Bench

	bench = Bench(bench_path)
	conf = bench.conf
	cmd = conf.get("supervisor_restart_cmd")
	bench_name = get_bench_name(bench_path)

	if cmd:
		bench.run(cmd)

	else:
		sudo = ""
		try:
			supervisor_status = get_cmd_output("supervisorctl status", cwd=bench_path)
		except Exception as e:
			if e.returncode == 127:
				log("restart failed: Couldn't find supervisorctl in PATH", level=3)
				return
			sudo = "sudo "
			supervisor_status = get_cmd_output("sudo supervisorctl status", cwd=bench_path)

		if web_workers and f"{bench_name}-web:" in supervisor_status:
			group = f"{bench_name}-web:\t"

		elif f"{bench_name}-workers:" in supervisor_status:
			group = f"{bench_name}-workers: {bench_name}-web:"

		# backward compatibility
		elif f"{bench_name}-processes:" in supervisor_status:
			group = f"{bench_name}-processes:"

		# backward compatibility
		else:
			group = "frappe:"

		bench.run(f"{sudo}supervisorctl restart {group}")


def restart_systemd_processes(bench_path=".", web_workers=False):
	bench_name = get_bench_name(bench_path)
	exec_cmd(
		f"sudo systemctl stop -- $(systemctl show -p Requires {bench_name}.target | cut"
		" -d= -f2)"
	)
	exec_cmd(
		f"sudo systemctl start -- $(systemctl show -p Requires {bench_name}.target |"
		" cut -d= -f2)"
	)


def restart_process_manager(bench_path=".", web_workers=False):
	# only overmind has the restart feature, not sure other supported procmans do
	if which("overmind") and os.path.exists(os.path.join(bench_path, ".overmind.sock")):
		worker = "web" if web_workers else ""
		exec_cmd(f"overmind restart {worker}", cwd=bench_path)


def build_assets(bench_path=".", app=None):
	command = "bench build"
	if app:
		command += f" --app {app}"
	exec_cmd(command, cwd=bench_path, env={"BENCH_DEVELOPER": "1"})


def handle_version_upgrade(version_upgrade, bench_path, force, reset, conf):
	from bench.utils import log, pause_exec

	if version_upgrade[0]:
		if force:
			log(
				"""Force flag has been used for a major version change in Frappe and it's apps.
This will take significant time to migrate and might break custom apps.""",
				level=3,
			)
		else:
			print(
				f"""This update will cause a major version change in Frappe/ERPNext from {version_upgrade[1]} to {version_upgrade[2]}.
This would take significant time to migrate and might break custom apps."""
			)
			click.confirm("Do you want to continue?", abort=True)

	if not reset and conf.get("shallow_clone"):
		log(
			"""shallow_clone is set in your bench config.
However without passing the --reset flag, your repositories will be unshallowed.
To avoid this, cancel this operation and run `bench update --reset`.

Consider the consequences of `git reset --hard` on your apps before you run that.
To avoid seeing this warning, set shallow_clone to false in your common_site_config.json
		""",
			level=3,
		)
		pause_exec(seconds=10)

	if version_upgrade[0] or (not version_upgrade[0] and force):
		validate_upgrade(version_upgrade[1], version_upgrade[2], bench_path=bench_path)


def update(
	pull: bool = False,
	apps: str = None,
	patch: bool = False,
	build: bool = False,
	requirements: bool = False,
	backup: bool = True,
	compile: bool = True,
	force: bool = False,
	reset: bool = False,
	restart_supervisor: bool = False,
	restart_systemd: bool = False,
):
	"""command: bench update"""
	import re

	from bench import patches
	from bench.app import pull_apps
	from bench.bench import Bench
	from bench.config.common_site_config import update_config
	from bench.exceptions import CannotUpdateReleaseBench
	from bench.utils import clear_command_cache
	from bench.utils.app import is_version_upgrade
	from bench.utils.system import backup_all_sites

	bench_path = os.path.abspath(".")
	bench = Bench(bench_path)
	patches.run(bench_path=bench_path)
	conf = bench.conf

	clear_command_cache(bench_path=".")

	if conf.get("release_bench"):
		raise CannotUpdateReleaseBench("Release bench detected, cannot update!")

	if not (pull or patch or build or requirements):
		pull, patch, build, requirements = True, True, True, True

	if apps and pull:
		apps = [app.strip() for app in re.split(",| ", apps) if app]
	else:
		apps = []

	validate_branch()

	version_upgrade = is_version_upgrade()
	handle_version_upgrade(version_upgrade, bench_path, force, reset, conf)

	conf.update({"maintenance_mode": 1, "pause_scheduler": 1})
	update_config(conf, bench_path=bench_path)

	if backup:
		print("Backing up sites...")
		backup_all_sites(bench_path=bench_path)

	if pull:
		print("Updating apps source...")
		pull_apps(apps=apps, bench_path=bench_path, reset=reset)

	if requirements:
		print("Setting up requirements...")
		bench.setup.requirements()

	if patch:
		print("Patching sites...")
		patch_sites(bench_path=bench_path)

	if build:
		print("Building assets...")
		bench.build()

	if version_upgrade[0] or (not version_upgrade[0] and force):
		post_upgrade(version_upgrade[1], version_upgrade[2], bench_path=bench_path)

	if pull and compile:
		from compileall import compile_dir

		print("Compiling Python files...")
		apps_dir = os.path.join(bench_path, "apps")
		compile_dir(apps_dir, quiet=1, rx=re.compile(".*node_modules.*"))

	bench.reload(web=False, supervisor=restart_supervisor, systemd=restart_systemd)

	conf.update({"maintenance_mode": 0, "pause_scheduler": 0})
	update_config(conf, bench_path=bench_path)

	print(
		"_" * 80 + "\nBench: Deployment tool for Frappe and Frappe Applications"
		" (https://frappe.io/bench).\nOpen source depends on your contributions, so do"
		" give back by submitting bug reports, patches and fixes and be a part of the"
		" community :)"
	)


def clone_apps_from(bench_path, clone_from, update_app=True):
	from bench.app import install_app

	print(f"Copying apps from {clone_from}...")
	subprocess.check_output(["cp", "-R", os.path.join(clone_from, "apps"), bench_path])

	node_modules_path = os.path.join(clone_from, "node_modules")
	if os.path.exists(node_modules_path):
		print(f"Copying node_modules from {clone_from}...")
		subprocess.check_output(["cp", "-R", node_modules_path, bench_path])

	def setup_app(app):
		# run git reset --hard in each branch, pull latest updates and install_app
		app_path = os.path.join(bench_path, "apps", app)

		# remove .egg-ino
		subprocess.check_output(["rm", "-rf", app + ".egg-info"], cwd=app_path)

		if update_app and os.path.exists(os.path.join(app_path, ".git")):
			remotes = subprocess.check_output(["git", "remote"], cwd=app_path).strip().split()
			if "upstream" in remotes:
				remote = "upstream"
			else:
				remote = remotes[0]
			print(f"Cleaning up {app}")
			branch = subprocess.check_output(
				["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=app_path
			).strip()
			subprocess.check_output(["git", "reset", "--hard"], cwd=app_path)
			subprocess.check_output(["git", "pull", "--rebase", remote, branch], cwd=app_path)

		install_app(app, bench_path, restart_bench=False)

	with open(os.path.join(clone_from, "sites", "apps.txt")) as f:
		apps = f.read().splitlines()

	for app in apps:
		setup_app(app)


def remove_backups_crontab(bench_path="."):
	from crontab import CronTab

	from bench.bench import Bench

	logger.log("removing backup cronjob")

	bench_dir = os.path.abspath(bench_path)
	user = Bench(bench_dir).conf.get("frappe_user")
	logfile = os.path.join(bench_dir, "logs", "backup.log")
	system_crontab = CronTab(user=user)
	backup_command = f"cd {bench_dir} && {sys.argv[0]} --verbose --site all backup"
	job_command = f"{backup_command} >> {logfile} 2>&1"

	system_crontab.remove_all(command=job_command)


def set_mariadb_host(host, bench_path="."):
	update_common_site_config({"db_host": host}, bench_path=bench_path)


def set_redis_cache_host(host, bench_path="."):
	update_common_site_config({"redis_cache": f"redis://{host}"}, bench_path=bench_path)


def set_redis_queue_host(host, bench_path="."):
	update_common_site_config({"redis_queue": f"redis://{host}"}, bench_path=bench_path)


def set_redis_socketio_host(host, bench_path="."):
	update_common_site_config({"redis_socketio": f"redis://{host}"}, bench_path=bench_path)


def update_common_site_config(ddict, bench_path="."):
	filename = os.path.join(bench_path, "sites", "common_site_config.json")

	if os.path.exists(filename):
		with open(filename) as f:
			content = json.load(f)

	else:
		content = {}

	content.update(ddict)
	with open(filename, "w") as f:
		json.dump(content, f, indent=1, sort_keys=True)


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
		).decode("utf-8")
	except subprocess.CalledProcessError:
		return None

	try:
		apps_sites_dict = json.loads(out)
	except JSONDecodeError:
		return None

	for site, apps in apps_sites_dict.items():
		if app in apps:
			raise ValidationError(f"Cannot remove, app is installed on site: {site}")


def check_app_installed_legacy(app, bench_path="."):
	site_path = os.path.join(bench_path, "sites")

	for site in os.listdir(site_path):
		req_file = os.path.join(site_path, site, "site_config.json")
		if os.path.exists(req_file):
			out = subprocess.check_output(
				["bench", "--site", site, "list-apps"], cwd=bench_path
			).decode("utf-8")
			if re.search(r"\b" + app + r"\b", out):
				print(f"Cannot remove, app is installed on site: {site}")
				sys.exit(1)


def validate_branch():
	from bench.bench import Bench
	from bench.utils.app import get_current_branch

	apps = Bench(".").apps

	installed_apps = set(apps)
	check_apps = {"frappe", "erpnext"}
	intersection_apps = installed_apps.intersection(check_apps)

	for app in intersection_apps:
		branch = get_current_branch(app)

		if branch == "master":
			print(
				"""'master' branch is renamed to 'version-11' since 'version-12' release.
As of January 2020, the following branches are
version		Frappe			ERPNext
11		version-11		version-11
12		version-12		version-12
13		version-13		version-13
14		develop			develop

Please switch to new branches to get future updates.
To switch to your required branch, run the following commands: bench switch-to-branch [branch-name]"""
			)

			sys.exit(1)
