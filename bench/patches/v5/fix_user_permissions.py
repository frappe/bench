# imports - standard imports
import getpass
import os
import subprocess

# imports - module imports
from bench.cli import change_uid_msg
from bench.config.production_setup import get_supervisor_confdir, is_centos7
from bench.config.common_site_config import get_config
from bench.utils import exec_cmd, get_bench_name, get_cmd_output


def is_sudoers_set():
	cmd = ["sudo", "-n", "bench"]
	return (not subprocess.call(cmd)) or (change_uid_msg in get_cmd_output(cmd, _raise=False))


def is_production_set(bench_path):
	production_setup = False
	bench_name = get_bench_name(bench_path)

	supervisor_conf_extn = "ini" if is_centos7() else "conf"
	supervisor_conf_file_name = '{bench_name}.{extn}'.format(bench_name=bench_name, extn=supervisor_conf_extn)
	supervisor_conf = os.path.join(get_supervisor_confdir(), supervisor_conf_file_name)

	if os.path.exists(supervisor_conf):
		production_setup = production_setup or True

	nginx_conf = '/etc/nginx/conf.d/{bench_name}.conf'.format(bench_name=bench_name)

	if os.path.exists(nginx_conf):
		production_setup = production_setup or True

	return production_setup


def execute(bench_path):
	user = get_config('.').get("frappe_user") or getpass.getuser()

	if is_sudoers_set():
		exec_cmd("sudo bench setup sudoers {user}".format(user=user))

		if is_production_set(bench_path):
			exec_cmd("sudo bench setup supervisor --yes --user {user}".format(user=user))
