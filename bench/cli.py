# imports - standard imports
import atexit
import json
import logging
import os
import pwd
import sys

# imports - third party imports
import click

# imports - module imports
import bench
from bench.app import get_apps
from bench.commands import bench_command
from bench.config.common_site_config import get_config
from bench.utils import PatchError, bench_cache_file, check_latest_version, drop_privileges, find_parent_bench, generate_command_cache, get_cmd_output, get_env_cmd, get_frappe, is_bench_directory, is_dist_editable, is_root, log, setup_logging

from_command_line = False
change_uid_msg = "You should not run this command as root"
src = os.path.dirname(__file__)


def cli():
	global from_command_line
	from_command_line = True
	command = " ".join(sys.argv)

	change_working_directory()
	logger = setup_logging() or logging.getLogger(bench.PROJECT_NAME)
	logger.info(command)
	check_uid()
	change_dir()
	change_uid()

	if is_dist_editable(bench.PROJECT_NAME) and len(sys.argv) > 1 and sys.argv[1] != "src" and not get_config(".").get("developer_mode"):
		log("bench is installed in editable mode!\n\nThis is not the recommended mode of installation for production. Instead, install the package from PyPI with: `pip install frappe-bench`\n", level=3)

	if not is_bench_directory() and not cmd_requires_root() and len(sys.argv) > 1 and sys.argv[1] not in ("init", "find", "src"):
		log("Command not being executed in bench directory", level=3)

	if len(sys.argv) > 2 and sys.argv[1] == "frappe":
		return old_frappe_cli()

	elif len(sys.argv) > 1:
		if sys.argv[1] in get_frappe_commands() + ["--site", "--verbose", "--force", "--profile"]:
			return frappe_cmd()

		elif sys.argv[1] == "--help":
			print(click.Context(bench_command).get_help())
			print(get_frappe_help())
			return

		elif sys.argv[1] in get_apps():
			return app_cmd()

	if not (len(sys.argv) > 1 and sys.argv[1] == "src"):
		atexit.register(check_latest_version)

	try:
		bench_command()
	except BaseException as e:
		return_code = getattr(e, "code", 0)
		if return_code:
			logger.warning("{0} executed with exit code {1}".format(command, return_code))
		sys.exit(return_code)


def check_uid():
	if cmd_requires_root() and not is_root():
		log('superuser privileges required for this command', level=3)
		sys.exit(1)


def cmd_requires_root():
	if len(sys.argv) > 2 and sys.argv[2] in ('production', 'sudoers', 'lets-encrypt', 'fonts',
		'print', 'firewall', 'ssh-port', 'role', 'fail2ban', 'wildcard-ssl'):
		return True
	if len(sys.argv) >= 2 and sys.argv[1] in ('patch', 'renew-lets-encrypt', 'disable-production'):
		return True
	if len(sys.argv) > 2 and sys.argv[1] in ('install'):
		return True


def change_dir():
	if os.path.exists('config.json') or "init" in sys.argv:
		return
	dir_path_file = '/etc/frappe_bench_dir'
	if os.path.exists(dir_path_file):
		with open(dir_path_file) as f:
			dir_path = f.read().strip()
		if os.path.exists(dir_path):
			os.chdir(dir_path)


def change_uid():
	if is_root() and not cmd_requires_root():
		frappe_user = get_config(".").get('frappe_user')
		if frappe_user:
			drop_privileges(uid_name=frappe_user, gid_name=frappe_user)
			os.environ['HOME'] = pwd.getpwnam(frappe_user).pw_dir
		else:
			log(change_uid_msg, level=3)
			sys.exit(1)


def old_frappe_cli(bench_path='.'):
	f = get_frappe(bench_path=bench_path)
	os.chdir(os.path.join(bench_path, 'sites'))
	os.execv(f, [f] + sys.argv[2:])


def app_cmd(bench_path='.'):
	f = get_env_cmd('python', bench_path=bench_path)
	os.chdir(os.path.join(bench_path, 'sites'))
	os.execv(f, [f] + ['-m', 'frappe.utils.bench_helper'] + sys.argv[1:])


def frappe_cmd(bench_path='.'):
	f = get_env_cmd('python', bench_path=bench_path)
	os.chdir(os.path.join(bench_path, 'sites'))
	os.execv(f, [f] + ['-m', 'frappe.utils.bench_helper', 'frappe'] + sys.argv[1:])


def get_frappe_commands():
	if not is_bench_directory():
		return []

	if os.path.exists(bench_cache_file):
		command_dump = open(bench_cache_file, 'r').read() or '[]'
		return json.loads(command_dump)

	else:
		return generate_command_cache()


def get_frappe_help(bench_path='.'):
	python = get_env_cmd('python', bench_path=bench_path)
	sites_path = os.path.join(bench_path, 'sites')
	try:
		out = get_cmd_output("{python} -m frappe.utils.bench_helper get-frappe-help".format(python=python), cwd=sites_path)
		return "\n\nFramework commands:\n" + out.split('Commands:')[1]
	except:
		return ""


def change_working_directory():
	"""Allows bench commands to be run from anywhere inside a bench directory"""
	cur_dir = os.path.abspath(".")
	bench_path = find_parent_bench(cur_dir)

	if bench_path:
		os.chdir(bench_path)
