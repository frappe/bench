# imports - standard imports
import getpass
import os
import subprocess

# imports - module imports
from bench.cli import change_uid_msg
from bench.config.production_setup import get_supervisor_confdir, is_centos7, service
from bench.config.common_site_config import get_config
from bench.utils import exec_cmd, get_bench_name, get_cmd_output


def is_sudoers_set():
	"""Check if bench sudoers is set"""
	cmd = ["sudo", "-n", "bench"]

	with open(os.devnull, "wb") as f:
		return_code_check = not subprocess.call(cmd, stdout=f)

	if return_code_check:
		try:
			bench_warn = change_uid_msg in get_cmd_output(cmd, _raise=False)
		except subprocess.CalledProcessError:
			bench_warn = False
		finally:
			return_code_check = return_code_check and bench_warn

	return return_code_check


def is_production_set(bench_path):
	"""Check if production is set for current bench"""
	production_setup = False
	bench_name = get_bench_name(bench_path)

	supervisor_conf_extn = "ini" if is_centos7() else "conf"
	supervisor_conf_file_name = f"{bench_name}.{supervisor_conf_extn}"
	supervisor_conf = os.path.join(get_supervisor_confdir(), supervisor_conf_file_name)

	if os.path.exists(supervisor_conf):
		production_setup = production_setup or True

	nginx_conf = f"/etc/nginx/conf.d/{bench_name}.conf"

	if os.path.exists(nginx_conf):
		production_setup = production_setup or True

	return production_setup


def execute(bench_path):
	"""This patch checks if bench sudoers is set and regenerate supervisor and sudoers files"""
	user = get_config(".").get("frappe_user") or getpass.getuser()

	if is_sudoers_set():
		if is_production_set(bench_path):
			exec_cmd(f"sudo bench setup supervisor --yes --user {user}")
			service("supervisord", "restart")

		exec_cmd(f"sudo bench setup sudoers {user}")
