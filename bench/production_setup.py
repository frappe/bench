from .utils import get_program, exec_cmd, get_cmd_output
from .config import generate_nginx_config, generate_supervisor_config
import os

def restart_service(service):
	program = get_program(['systemctl', 'service'])
	if not program:
		raise Exception, 'No service manager found'
	elif program == 'systemctl':
		exec_cmd("{prog} restart {service}".format(prog=program, service=service))
	elif program == 'service':
		exec_cmd("{prog} {service} restart ".format(prog=program, service=service))

def get_supervisor_confdir():
	possiblities = ('/etc/supervisor/conf.d', '/etc/supervisor.d/', '/etc/supervisord/conf.d', '/etc/supervisord.d')
	for possiblity in possiblities:
		if os.path.exists(possiblity):
			return possiblity

def remove_default_nginx_configs():
	default_nginx_configs = ['/etc/nginx/conf.d/default.conf', '/etc/nginx/sites-available/default.conf']

	for conf_file in default_nginx_configs:
		if os.path.exists(conf_file):
			os.unlink(conf_file)

def setup_production(bench='.'):
	generate_supervisor_config(bench=bench)
	generate_nginx_config(bench=bench)
	remove_default_nginx_configs()

	if os.path.exists('/etc/redhat-release') and get_cmd_output("cat /etc/redhat-release | sed 's/Linux\ //g' | cut -d" " -f3 | cut -d. -f1") == '7':
		supervisor_conf_filename = 'frappe.ini'
	else:
		supervisor_conf_filename = 'frappe.conf'

	os.symlink(os.path.abspath(os.path.join(bench, 'config', 'supervisor.conf')), os.path.join(get_supervisor_confdir(), supervisor_conf_filename))
	os.symlink(os.path.abspath(os.path.join(bench, 'config', 'nginx.conf')), '/etc/nginx/conf.d/frappe.conf')
	exec_cmd('supervisorctl reload')
	restart_service('nginx')
