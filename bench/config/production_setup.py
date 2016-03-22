from bench.utils import get_program, exec_cmd, get_cmd_output, fix_prod_setup_perms, get_bench_name
from bench.config.supervisor import generate_supervisor_config
from bench.config.nginx import make_nginx_conf
import os

def setup_production(user, bench='.'):
	generate_supervisor_config(bench_path=bench, user=user)
	make_nginx_conf(bench_path=bench)
	fix_prod_setup_perms(bench, frappe_user=user)
	remove_default_nginx_configs()

	bench_name = get_bench_name(bench)
	nginx_conf = '/etc/nginx/conf.d/{bench_name}.conf'.format(bench_name=bench_name)

	supervisor_conf_extn = "ini" if is_centos7() else "conf"
	supervisor_conf = os.path.join(get_supervisor_confdir(), '{bench_name}.{extn}'.format(
		bench_name=bench_name, extn=supervisor_conf_extn))


	os.symlink(os.path.abspath(os.path.join(bench, 'config', 'supervisor.conf')), supervisor_conf)
	os.symlink(os.path.abspath(os.path.join(bench, 'config', 'nginx.conf')), nginx_conf)

	exec_cmd('supervisorctl reload')
	if os.environ.get('NO_SERVICE_RESTART'):
		return

	restart_service('nginx')


def restart_service(service):
	if os.path.basename(get_program(['systemctl']) or '') == 'systemctl' and is_running_systemd():
		exec_cmd("{service_manager} restart {service}".format(service_manager='systemctl', service=service))
	elif os.path.basename(get_program(['service']) or '') == 'service':
		exec_cmd("{service_manager} {service} restart ".format(service_manager='service', service=service))
	else:
		# look for 'service_manager' and 'service_manager_command' in environment
		service_manager = os.environ.get("BENCH_SERVICE_MANAGER")
		if service_manager:
			service_manager_command = (os.environ.get("BENCH_SERVICE_MANAGER_COMMAND")
				or "{service_manager} restart {service}").format(service_manager=service_manager, service=service)
			exec_cmd(service_manager_command)

		else:
			raise Exception, 'No service manager found'

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
