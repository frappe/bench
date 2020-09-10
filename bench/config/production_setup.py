# imports - standard imports
import os
import logging
import sys

# imports - module imports
import bench
from bench.config.common_site_config import get_config
from bench.config.nginx import make_nginx_conf
from bench.config.supervisor import generate_supervisor_config, update_supervisord_config
from bench.config.systemd import generate_systemd_config
from bench.utils import CommandFailedError, exec_cmd, find_executable, fix_prod_setup_perms, get_bench_name, get_cmd_output, log


logger = logging.getLogger(bench.PROJECT_NAME)


def setup_production_prerequisites():
	"""Installs ansible, fail2banc, NGINX and supervisor"""
	if not find_executable("ansible"):
		exec_cmd("sudo {0} -m pip install ansible".format(sys.executable))
	if not find_executable("fail2ban-client"):
		exec_cmd("bench setup role fail2ban")
	if not find_executable("nginx"):
		exec_cmd("bench setup role nginx")
	if not find_executable("supervisord"):
		exec_cmd("bench setup role supervisor")


def setup_production(user, bench_path='.', yes=False):
	print("Setting Up prerequisites...")
	setup_production_prerequisites()
	if get_config(bench_path).get('restart_supervisor_on_update') and get_config(bench_path).get('restart_systemd_on_update'):
		raise Exception("You cannot use supervisor and systemd at the same time. Modify your common_site_config accordingly." )

	if get_config(bench_path).get('restart_systemd_on_update'):
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
	nginx_conf = '/etc/nginx/conf.d/{bench_name}.conf'.format(bench_name=bench_name)

	print("Setting Up symlinks and reloading services...")
	if get_config(bench_path).get('restart_supervisor_on_update'):
		supervisor_conf_extn = "ini" if is_centos7() else "conf"
		supervisor_conf = os.path.join(get_supervisor_confdir(), '{bench_name}.{extn}'.format(
			bench_name=bench_name, extn=supervisor_conf_extn))

		# Check if symlink exists, If not then create it.
		if not os.path.islink(supervisor_conf):
			os.symlink(os.path.abspath(os.path.join(bench_path, 'config', 'supervisor.conf')), supervisor_conf)

	if not os.path.islink(nginx_conf):
		os.symlink(os.path.abspath(os.path.join(bench_path, 'config', 'nginx.conf')), nginx_conf)

	if get_config(bench_path).get('restart_supervisor_on_update'):
		reload_supervisor()

	if os.environ.get('NO_SERVICE_RESTART'):
		return

	reload_nginx()


def disable_production(bench_path='.'):
	bench_name = get_bench_name(bench_path)

	# supervisorctl
	supervisor_conf_extn = "ini" if is_centos7() else "conf"
	supervisor_conf = os.path.join(get_supervisor_confdir(), '{bench_name}.{extn}'.format(
		bench_name=bench_name, extn=supervisor_conf_extn))

	if os.path.islink(supervisor_conf):
		os.unlink(supervisor_conf)

	if get_config(bench_path).get('restart_supervisor_on_update'):
		reload_supervisor()

	# nginx
	nginx_conf = '/etc/nginx/conf.d/{bench_name}.conf'.format(bench_name=bench_name)

	if os.path.islink(nginx_conf):
		os.unlink(nginx_conf)

	reload_nginx()


def service(service_name, service_option):
	if os.path.basename(find_executable('systemctl') or '') == 'systemctl' and is_running_systemd():
		systemctl_cmd = "sudo {service_manager} {service_option} {service_name}"
		exec_cmd(systemctl_cmd.format(service_manager='systemctl', service_option=service_option, service_name=service_name))

	elif os.path.basename(find_executable('service') or '') == 'service':
		service_cmd = "sudo {service_manager} {service_name} {service_option}"
		exec_cmd(service_cmd.format(service_manager='service', service_name=service_name, service_option=service_option))

	else:
		# look for 'service_manager' and 'service_manager_command' in environment
		service_manager = os.environ.get("BENCH_SERVICE_MANAGER")
		if service_manager:
			service_manager_command = (os.environ.get("BENCH_SERVICE_MANAGER_COMMAND")
				or "{service_manager} {service_option} {service}").format(service_manager=service_manager, service=service, service_option=service_option)
			exec_cmd(service_manager_command)

		else:
			log("No service manager found: '{0} {1}' failed to execute".format(service_name, service_option), level=2)


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


def is_centos7():
	return os.path.exists('/etc/redhat-release') and get_cmd_output("cat /etc/redhat-release | sed 's/Linux\ //g' | cut -d' ' -f3 | cut -d. -f1").strip() == '7'


def is_running_systemd():
	with open('/proc/1/comm') as f:
		comm = f.read().strip()
	if comm == "init":
		return False
	elif comm == "systemd":
		return True
	return False


def reload_supervisor():
	supervisorctl = find_executable('supervisorctl')

	try:
		# first try reread/update
		exec_cmd('{0} reread'.format(supervisorctl))
		exec_cmd('{0} update'.format(supervisorctl))
		return
	except CommandFailedError:
		pass

	try:
		# something is wrong, so try reloading
		exec_cmd('{0} reload'.format(supervisorctl))
		return
	except CommandFailedError:
		pass

	try:
		# then try restart for centos
		service('supervisord', 'restart')
		return
	except CommandFailedError:
		pass

	try:
		# else try restart for ubuntu / debian
		service('supervisor', 'restart')
		return
	except CommandFailedError:
		pass

def reload_nginx():
	try:
		exec_cmd('sudo {0} -t'.format(find_executable('nginx')))
	except:
		raise

	service('nginx', 'reload')
