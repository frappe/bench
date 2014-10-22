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
from .utils import set_default_site as _set_default_site
from .utils import (build_assets, patch_sites, exec_cmd, update_bench, get_frappe, setup_logging,
		get_config, update_config, restart_supervisor_processes, put_config, default_config, update_requirements,
		backup_all_sites, backup_site, get_sites, prime_wheel_cache)
from .app import get_app as _get_app
from .app import new_app as _new_app
from .app import pull_all_apps
from .config import generate_nginx_config, generate_supervisor_config
import os
import sys
import logging
import copy

logger = logging.getLogger('bench')

def cli():
	if len(sys.argv) > 2 and sys.argv[1] == "frappe":
		return frappe()
	return bench()

def frappe(bench='.'):
	f = get_frappe(bench=bench)
	os.chdir(os.path.join(bench, 'sites'))
	os.execv(f, [f] + sys.argv[2:])

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
	setup_logging(bench=bench)

@click.command()
@click.argument('path')
@click.option('--apps_path', default=None, help="path to json files with apps to install after init")
@click.option('--frappe-path', default=None, help="path to frappe repo")
@click.option('--frappe-branch', default=None, help="path to frappe repo")
@click.option('--no-procfile', flag_value=True, type=bool, help="Pull changes in all the apps in bench")
@click.option('--no-backups',flag_value=True, type=bool, help="Run migrations for all sites in the bench")
@click.option('--no-auto-update',flag_value=True, type=bool, help="Build JS and CSS artifacts for the bench")
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
@click.option('--pull', flag_value=True, type=bool, help="Pull changes in all the apps in bench")
@click.option('--patch',flag_value=True, type=bool, help="Run migrations for all sites in the bench")
@click.option('--build',flag_value=True, type=bool, help="Build JS and CSS artifacts for the bench")
@click.option('--bench',flag_value=True, type=bool, help="Update bench")
@click.option('--requirements',flag_value=True, type=bool, help="Update requirements")
@click.option('--restart-supervisor',flag_value=True, type=bool, help="restart supervisor processes after update")
@click.option('--auto',flag_value=True, type=bool)
@click.option('--no-backup',flag_value=True, type=bool)
def update(pull=False, patch=False, build=False, bench=False, auto=False, restart_supervisor=False, requirements=False, no_backup=False):
	"Update bench"

	if not (pull or patch or build or bench or requirements):
		pull, patch, build, bench, requirements = True, True, True, True, True

	conf = get_config()
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
				'restart-supervisor': restart_supervisor
		})
	if pull:
		pull_all_apps()
	if requirements:
		update_requirements()
	if patch:
		if not no_backup:
			backup_all_sites()
		patch_sites()
	if build:
		build_assets()
	if restart_supervisor or conf.get('restart_supervisor_on_update'):
		restart_supervisor_processes()

	print "_"*80
	print "https://frappe.io/buy - Donate to help make better free and open source tools"
	print

def restart_update(kwargs):
	args = ['--'+k for k, v in kwargs.items() if v]
	print 'restarting '
	os.execv(sys.argv[0], sys.argv[:2] + args)

@click.command('restart')
def restart():
	"Restart supervisor processes"
	restart_supervisor_processes()

@click.command('start')
def start():
	"Start Frappe development processes"
	_start()

@click.command('migrate-3to4')
@click.argument('path')
def migrate_3to4(path):
	"Migrate from ERPNext v3.x"
	exec_cmd("{python} {migrate_3to4} {site}".format(
			python=os.path.join('env', 'bin', 'python'),
			migrate_3to4=os.path.join(os.path.dirname(__file__), 'migrate3to4.py'),
			site=path))

@click.command('set-nginx-port')
@click.argument('site')
@click.argument('port', type=int)
def set_nginx_port(site, port):
	"Set nginx port for site"
	_set_nginx_port(site, port)

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
def _release(app, bump_type):
	"Release app (internal to the Frappe team)"
	from .release import release
	repo = os.path.join('apps', app)
	release(repo, bump_type)

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
	update_config({'restart_supervisor_on_update': True})

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
def setup_procfile():
	"Setup Procfile for bench start"
	_setup_procfile()

@click.command('config')
def setup_config():
	"overwrite or make config.json"
	put_config(default_config)

setup.add_command(setup_nginx)
setup.add_command(setup_sudoers)
setup.add_command(setup_supervisor)
setup.add_command(setup_auto_update)
setup.add_command(setup_dnsmasq)
setup.add_command(setup_backups)
setup.add_command(setup_env)
setup.add_command(setup_procfile)
setup.add_command(setup_config)

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

@click.command('mariadb-config')
def _patch_mariadb_config():
	"patch MariaDB 5.5.40"
	repo_dir = os.path.dirname(__file__)
	exec_cmd(os.path.join(repo_dir, 'patches', 'fix-mariadb.sh'), cwd=os.path.join(repo_dir, 'patches'))

patch.add_command(_patch_mariadb_config)

#Bench commands

bench.add_command(init)
bench.add_command(get_app)
bench.add_command(new_app)
bench.add_command(new_site)
bench.add_command(setup)
bench.add_command(update)
bench.add_command(restart)
bench.add_command(config)
bench.add_command(start)
bench.add_command(set_nginx_port)
bench.add_command(set_default_site)
bench.add_command(migrate_3to4)
bench.add_command(shell)
bench.add_command(_backup_all_sites)
bench.add_command(_backup_site)
bench.add_command(_prime_wheel_cache)
bench.add_command(_release)
bench.add_command(patch)
