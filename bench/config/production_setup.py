from bench.utils import get_program, exec_cmd, get_cmd_output, fix_prod_setup_perms, get_bench_name, find_executable, CommandFailedError
from bench.config.supervisor import generate_supervisor_config
from bench.config.systemd import generate_systemd_config
from bench.config.nginx import make_nginx_conf
from bench.config.common_site_config import get_config
import os, subprocess

def setup_production(user, bench_path='.', yes=False):
	if get_config(bench_path).get('restart_supervisor_on_update') and get_config(bench_path).get('restart_systemd_on_update'):
		raise Exception("You cannot use supervisor and systemd at the same time. Modify your common_site_config accordingly." )

	if get_config(bench_path).get('restart_systemd_on_update'):
		generate_systemd_config(bench_path=bench_path, user=user, yes=yes)
	else:
		generate_supervisor_config(bench_path=bench_path, user=user, yes=yes)
	make_nginx_conf(bench_path=bench_path, yes=yes)
	fix_prod_setup_perms(bench_path, frappe_user=user)
	remove_default_nginx_configs()

	bench_name = get_bench_name(bench_path)
	nginx_conf = '/etc/nginx/conf.d/{bench_name}.conf'.format(bench_name=bench_name)

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

def service(service, option):
	if os.path.basename(get_program(['systemctl']) or '') == 'systemctl' and is_running_systemd():
		exec_cmd("sudo {service_manager} {option} {service}".format(service_manager='systemctl', option=option, service=service))
	elif os.path.basename(get_program(['service']) or '') == 'service':
		exec_cmd("sudo {service_manager} {service} {option} ".format(service_manager='service', service=service, option=option))
	else:
		# look for 'service_manager' and 'service_manager_command' in environment
		service_manager = os.environ.get("BENCH_SERVICE_MANAGER")
		if service_manager:
			service_manager_command = (os.environ.get("BENCH_SERVICE_MANAGER_COMMAND")
				or "{service_manager} {option} {service}").format(service_manager=service_manager, service=service, option=option)
			exec_cmd(service_manager_command)

		else:
			raise Exception('No service manager found')

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
		exec_cmd('sudo {0} reread'.format(supervisorctl))
		exec_cmd('sudo {0} update'.format(supervisorctl))
		return
	except CommandFailedError:
		pass

	try:
		# something is wrong, so try reloading
		exec_cmd('sudo {0} reload'.format(supervisorctl))
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
		subprocess.check_output(['sudo', find_executable('nginx'), '-t'])
	except:
		raise

	service('nginx', 'reload')
