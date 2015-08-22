import click
from .utils import init as _init
from .utils import setup_env as _setup_env
from .utils import new_site as _new_site
from .utils import setup_backups as _setup_backups
from .utils import setup_auto_update as _setup_auto_update
from .utils import setup_sudoers as _setup_sudoers
from .utils import start as _start
from .utils import setup_procfile as _setup_procfile
from .utils import set_nginx_port as _set_nginx_port
from .utils import set_url_root as _set_url_root
from .utils import set_default_site as _set_default_site
from .utils import (build_assets, patch_sites, exec_cmd, update_bench, get_env_cmd, get_frappe, setup_logging,
					get_config, update_config, restart_supervisor_processes, put_config, default_config, update_requirements,
					backup_all_sites, backup_site, get_sites, prime_wheel_cache, is_root, set_mariadb_host, drop_privileges,
					fix_file_perms, fix_prod_setup_perms, set_ssl_certificate, set_ssl_certificate_key, get_cmd_output, post_upgrade,
					pre_upgrade, validate_upgrade, PatchError, download_translations_p, setup_socketio)
from .app import get_app as _get_app
from .app import new_app as _new_app
from .app import pull_all_apps, get_apps, get_current_frappe_version, is_version_upgrade, switch_to_v4, switch_to_v5, switch_to_master, switch_to_develop
from .config import generate_nginx_config, generate_supervisor_config, generate_redis_cache_config, generate_redis_async_broker_config
from .production_setup import setup_production as _setup_production
from .migrate_to_v5 import migrate_to_v5
import os
import sys
import logging
import copy
import json
import pwd
import grp
import subprocess

logger = logging.getLogger('bench')
from_command_line = False

global FRAPPE_VERSION

def cli():
	global from_command_line
	from_command_line = True

	check_uid()
	change_dir()
	change_uid()
	if len(sys.argv) > 2 and sys.argv[1] == "frappe":
		return old_frappe_cli()
	elif len(sys.argv) > 1 and sys.argv[1] in get_frappe_commands():
		return frappe_cmd()
	elif len(sys.argv) > 1 and sys.argv[1] in ("--site", "--verbose", "--force", "--profile"):
		return frappe_cmd()
	elif len(sys.argv) > 1 and sys.argv[1]=="--help":
		print click.Context(bench).get_help()
		print
		print get_frappe_help()
		return
	elif len(sys.argv) > 1 and sys.argv[1] in get_apps():
		return app_cmd()
	else:
		try:
			bench()
		except PatchError:
			sys.exit(1)

def cmd_requires_root():
	if len(sys.argv) > 2 and sys.argv[2] in ('production', 'sudoers'):
	    return True
	if len(sys.argv) > 2 and sys.argv[1] in ('patch',):
	    return True

def check_uid():
	if cmd_requires_root() and not is_root():
		print 'superuser privileges required for this command'
		sys.exit(1)

def change_uid():
	if is_root() and not cmd_requires_root():
		frappe_user = get_config().get('frappe_user')
		if frappe_user:
			drop_privileges(uid_name=frappe_user, gid_name=frappe_user)
			os.environ['HOME'] = pwd.getpwnam(frappe_user).pw_dir
		else:
			print 'You should not run this command as root'
			sys.exit(1)

def change_dir():
	if os.path.exists('config.json') or "init" in sys.argv:
		return
	dir_path_file = '/etc/frappe_bench_dir'
	if os.path.exists(dir_path_file):
		with open(dir_path_file) as f:
			dir_path = f.read().strip()
		if os.path.exists(dir_path):
			os.chdir(dir_path)

def old_frappe_cli(bench='.'):
	f = get_frappe(bench=bench)
	os.chdir(os.path.join(bench, 'sites'))
	os.execv(f, [f] + sys.argv[2:])

def app_cmd(bench='.'):
	f = get_env_cmd('python', bench=bench)
	os.chdir(os.path.join(bench, 'sites'))
	os.execv(f, [f] + ['-m', 'frappe.utils.bench_helper'] + sys.argv[1:])

def frappe_cmd(bench='.'):
	f = get_env_cmd('python', bench=bench)
	os.chdir(os.path.join(bench, 'sites'))
	os.execv(f, [f] + ['-m', 'frappe.utils.bench_helper', 'frappe'] + sys.argv[1:])

def get_frappe_commands(bench='.'):
	python = get_env_cmd('python', bench=bench)
	sites_path = os.path.join(bench, 'sites')
	if not os.path.exists(sites_path):
		return []
	try:
		return json.loads(get_cmd_output("{python} -m frappe.utils.bench_helper get-frappe-commands".format(python=python), cwd=sites_path))
	except subprocess.CalledProcessError:
		return []

def get_frappe_help(bench='.'):
	python = get_env_cmd('python', bench=bench)
	sites_path = os.path.join(bench, 'sites')
	if not os.path.exists(sites_path):
		return []
	try:
		out = get_cmd_output("{python} -m frappe.utils.bench_helper get-frappe-help".format(python=python), cwd=sites_path)
		return "Framework commands:\n" + out.split('Commands:')[1]
	except subprocess.CalledProcessError:
		return ""

@click.command()
def shell(bench='.'):
	if not os.environ.get('SHELL'):
		print "Cannot get shell"
		sys.exit(1)
	if not os.path.exists('sites'):
		print "sites dir doesn't exist"
		sys.exit(1)
	env = copy.copy(os.environ)
	env['PS1'] = '(' + os.path.basename(os.path.dirname(os.path.abspath(__file__))) + ')' + env.get('PS1', '')
	env['PATH'] = os.path.dirname(os.path.abspath(os.path.join('env','bin')) + ':' + env['PATH'])
	os.chdir('sites')
	os.execve(env['SHELL'], [env['SHELL']], env)

@click.group()
def bench(bench='.'):
	"Bench manager for Frappe"
	# TODO add bench path context
	global FRAPPE_VERSION
	FRAPPE_VERSION = get_current_frappe_version()
	setup_logging(bench=bench)

@click.command()
@click.argument('path')
@click.option('--apps_path', default=None, help="path to json files with apps to install after init")
@click.option('--frappe-path', default=None, help="path to frappe repo")
@click.option('--frappe-branch', default=None, help="path to frappe repo")
@click.option('--no-procfile', is_flag=True, help="Pull changes in all the apps in bench")
@click.option('--no-backups',is_flag=True, help="Run migrations for all sites in the bench")
@click.option('--no-auto-update',is_flag=True, help="Build JS and CSS artifacts for the bench")
def init(path, apps_path, frappe_path, frappe_branch, no_procfile, no_backups,
		no_auto_update):
	"Create a new bench"
	_init(path, apps_path=apps_path, no_procfile=no_procfile, no_backups=no_backups,
			no_auto_update=no_auto_update, frappe_path=frappe_path, frappe_branch=frappe_branch)
	click.echo('Bench {} initialized'.format(path))

@click.command('get-app')
@click.argument('name')
@click.argument('git-url')
@click.option('--branch', default=None, help="branch to checkout")
def get_app(name, git_url, branch):
	"clone an app from the internet and set it up in your bench"
	_get_app(name, git_url, branch=branch)

@click.command('new-app')
@click.argument('app-name')
def new_app(app_name):
	"start a new app"
	_new_app(app_name)

@click.command('new-site')
@click.option('--mariadb-root-password', help="MariaDB root password")
@click.option('--admin-password', help="admin password to set for site")
@click.argument('site')
def new_site(site, mariadb_root_password=None, admin_password=None):
	"Create a new site in the bench"
	_new_site(site, mariadb_root_password=mariadb_root_password, admin_password=admin_password)

#TODO: Not DRY
@click.command('update')
@click.option('--pull', is_flag=True, help="Pull changes in all the apps in bench")
@click.option('--patch',is_flag=True, help="Run migrations for all sites in the bench")
@click.option('--build',is_flag=True, help="Build JS and CSS artifacts for the bench")
@click.option('--bench',is_flag=True, help="Update bench")
@click.option('--requirements',is_flag=True, help="Update requirements")
@click.option('--restart-supervisor',is_flag=True, help="restart supervisor processes after update")
@click.option('--auto',is_flag=True)
@click.option('--upgrade',is_flag=True)
@click.option('--no-backup',is_flag=True)
@click.option('--force',is_flag=True)
def _update(pull=False, patch=False, build=False, bench=False, auto=False, restart_supervisor=False, requirements=False, no_backup=False, upgrade=False, force=False):
	"Update bench"

	if not (pull or patch or build or bench or requirements):
		pull, patch, build, bench, requirements = True, True, True, True, True

	conf = get_config()

	version_upgrade = is_version_upgrade()

	if version_upgrade[0] and not upgrade:
		print
		print
		print "This update will cause a major version change in Frappe/ERPNext from {0} to {1}.".format(*version_upgrade[1:])
		print "This would take significant time to migrate and might break custom apps. Please run `bench update --upgrade` to confirm."
		print
		print "You can stay on the latest stable release by running `bench switch-to-master` or pin your bench to {0} by running `bench switch-to-v{0}`".format(version_upgrade[1])
		sys.exit(1)

	if conf.get('release_bench'):
		print 'Release bench, cannot update'
		sys.exit(1)

	if auto:
		sys.exit(1)

	if bench and conf.get('update_bench_on_update'):
		update_bench()
		restart_update({
				'pull': pull,
				'patch': patch,
				'build': build,
				'requirements': requirements,
				'no-backup': no_backup,
				'restart-supervisor': restart_supervisor,
				'upgrade': upgrade
		})

	update(pull, patch, build, bench, auto, restart_supervisor, requirements, no_backup, upgrade, force=force)

	print "_"*80
	print "https://frappe.io/buy - Donate to help make better free and open source tools"
	print

def update(pull=False, patch=False, build=False, bench=False, auto=False, restart_supervisor=False, requirements=False, no_backup=False, upgrade=False, bench_path='.', force=False):
	conf = get_config(bench=bench_path)
	version_upgrade = is_version_upgrade(bench=bench_path)
	if version_upgrade[0] and not upgrade:
		raise Exception("Major Version Upgrade")

	if upgrade and (version_upgrade[0] or (not version_upgrade[0] and force)):
		validate_upgrade(version_upgrade[1], version_upgrade[2], bench=bench_path)

	if pull:
		pull_all_apps(bench=bench_path)

	if requirements:
		update_requirements(bench=bench_path)

	if upgrade and (version_upgrade[0] or (not version_upgrade[0] and force)):
		pre_upgrade(version_upgrade[1], version_upgrade[2], bench=bench_path)
		import utils, app
		reload(utils)
		reload(app)

	if patch:
		if not no_backup:
			backup_all_sites(bench=bench_path)
		patch_sites(bench=bench_path)
	if build:
		build_assets(bench=bench_path)
	if upgrade and (version_upgrade[0] or (not version_upgrade[0] and force)):
		post_upgrade(version_upgrade[1], version_upgrade[2], bench=bench_path)
	if restart_supervisor or conf.get('restart_supervisor_on_update'):
		restart_supervisor_processes(bench=bench_path)

	print "_"*80
	print "Bench: Open source installer + admin for Frappe and ERPNext (https://erpnext.com)"
	print

@click.command('retry-upgrade')
@click.option('--version', default=5)
def retry_upgrade(version):
	pull_all_apps()
	patch_sites()
	build_assets()
	post_upgrade(version-1, version)

def restart_update(kwargs):
	args = ['--'+k for k, v in kwargs.items() if v]
	os.execv(sys.argv[0], sys.argv[:2] + args)

@click.command('restart')
def restart():
	"Restart supervisor processes"
	restart_supervisor_processes()

@click.command('start')
@click.option('--no-dev', is_flag=True)
def start(no_dev=False):
	"Start Frappe development processes"
	_start(no_dev=no_dev)

@click.command('migrate-3to4')
@click.argument('path')
def migrate_3to4(path):
	"Migrate from ERPNext v3.x"
	exec_cmd("{python} {migrate_3to4} {site}".format(
			python=os.path.join('env', 'bin', 'python'),
			migrate_3to4=os.path.join(os.path.dirname(__file__), 'migrate3to4.py'),
			site=path))

@click.command('switch-to-master')
@click.option('--upgrade',is_flag=True)
def _switch_to_master(upgrade=False):
	"Switch frappe and erpnext to master branch"
	switch_to_master(upgrade=upgrade)
	print
	print 'Switched to master'
	print 'Please run `bench update --patch` to be safe from any differences in database schema'

@click.command('switch-to-develop')
@click.option('--upgrade',is_flag=True)
def _switch_to_develop(upgrade=False):
	"Switch frappe and erpnext to develop branch"
	switch_to_develop(upgrade=upgrade)
	print
	print 'Switched to develop'
	print 'Please run `bench update --patch` to be safe from any differences in database schema'

@click.command('switch-to-v4')
@click.option('--upgrade',is_flag=True)
def _switch_to_v4(upgrade=False):
	"Switch frappe and erpnext to v4 branch"
	switch_to_v4(upgrade=upgrade)
	print
	print 'Switched to v4'
	print 'Please run `bench update --patch` to be safe from any differences in database schema'

@click.command('switch-to-v5')
@click.option('--upgrade',is_flag=True)
def _switch_to_v5(upgrade=False):
	"Switch frappe and erpnext to v4 branch"
	switch_to_v5(upgrade=upgrade)
	print
	print 'Switched to v5'
	print 'Please run `bench update --patch` to be safe from any differences in database schema'

@click.command('set-nginx-port')
@click.argument('site')
@click.argument('port', type=int)
def set_nginx_port(site, port):
	"Set nginx port for site"
	_set_nginx_port(site, port)

@click.command('set-ssl-certificate')
@click.argument('site')
@click.argument('ssl-certificate-path')
def _set_ssl_certificate(site, ssl_certificate_path):
	"Set ssl certificate path for site"
	set_ssl_certificate(site, ssl_certificate_path)

@click.command('set-ssl-key')
@click.argument('site')
@click.argument('ssl-certificate-key-path')
def _set_ssl_certificate_key(site, ssl_certificate_key_path):
	"Set ssl certificate private key path for site"
	set_ssl_certificate_key(site, ssl_certificate_key_path)

@click.command('set-url-root')
@click.argument('site')
@click.argument('url-root')
def set_url_root(site, url_root):
	"Set url root for site"
	_set_url_root(site, url_root)

@click.command('set-mariadb-host')
@click.argument('host')
def _set_mariadb_host(host):
	"Set MariaDB host for bench"
	set_mariadb_host(host)

@click.command('set-default-site')
@click.argument('site')
def set_default_site(site):
	"Set default site for bench"
	_set_default_site(site)

@click.command('backup')
@click.argument('site')
def _backup_site(site):
	"backup site"
	if not site in get_sites(bench='.'):
		print 'site not found'
		sys.exit(1)
	backup_site(site, bench='.')

@click.command('backup-all-sites')
def _backup_all_sites():
	"backup all sites"
	backup_all_sites(bench='.')

@click.command('prime-wheel-cache')
def _prime_wheel_cache():
	"Update wheel cache"
	prime_wheel_cache(bench='.')

@click.command('release')
@click.argument('app', type=click.Choice(['frappe', 'erpnext', 'shopping_cart']))
@click.argument('bump-type', type=click.Choice(['major', 'minor', 'patch']))
@click.option('--develop', default='develop')
@click.option('--master', default='master')
def _release(app, bump_type, develop, master):
	"Release app (internal to the Frappe team)"
	from .release import release
	repo = os.path.join('apps', app)
	release(repo, bump_type, develop, master)

## Setup
@click.group()
def setup():
	"Setup bench"
	pass

@click.command('sudoers')
@click.argument('user')
def setup_sudoers(user):
	"Add commands to sudoers list for execution without password"
	_setup_sudoers(user)

@click.command('nginx')
def setup_nginx():
	"generate config for nginx"
	generate_nginx_config()

@click.command('supervisor')
def setup_supervisor():
	"generate config for supervisor"
	generate_supervisor_config()

@click.command('redis-cache')
def setup_redis_cache():
	"generate config for redis cache"
	generate_redis_cache_config()

@click.command('redis-async-broker')
def setup_redis_async_broker():
	"generate config for redis async broker"
	generate_redis_async_broker_config()

@click.command('production')
@click.argument('user')
def setup_production(user):
	"setup bench for production"
	_setup_production(user=user)

@click.command('auto-update')
def setup_auto_update():
	"Add cronjob for bench auto update"
	_setup_auto_update()

@click.command('backups')
def setup_backups():
	"Add cronjob for bench backups"
	_setup_backups()

@click.command('dnsmasq')
def setup_dnsmasq():
	pass

@click.command('env')
def setup_env():
	"Setup virtualenv for bench"
	_setup_env()

@click.command('procfile')
@click.option('--with-watch', is_flag=True)
@click.option('--with-celery-broker', is_flag=True)
def setup_procfile(with_celery_broker, with_watch):
	"Setup Procfile for bench start"
	_setup_procfile(with_celery_broker, with_watch)

@click.command('socketio')
def _setup_socketio():
	"Setup node deps for socketio server"
	setup_socketio()

@click.command('config')
def setup_config():
	"overwrite or make config.json"
	put_config(default_config)

setup.add_command(setup_nginx)
setup.add_command(setup_sudoers)
setup.add_command(setup_supervisor)
setup.add_command(setup_redis_cache)
setup.add_command(setup_redis_async_broker)
setup.add_command(setup_auto_update)
setup.add_command(setup_dnsmasq)
setup.add_command(setup_backups)
setup.add_command(setup_env)
setup.add_command(setup_procfile)
setup.add_command(_setup_socketio)
setup.add_command(setup_config)
setup.add_command(setup_production)

## Config
## Not DRY
@click.group()
def config():
	"change bench configuration"
	pass

@click.command('auto_update')
@click.argument('state', type=click.Choice(['on', 'off']))
def config_auto_update(state):
	"Enable/Disable auto update for bench"
	state = True if state == 'on' else False
	update_config({'auto_update': state})

@click.command('restart_supervisor_on_update')
@click.argument('state', type=click.Choice(['on', 'off']))
def config_restart_supervisor_on_update(state):
	"Enable/Disable auto restart of supervisor processes"
	state = True if state == 'on' else False
	update_config({'restart_supervisor_on_update': state})

@click.command('update_bench_on_update')
@click.argument('state', type=click.Choice(['on', 'off']))
def config_update_bench_on_update(state):
	"Enable/Disable bench updates on running bench update"
	state = True if state == 'on' else False
	update_config({'update_bench_on_update': state})

@click.command('dns_multitenant')
@click.argument('state', type=click.Choice(['on', 'off']))
def config_dns_multitenant(state):
	"Enable/Disable bench updates on running bench update"
	state = True if state == 'on' else False
	update_config({'dns_multitenant': state})

@click.command('serve_default_site')
@click.argument('state', type=click.Choice(['on', 'off']))
def config_serve_default_site(state):
	"Configure nginx to serve the default site on port 80"
	state = True if state == 'on' else False
	update_config({'serve_default_site': state})

@click.command('rebase_on_pull')
@click.argument('state', type=click.Choice(['on', 'off']))
def config_rebase_on_pull(state):
	"Rebase repositories on pulling"
	state = True if state == 'on' else False
	update_config({'rebase_on_pull': state})

@click.command('http_timeout')
@click.argument('seconds', type=int)
def config_http_timeout(seconds):
	"set http timeout"
	update_config({'http_timeout': seconds})

config.add_command(config_auto_update)
config.add_command(config_update_bench_on_update)
config.add_command(config_restart_supervisor_on_update)
config.add_command(config_dns_multitenant)
config.add_command(config_serve_default_site)
config.add_command(config_http_timeout)


@click.group()
def patch():
	pass

@click.command('fix-prod-perms')
def _fix_prod_perms():
	"Fix permissions if supervisor processes were run as root"
	if os.path.exists("config/supervisor.conf"):
		exec_cmd("supervisorctl stop frappe:")

	fix_prod_setup_perms()

	if os.path.exists("config/supervisor.conf"):
		exec_cmd("{bench} setup supervisor".format(bench=sys.argv[0]))
		exec_cmd("supervisorctl reload")


@click.command('fix-file-perms')
def _fix_file_perms():
	"Fix file permissions"
	fix_file_perms()

patch.add_command(_fix_file_perms)
patch.add_command(_fix_prod_perms)


@click.command('download-translations')
def _download_translations():
	"Download latest translations"
	download_translations_p()

#Bench commands

bench.add_command(init)
bench.add_command(get_app)
bench.add_command(new_app)
bench.add_command(new_site)
bench.add_command(setup)
bench.add_command(_update)
bench.add_command(restart)
bench.add_command(config)
bench.add_command(start)
bench.add_command(set_nginx_port)
bench.add_command(_set_ssl_certificate)
bench.add_command(_set_ssl_certificate_key)
bench.add_command(_set_mariadb_host)
bench.add_command(set_default_site)
bench.add_command(migrate_3to4)
bench.add_command(_switch_to_master)
bench.add_command(_switch_to_develop)
bench.add_command(_switch_to_v4)
bench.add_command(_switch_to_v5)
bench.add_command(shell)
bench.add_command(_backup_all_sites)
bench.add_command(_backup_site)
bench.add_command(_prime_wheel_cache)
bench.add_command(_release)
bench.add_command(patch)
bench.add_command(set_url_root)
bench.add_command(retry_upgrade)
bench.add_command(_download_translations)
