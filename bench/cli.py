# imports - standard imports
import atexit
from contextlib import contextmanager
import json
from logging import Logger
import os
import pwd
import sys

# imports - third party imports
import click

# imports - module imports
import bench
from bench.bench import Bench
from bench.commands import bench_command
from bench.config.common_site_config import get_config
from bench.utils import (
	bench_cache_file,
	check_latest_version,
	drop_privileges,
	find_parent_bench,
	generate_command_cache,
	get_cmd_output,
	is_bench_directory,
	is_dist_editable,
	is_root,
	log,
	setup_logging,
	get_cmd_from_sysargv,
)
from bench.utils.bench import get_env_cmd

# these variables are used to show dynamic outputs on the terminal
dynamic_feed = False
verbose = False
is_envvar_warn_set = None
from_command_line = False  # set when commands are executed via the CLI
bench.LOG_BUFFER = []

change_uid_msg = "You should not run this command as root"
src = os.path.dirname(__file__)


@contextmanager
def execute_cmd(check_for_update=True, command: str = None, logger: Logger = None):
	if check_for_update:
		atexit.register(check_latest_version)

	try:
		yield
	except BaseException as e:
		return_code = getattr(e, "code", 1)

		if isinstance(e, Exception):
			click.secho(f"ERROR: {e}", fg="red")

		if return_code:
			logger.warning(f"{command} executed with exit code {return_code}")

		raise e


def cli():
	global from_command_line, bench_config, is_envvar_warn_set, verbose

	from_command_line = True
	command = " ".join(sys.argv)
	argv = set(sys.argv)
	is_envvar_warn_set = not (os.environ.get("BENCH_DEVELOPER") or os.environ.get("CI"))
	is_cli_command = len(sys.argv) > 1 and not argv.intersection({"src", "--version"})
	cmd_from_sys = get_cmd_from_sysargv()

	if "--verbose" in argv:
		verbose = True

	change_working_directory()
	logger = setup_logging()
	logger.info(command)
	setup_clear_cache()

	bench_config = get_config(".")

	if is_cli_command:
		check_uid()
		change_uid()
		change_dir()

	if (
		is_envvar_warn_set
		and is_cli_command
		and not bench_config.get("developer_mode")
		and is_dist_editable(bench.PROJECT_NAME)
	):
		log(
			"bench is installed in editable mode!\n\nThis is not the recommended mode"
			" of installation for production. Instead, install the package from PyPI"
			" with: `pip install frappe-bench`\n",
			level=3,
		)

	in_bench = is_bench_directory()

	if (
		not in_bench
		and len(sys.argv) > 1
		and not argv.intersection(
			{"init", "find", "src", "drop", "get", "get-app", "--version"}
		)
		and not cmd_requires_root()
	):
		log("Command not being executed in bench directory", level=3)

	if len(sys.argv) == 1 or sys.argv[1] == "--help":
		print(click.Context(bench_command).get_help())
		if in_bench:
			print(get_frappe_help())
		return

	_opts = [x.opts + x.secondary_opts for x in bench_command.params]
	opts = {item for sublist in _opts for item in sublist}

	# handle usages like `--use-feature='feat-x'` and `--use-feature 'feat-x'`
	if cmd_from_sys and cmd_from_sys.split("=", 1)[0].strip() in opts:
		bench_command()

	if cmd_from_sys in bench_command.commands:
		with execute_cmd(check_for_update=not is_cli_command, command=command, logger=logger):
			bench_command()

	if in_bench:
		if cmd_from_sys in get_frappe_commands():
			frappe_cmd()
		else:
			app_cmd()

	bench_command()


def check_uid():
	if cmd_requires_root() and not is_root():
		log("superuser privileges required for this command", level=3)
		sys.exit(1)


def cmd_requires_root():
	if len(sys.argv) > 2 and sys.argv[2] in (
		"production",
		"sudoers",
		"lets-encrypt",
		"fonts",
		"print",
		"firewall",
		"ssh-port",
		"role",
		"fail2ban",
		"wildcard-ssl",
	):
		return True
	if len(sys.argv) >= 2 and sys.argv[1] in (
		"patch",
		"renew-lets-encrypt",
		"disable-production",
	):
		return True
	if len(sys.argv) > 2 and sys.argv[1] in ("install"):
		return True


def change_dir():
	if os.path.exists("config.json") or "init" in sys.argv:
		return
	dir_path_file = "/etc/frappe_bench_dir"
	if os.path.exists(dir_path_file):
		with open(dir_path_file) as f:
			dir_path = f.read().strip()
		if os.path.exists(dir_path):
			os.chdir(dir_path)


def change_uid():
	if is_root() and not cmd_requires_root():
		frappe_user = bench_config.get("frappe_user")
		if frappe_user:
			drop_privileges(uid_name=frappe_user, gid_name=frappe_user)
			os.environ["HOME"] = pwd.getpwnam(frappe_user).pw_dir
		else:
			log(change_uid_msg, level=3)
			sys.exit(1)


def app_cmd(bench_path="."):
	f = get_env_cmd("python", bench_path=bench_path)
	os.chdir(os.path.join(bench_path, "sites"))
	os.execv(f, [f] + ["-m", "frappe.utils.bench_helper"] + sys.argv[1:])


def frappe_cmd(bench_path="."):
	f = get_env_cmd("python", bench_path=bench_path)
	os.chdir(os.path.join(bench_path, "sites"))
	os.execv(f, [f] + ["-m", "frappe.utils.bench_helper", "frappe"] + sys.argv[1:])


def get_cached_frappe_commands():
	if os.path.exists(bench_cache_file):
		command_dump = open(bench_cache_file).read() or "[]"
		return set(json.loads(command_dump))
	return set()


def get_frappe_commands():
	if not is_bench_directory():
		return set()

	return set(generate_command_cache())


def get_frappe_help(bench_path="."):
	python = get_env_cmd("python", bench_path=bench_path)
	sites_path = os.path.join(bench_path, "sites")
	try:
		out = get_cmd_output(
			f"{python} -m frappe.utils.bench_helper get-frappe-help", cwd=sites_path
		)
		return "\n\nFramework commands:\n" + out.split("Commands:")[1]
	except Exception:
		return ""


def change_working_directory():
	"""Allows bench commands to be run from anywhere inside a bench directory"""
	cur_dir = os.path.abspath(".")
	bench_path = find_parent_bench(cur_dir)
	bench.current_path = os.getcwd()
	bench.updated_path = bench_path

	if bench_path:
		os.chdir(bench_path)


def setup_clear_cache():
	from copy import copy

	f = copy(os.chdir)

	def _chdir(*args, **kwargs):
		Bench.cache_clear()
		return f(*args, **kwargs)

	os.chdir = _chdir
