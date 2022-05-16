# imports - standard imports
import os
import logging
import sys
import re

# imports - module imports
import bench
from bench.config.nginx import make_nginx_conf
from bench.config.supervisor import generate_supervisor_config, update_supervisord_config
from bench.config.systemd import generate_systemd_config
from bench.bench import Bench
from bench.utils import exec_cmd, which, get_bench_name, get_cmd_output, log
from bench.utils.system import fix_prod_setup_perms
from bench.exceptions import CommandFailedError

logger = logging.getLogger(bench.PROJECT_NAME)


def setup_production_prerequisites():
	"""Installs ansible, fail2banc, NGINX and supervisor"""
	if not which("ansible"):
		exec_cmd(f"sudo {sys.executable} -m pip install ansible")
	if not which("fail2ban-client"):
		exec_cmd("bench setup role fail2ban")
	if not which("nginx"):
		exec_cmd("bench setup role nginx")
	if not which("supervisord"):
		exec_cmd("bench setup role supervisor")


def setup_production(user, bench_path='.', yes=False):
	print("Setting Up prerequisites...")
	setup_production_prerequisites()

	conf = Bench(bench_path).conf

	if conf.get('restart_supervisor_on_update') and conf.get('restart_systemd_on_update'):
		raise Exception("You cannot use supervisor and systemd at the same time. Modify your common_site_config accordingly." )

	if conf.get('restart_systemd_on_update'):
		print("Setting Up systemd...")
		generate_systemd_config(bench_path=bench_path, user=user, yes=yes)
	else:
		print("Setting Up supervisor...")
		update_supervisord_config(user=user, yes=yes)
		generate_supervisor_config(bench_path=bench_path, user=user, yes=yes)

	print("Setting Up NGINX...")
	make_nginx_conf(bench_path=bench_path, yes=yes)
	fix_prod_setup_perms(bench_path, frappe_user=user)
	remove_default_nginx_configs()

	bench_name = get_bench_name(bench_path)
	nginx_conf = f'/etc/nginx/conf.d/{bench_name}.conf'

	print("Setting Up symlinks and reloading services...")
	if conf.get('restart_supervisor_on_update'):
		supervisor_conf_extn = "ini" if is_centos7_or_newer() else "conf"
		supervisor_conf = os.path.join(get_supervisor_confdir(), f'{bench_name}.{supervisor_conf_extn}')

		# Check if symlink exists, If not then create it.
		if not os.path.islink(supervisor_conf):
			os.symlink(os.path.abspath(os.path.join(bench_path, 'config', 'supervisor.conf')), supervisor_conf)

	if not os.path.islink(nginx_conf):
		os.symlink(os.path.abspath(os.path.join(bench_path, 'config', 'nginx.conf')), nginx_conf)

	if conf.get('restart_supervisor_on_update'):
		reload_supervisor()

	if os.environ.get('NO_SERVICE_RESTART'):
		return

	reload_nginx()


def disable_production(bench_path='.'):
	bench_name = get_bench_name(bench_path)
	conf = Bench(bench_path).conf

	# supervisorctl
	supervisor_conf_extn = "ini" if is_centos7_or_newer() else "conf"
	supervisor_conf = os.path.join(get_supervisor_confdir(), f'{bench_name}.{supervisor_conf_extn}')

	if os.path.islink(supervisor_conf):
		os.unlink(supervisor_conf)

	if conf.get('restart_supervisor_on_update'):
		reload_supervisor()

	# nginx
	nginx_conf = f'/etc/nginx/conf.d/{bench_name}.conf'

	if os.path.islink(nginx_conf):
		os.unlink(nginx_conf)

	reload_nginx()


def service(service_name, service_option):
	if os.path.basename(which('systemctl') or '') == 'systemctl' and is_running_systemd():
		status = exec_cmd(f"sudo systemctl {service_option} {service_name}", _raise=False)
		if service_option == "status":
			return status == 0
		if service_option == "reload":
			if status == 0:
				exec_cmd(f"sudo systemctl {service_option} {service_name}")
			else:
				exec_cmd(f"sudo systemctl start {service_name}")

	elif os.path.basename(which('service') or '') == 'service':
		status = exec_cmd(f"sudo service {service_name} {service_option}", _raise=False)
		if service_option == "status":
			return status == 0
		if service_option == "reload":
			if status == 0:
				exec_cmd(f"sudo service {service_name} {service_option}")
			else:
				exec_cmd(f"sudo service start {service_option}")

	else:
		# look for 'service_manager' and 'service_manager_command' in environment
		service_manager = os.environ.get("BENCH_SERVICE_MANAGER")
		if service_manager:
			service_manager_command = (
				os.environ.get("BENCH_SERVICE_MANAGER_COMMAND")
				or f"{service_manager} {service_option} {service}"
			)
			exec_cmd(service_manager_command)

		else:
			log(f"No service manager found: '{service_name} {service_option}' failed to execute", level=2)


def get_supervisor_confdir():
	possiblities = ('/etc/supervisor/conf.d', '/etc/supervisor.d/', '/etc/supervisord/conf.d', '/etc/supervisord.d')
	for possiblity in possiblities:
		if os.path.exists(possiblity):
			return possiblity


def remove_default_nginx_configs():
	default_nginx_configs = ['/etc/nginx/conf.d/default.conf', '/etc/nginx/sites-enabled/default']

	for conf_file in default_nginx_configs:
		if os.path.exists(conf_file):
			os.unlink(conf_file)


def is_centos7_or_newer():
	distro_release = '/etc/redhat-release'
	if os.path.exists(distro_release):
		with open(distro_release, 'r') as file_handle:
			try:
				result = re.search(r"(?:(\d+)\.)?(?:(\d+)\.)?(\*|\d+)", file_handle.read(), re.MULTILINE)
				return int(result.group(1)) >= 7
			except AttributeError:
				pass
	return False


def is_running_systemd():
	with open('/proc/1/comm') as f:
		comm = f.read().strip()
	if comm == "init":
		return False
	elif comm == "systemd":
		return True
	return False


def reload_supervisor():
	supervisorctl = which('supervisorctl')

	if is_centos7_or_newer():
		service_name = 'supervisord'
	else:
		service_name = 'supervisor'
	status = service(service_name, 'status')

	if status:
		try:
			# first try reread/update
			exec_cmd(f'{supervisorctl} reread', _raise=False)
			exec_cmd(f'{supervisorctl} update', _raise=False)
			return
		except CommandFailedError:
			pass

		try:
			# something is wrong, so try reloading
			exec_cmd(f'{supervisorctl} reload', _raise=False)
			return
		except CommandFailedError:
			pass

		try:
			service(service_name, 'restart')
			return
		except CommandFailedError:
			pass
	else:
		service(service_name, 'start')

def reload_nginx():
	try:
		exec_cmd(f"sudo {which('nginx')} -t")
	except Exception:
		raise

	service('nginx', 'reload')
