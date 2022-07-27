# imports - standard imports
import grp
import os
import pwd
import shutil
import sys

# imports - module imports
import bench
from bench.utils import (
	exec_cmd,
	get_process_manager,
	log,
	run_frappe_cmd,
	sudoers_file,
	which,
	is_valid_frappe_branch,
)
from bench.utils.bench import build_assets, clone_apps_from
from bench.utils.render import job


@job(title="Initializing Bench {path}", success="Bench {path} initialized")
def init(
	path,
	apps_path=None,
	no_procfile=False,
	no_backups=False,
	frappe_path=None,
	frappe_branch=None,
	verbose=False,
	clone_from=None,
	skip_redis_config_generation=False,
	clone_without_update=False,
	skip_assets=False,
	python="python3",
	install_app=None,
):
	"""Initialize a new bench directory

	* create a bench directory in the given path
	* setup logging for the bench
	* setup env for the bench
	* setup config (dir/pids/redis/procfile) for the bench
	* setup patches.txt for bench
	* clone & install frappe
	        * install python & node dependencies
	        * build assets
	* setup backups crontab
	"""

	# Use print("\033c", end="") to clear entire screen after each step and re-render each list
	# another way => https://stackoverflow.com/a/44591228/10309266

	import bench.cli
	from bench.app import get_app, install_apps_from_path
	from bench.bench import Bench

	verbose = bench.cli.verbose or verbose

	bench = Bench(path)

	bench.setup.dirs()
	bench.setup.logging()
	bench.setup.env(python=python)
	bench.setup.config(redis=not skip_redis_config_generation, procfile=not no_procfile)
	bench.setup.patches()

	# local apps
	if clone_from:
		clone_apps_from(
			bench_path=path, clone_from=clone_from, update_app=not clone_without_update
		)

	# remote apps
	else:
		frappe_path = frappe_path or "https://github.com/frappe/frappe.git"
		is_valid_frappe_branch(frappe_path=frappe_path, frappe_branch=frappe_branch)
		get_app(
			frappe_path,
			branch=frappe_branch,
			bench_path=path,
			skip_assets=True,
			verbose=verbose,
			resolve_deps=False,
		)

		# fetch remote apps using config file - deprecate this!
		if apps_path:
			install_apps_from_path(apps_path, bench_path=path)

	# getting app on bench init using --install-app
	if install_app:
		get_app(
			install_app,
			branch=frappe_branch,
			bench_path=path,
			skip_assets=True,
			verbose=verbose,
			resolve_deps=False,
		)

	if not skip_assets:
		build_assets(bench_path=path)

	if not no_backups:
		bench.setup.backups()


def setup_sudoers(user):
	from bench.config.lets_encrypt import get_certbot_path

	if not os.path.exists("/etc/sudoers.d"):
		os.makedirs("/etc/sudoers.d")

		set_permissions = not os.path.exists("/etc/sudoers")
		with open("/etc/sudoers", "a") as f:
			f.write("\n#includedir /etc/sudoers.d\n")

		if set_permissions:
			os.chmod("/etc/sudoers", 0o440)

	template = bench.config.env().get_template("frappe_sudoers")
	frappe_sudoers = template.render(
		**{
			"user": user,
			"service": which("service"),
			"systemctl": which("systemctl"),
			"nginx": which("nginx"),
			"certbot": get_certbot_path(),
		}
	)

	with open(sudoers_file, "w") as f:
		f.write(frappe_sudoers)

	os.chmod(sudoers_file, 0o440)
	log(f"Sudoers was set up for user {user}", level=1)


def start(no_dev=False, concurrency=None, procfile=None, no_prefix=False, procman=None):
	program = which(procman) if procman else get_process_manager()
	if not program:
		raise Exception("No process manager found")

	os.environ["PYTHONUNBUFFERED"] = "true"
	if not no_dev:
		os.environ["DEV_SERVER"] = "true"

	command = [program, "start"]
	if concurrency:
		command.extend(["-c", concurrency])

	if procfile:
		command.extend(["-f", procfile])

	if no_prefix:
		command.extend(["--no-prefix"])

	os.execv(program, command)


def migrate_site(site, bench_path="."):
	run_frappe_cmd("--site", site, "migrate", bench_path=bench_path)


def backup_site(site, bench_path="."):
	run_frappe_cmd("--site", site, "backup", bench_path=bench_path)


def backup_all_sites(bench_path="."):
	from bench.bench import Bench

	for site in Bench(bench_path).sites:
		backup_site(site, bench_path=bench_path)


def fix_prod_setup_perms(bench_path=".", frappe_user=None):
	from glob import glob
	from bench.bench import Bench

	frappe_user = frappe_user or Bench(bench_path).conf.get("frappe_user")

	if not frappe_user:
		print("frappe user not set")
		sys.exit(1)

	globs = ["logs/*", "config/*"]
	for glob_name in globs:
		for path in glob(glob_name):
			uid = pwd.getpwnam(frappe_user).pw_uid
			gid = grp.getgrnam(frappe_user).gr_gid
			os.chown(path, uid, gid)


def setup_fonts():
	fonts_path = os.path.join("/tmp", "fonts")

	if os.path.exists("/etc/fonts_backup"):
		return

	exec_cmd("git clone https://github.com/frappe/fonts.git", cwd="/tmp")
	os.rename("/etc/fonts", "/etc/fonts_backup")
	os.rename("/usr/share/fonts", "/usr/share/fonts_backup")
	os.rename(os.path.join(fonts_path, "etc_fonts"), "/etc/fonts")
	os.rename(os.path.join(fonts_path, "usr_share_fonts"), "/usr/share/fonts")
	shutil.rmtree(fonts_path)
	exec_cmd("fc-cache -fv")
