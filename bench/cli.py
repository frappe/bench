import click
from .utils import init as _init
from .utils import setup_env as _setup_env
from .utils import new_site as _new_site 
from .utils import setup_backups as _setup_backups
from .utils import setup_auto_update as _setup_auto_update
from .utils import setup_sudoers as _setup_sudoers
from .utils import start as _start
from .utils import setup_procfile as _setup_procfile
from .utils import build_assets, patch_sites, exec_cmd, update_bench, get_frappe, setup_logging, get_config, update_config, restart_supervisor_processes
from .app import get_app as _get_app
from .app import new_app as _new_app
from .app import pull_all_apps
from .config import generate_config
from .migrate3to4 import main as _migrate_3to4
import os
import sys
import logging

logger = logging.getLogger('bench')

def cli():
	if len(sys.argv) > 2 and sys.argv[1] == "frappe":
		return frappe()
	return bench()

def frappe(bench='.'):
	f = get_frappe(bench=bench)
	os.chdir(os.path.join(bench, 'sites'))
	os.execv(f, [f] + sys.argv[2:])

@click.group()
def bench(bench='.'):
	"Bench manager for Frappe"
	# TODO add bench path context
	setup_logging(bench=bench)

@click.command()
@click.argument('path')
def init(path):
	"Create a new bench"
	_init(path)
	click.echo('Bench {} initialized'.format(path))

@click.command('get-app')
@click.argument('name')
@click.argument('git-url')
def get_app(name, git_url):
	"clone an app from the internet and set it up in your bench"
	_get_app(name, git_url)
	
@click.command('new-app')
@click.argument('app-name')
def new_app(app_name):
	"start a new app"
	_new_app(app_name)
	
@click.command('new-site')
@click.argument('site')
def new_site(site):
	"Create a new site in the bench"
	_new_site(site)
	
@click.command('update')
@click.option('--pull', flag_value=True, type=bool, help="Pull changes in all the apps in bench")
@click.option('--patch',flag_value=True, type=bool, help="Run migrations for all sites in the bench")
@click.option('--build',flag_value=True, type=bool, help="Build JS and CSS artifacts for the bench")
@click.option('--bench',flag_value=True, type=bool, help="Update bench")
@click.option('--restart-supervisor',flag_value=True, type=bool, help="restart supervisor processes after update")
@click.option('--auto',flag_value=True, type=bool)
def update(pull=False, patch=False, build=False, bench=False, auto=False, restart_supervisor=False):
	"Update bench"

	if not (pull or patch or build or bench):
		pull, patch, build, bench = True, True, True, True

	conf = get_config()
	if auto and not conf.get('auto_update'):
		sys.exit(1)
	if bench and conf.get('update_bench_on_update'):
		update_bench()
	if pull:
		pull_all_apps()
	if patch:
		patch_sites()
	if build:
		build_assets()
	# if restart_supervisor or conf.get('restart_supervisor_on_update'):
	# 	restart_supervisor_processes()

	print "_"*80
	print "https://frappe.io/buy - Donate to help make better free and open source tools"
	print

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
	_migrate_3to4(path)

## Setup
@click.group()
def setup():
	"Setup bench"
	pass
	
@click.command('sudoers')
def setup_sudoers():
	"Add commands to sudoers list for execution without password"
	_setup_sudoers()
	
@click.command('nginx')
def setup_nginx():
	"generate config for nginx"
	generate_config('nginx', 'nginx.conf')
	
@click.command('supervisor')
def setup_supervisor():
	"generate config for supervisor"
	generate_config('supervisor', 'supervisor.conf')

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

setup.add_command(setup_nginx)
setup.add_command(setup_sudoers)
setup.add_command(setup_supervisor)
setup.add_command(setup_auto_update)
setup.add_command(setup_dnsmasq)
setup.add_command(setup_backups)
setup.add_command(setup_env)
setup.add_command(setup_procfile)

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

config.add_command(config_auto_update)
config.add_command(config_update_bench_on_update)
config.add_command(config_restart_supervisor_on_update)

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
bench.add_command(migrate_3to4)

