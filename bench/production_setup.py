from .utils import get_program, exec_cmd, get_cmd_output, fix_prod_setup_perms
from .config import generate_nginx_config, generate_supervisor_config
from jinja2 import Environment, PackageLoader
import os
import shutil

def restart_service(service):
	if os.path.basename(get_program(['systemctl']) or '') == 'systemctl' and is_running_systemd():
		exec_cmd("{prog} restart {service}".format(prog='systemctl', service=service))
	elif os.path.basename(get_program(['service']) or '') == 'service':
		exec_cmd("{prog} {service} restart ".format(prog='service', service=service))
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

def copy_default_nginx_config():
	shutil.copy(os.path.join(os.path.dirname(__file__), 'templates', 'nginx_default.conf'), '/etc/nginx/nginx.conf')

def setup_production(user, bench='.'):
	generate_supervisor_config(bench=bench, user=user)
	generate_nginx_config(bench=bench)
	fix_prod_setup_perms(frappe_user=user)
	remove_default_nginx_configs()

	if is_centos7():
		supervisor_conf_filename = 'frappe.ini'
		copy_default_nginx_config()
	else:
		supervisor_conf_filename = 'frappe.conf'

	os.symlink(os.path.abspath(os.path.join(bench, 'config', 'supervisor.conf')), os.path.join(get_supervisor_confdir(), supervisor_conf_filename))
	os.symlink(os.path.abspath(os.path.join(bench, 'config', 'nginx.conf')), '/etc/nginx/conf.d/frappe.conf')
	exec_cmd('supervisorctl reload')
	restart_service('nginx')
