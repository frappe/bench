from bench.utils import exec_cmd
import click, sys, json
import os

@click.group()
def setup():
	"Setup bench"
	pass

@click.command('sudoers')
@click.argument('user')
def setup_sudoers(user):
	"Add commands to sudoers list for execution without password"
	from bench.utils import setup_sudoers
	setup_sudoers(user)

@click.command('nginx')
@click.option('--yes', help='Yes to regeneration of nginx config file', default=False, is_flag=True)
def setup_nginx(yes=False):
	"generate config for nginx"
	from bench.config.nginx import make_nginx_conf
	make_nginx_conf(bench_path=".", yes=yes)

@click.command('reload-nginx')
def reload_nginx():
	from bench.config.production_setup import reload_nginx
	reload_nginx()

@click.command('supervisor')
@click.option('--user')
@click.option('--yes', help='Yes to regeneration of supervisor config', is_flag=True, default=False)
def setup_supervisor(user=None, yes=False):
	"generate config for supervisor with an optional user argument"
	from bench.config.supervisor import generate_supervisor_config
	generate_supervisor_config(bench_path=".", user=user, yes=yes)

@click.command('redis')
def setup_redis():
	"generate config for redis cache"
	from bench.config.redis import generate_config
	generate_config('.')


@click.command('fonts')
def setup_fonts():
	"Add frappe fonts to system"
	from bench.utils import setup_fonts
	setup_fonts()

@click.command('production')
@click.argument('user')
@click.option('--yes', help='Yes to regeneration config', is_flag=True, default=False)
def setup_production(user, yes=False):
	"setup bench for production"
	from bench.config.production_setup import setup_production
	from bench.utils import run_playbook
	# Install prereqs for production
	from distutils.spawn import find_executable
	if not find_executable('ansible'):
		exec_cmd("sudo pip install ansible")
	if not find_executable('fail2ban-client'):
		exec_cmd("bench setup role fail2ban")
	if not find_executable('nginx'):
		exec_cmd("bench setup role nginx")
	if not find_executable('supervisord'):
		exec_cmd("bench setup role supervisor")
	setup_production(user=user, yes=yes)


@click.command('auto-update')
def setup_auto_update():
	"Add cronjob for bench auto update"
	from bench.utils import setup_auto_update
	setup_auto_update()


@click.command('backups')
def setup_backups():
	"Add cronjob for bench backups"
	from bench.utils import setup_backups
	setup_backups()

@click.command('env')
@click.option('--python', type = str, default = 'python3', help = 'Path to Python Executable.')
def setup_env(python='python3'):
	"Setup virtualenv for bench"
	from bench.utils import setup_env
	setup_env(python=python)

@click.command('firewall')
@click.option('--ssh_port')
@click.option('--force')
def setup_firewall(ssh_port=None, force=False):
	"Setup firewall"
	from bench.utils import run_playbook

	if not force:
		click.confirm('Setting up the firewall will block all ports except 80, 443 and 22\n'
			'Do you want to continue?',
			abort=True)

	if not ssh_port:
		ssh_port = 22

	run_playbook('roles/bench/tasks/setup_firewall.yml', {"ssh_port": ssh_port})

@click.command('ssh-port')
@click.argument('port')
@click.option('--force')
def set_ssh_port(port, force=False):
	"Set SSH Port"
	from bench.utils import run_playbook

	if not force:
		click.confirm('This will change your SSH Port to {}\n'
			'Do you want to continue?'.format(port),
			abort=True)

	run_playbook('roles/bench/tasks/change_ssh_port.yml', {"ssh_port": port})

@click.command('lets-encrypt')
@click.argument('site')
@click.option('--custom-domain')
@click.option('-n', '--non-interactive', default=False, is_flag=True, help="Run certbot non-interactively. Shouldn't be used on 1'st attempt")
def setup_letsencrypt(site, custom_domain, non_interactive):
	"Setup lets-encrypt for site"
	from bench.config.lets_encrypt import setup_letsencrypt
	setup_letsencrypt(site, custom_domain, bench_path='.', interactive=not non_interactive)


@click.command('wildcard-ssl')
@click.argument('domain')
@click.option('--email')
@click.option('--exclude-base-domain', default=False, is_flag=True, help="SSL Certificate not applicable for base domain")
def setup_wildcard_ssl(domain, email, exclude_base_domain):
	''' Setup wildcard ssl certificate '''
	from bench.config.lets_encrypt import setup_wildcard_ssl
	setup_wildcard_ssl(domain, email, bench_path='.', exclude_base_domain=exclude_base_domain)


@click.command('procfile')
def setup_procfile():
	"Setup Procfile for bench start"
	from bench.config.procfile import setup_procfile
	setup_procfile('.')


@click.command('socketio')
def setup_socketio():
	"Setup node deps for socketio server"
	from bench.utils import setup_socketio
	setup_socketio()

@click.command('requirements', help="Update Python and Node packages")
@click.option('--node', help="Update only Node packages", default=False, is_flag=True)
@click.option('--python', help="Update only Python packages", default=False, is_flag=True)
def setup_requirements(node=False, python=False):
	"Setup python and node requirements"

	if not node:
		setup_python_requirements()
	if not python:
		setup_node_requirements()

def setup_python_requirements():
	from bench.utils import update_requirements
	update_requirements()

def setup_node_requirements():
	from bench.utils import update_node_packages
	update_node_packages()


@click.command('manager')
@click.option('--yes', help='Yes to regeneration of nginx config file', default=False, is_flag=True)
@click.option('--port', help='Port on which you want to run bench manager', default=23624)
@click.option('--domain', help='Domain on which you want to run bench manager')
def setup_manager(yes=False, port=23624, domain=None):
	"Setup bench-manager.local site with the bench_manager app installed on it"
	from six.moves import input
	create_new_site = True
	if 'bench-manager.local' in os.listdir('sites'):
		ans = input('Site already exists. Overwrite existing site? [Y/n]: ').lower()
		while ans not in ('y', 'n', ''):
			ans = input(
				'Please enter "y" or "n". Site already exists. Overwrite existing site? [Y/n]: ').lower()
		if ans == 'n':
			create_new_site = False
	if create_new_site:
		exec_cmd("bench new-site --force bench-manager.local")

	if 'bench_manager' in os.listdir('apps'):
		print('App already exists. Skipping app download.')
	else:
		exec_cmd("bench get-app bench_manager")

	exec_cmd("bench --site bench-manager.local install-app bench_manager")

	from bench.config.common_site_config import get_config
	bench_path = '.'
	conf = get_config(bench_path)
	if conf.get('restart_supervisor_on_update') or conf.get('restart_systemd_on_update'):
		# implicates a production setup or so I presume
		if not domain:
			print("Please specify the site name on which you want to host bench-manager using the 'domain' flag")
			sys.exit(1)

		from bench.utils import get_sites, get_bench_name
		bench_name = get_bench_name(bench_path)

		if domain not in get_sites(bench_path):
			raise Exception("No such site")

		from bench.config.nginx import make_bench_manager_nginx_conf
		make_bench_manager_nginx_conf(bench_path, yes=yes, port=port, domain=domain)


@click.command('config')
def setup_config():
	"overwrite or make config.json"
	from bench.config.common_site_config import make_config
	make_config('.')


@click.command('add-domain')
@click.argument('domain')
@click.option('--site', prompt=True)
@click.option('--ssl-certificate', help="Absolute path to SSL Certificate")
@click.option('--ssl-certificate-key', help="Absolute path to SSL Certificate Key")
def add_domain(domain, site=None, ssl_certificate=None, ssl_certificate_key=None):
	"""Add custom domain to site"""
	from bench.config.site_config import add_domain

	if not site:
		print("Please specify site")
		sys.exit(1)

	add_domain(site, domain, ssl_certificate, ssl_certificate_key, bench_path='.')

@click.command('remove-domain')
@click.argument('domain')
@click.option('--site', prompt=True)
def remove_domain(domain, site=None):
	"""Remove custom domain from a site"""
	from bench.config.site_config import remove_domain

	if not site:
		print("Please specify site")
		sys.exit(1)

	remove_domain(site, domain, bench_path='.')

@click.command('sync-domains')
@click.option('--domain', multiple=True)
@click.option('--site', prompt=True)
def sync_domains(domain=None, site=None):
	from bench.config.site_config import sync_domains

	if not site:
		print("Please specify site")
		sys.exit(1)

	try:
		domains = list(map(str,domain))
	except Exception:
		print("Domains should be a json list of strings or dictionaries")
		sys.exit(1)

	changed = sync_domains(site, domains, bench_path='.')

	# if changed, success, else failure
	sys.exit(0 if changed else 1)

@click.command('role')
@click.argument('role')
@click.option('--admin_emails', default='')
@click.option('--mysql_root_password')
@click.option('--container', is_flag=True, default=False)
def setup_roles(role, **kwargs):
	"Install dependancies via roles"
	from bench.utils import run_playbook

	extra_vars = {"production": True}
	extra_vars.update(kwargs)

	if role:
		run_playbook('site.yml', extra_vars=extra_vars, tag=role)
	else:
		run_playbook('site.yml', extra_vars=extra_vars)

@click.command('fail2ban')
@click.option('--maxretry', default=6, help="Number of matches (i.e. value of the counter) which triggers ban action on the IP. Default is 6 seconds" )
@click.option('--bantime', default=600, help="The counter is set to zero if no match is found within 'findtime' seconds. Default is 600 seconds")
@click.option('--findtime', default=600, help='Duration (in seconds) for IP to be banned for. Negative number for "permanent" ban. Default is 600 seconds')
def setup_nginx_proxy_jail(**kwargs):
	from bench.utils import run_playbook
	run_playbook('roles/fail2ban/tasks/configure_nginx_jail.yml', extra_vars=kwargs)

@click.command('systemd')
@click.option('--user')
@click.option('--yes', help='Yes to regeneration of systemd config files', is_flag=True, default=False)
@click.option('--stop', help='Stop bench services', is_flag=True, default=False)
@click.option('--create-symlinks', help='Create Symlinks', is_flag=True, default=False)
@click.option('--delete-symlinks', help='Delete Symlinks', is_flag=True, default=False)
def setup_systemd(user=None, yes=False, stop=False, create_symlinks=False, delete_symlinks=False):
	"generate configs for systemd with an optional user argument"
	from bench.config.systemd import generate_systemd_config
	generate_systemd_config(bench_path=".", user=user, yes=yes,
		stop=stop, create_symlinks=create_symlinks, delete_symlinks=delete_symlinks)

setup.add_command(setup_sudoers)
setup.add_command(setup_nginx)
setup.add_command(reload_nginx)
setup.add_command(setup_supervisor)
setup.add_command(setup_redis)
setup.add_command(setup_letsencrypt)
setup.add_command(setup_wildcard_ssl)
setup.add_command(setup_production)
setup.add_command(setup_auto_update)
setup.add_command(setup_backups)
setup.add_command(setup_env)
setup.add_command(setup_procfile)
setup.add_command(setup_socketio)
setup.add_command(setup_requirements)
setup.add_command(setup_manager)
setup.add_command(setup_config)
setup.add_command(setup_fonts)
setup.add_command(add_domain)
setup.add_command(remove_domain)
setup.add_command(sync_domains)
setup.add_command(setup_firewall)
setup.add_command(set_ssh_port)
setup.add_command(setup_roles)
setup.add_command(setup_nginx_proxy_jail)
setup.add_command(setup_systemd)
