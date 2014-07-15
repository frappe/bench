import click
from .utils import init as _init
from .utils import setup_env as _setup_env
from .utils import new_site as _new_site 
from .utils import setup_backups as _setup_backups
from .utils import setup_auto_update as _setup_auto_update
from .utils import setup_sudoers as _setup_sudoers
from .utils import build_assets, patch_sites, exec_cmd, update_bench, get_frappe, setup_logging, get_config
from .app import get_app as _get_app
from .app import new_app as _new_app
from .app import pull_all_apps
from .config import generate_config
import os
import sys
import logging

logger = logging.getLogger('bench')

def cli():
	if sys.argv[1] == "frappe":
		return frappe()
	return bench()

def frappe(bench='.'):
	f = get_frappe(bench=bench)
	os.chdir(os.path.join(bench, 'sites'))
	os.execv(f, [f] + sys.argv[2:])

@click.group()
def bench(bench='.'):
	# TODO add bench path context
	setup_logging(bench=bench)

@click.command()
@click.argument('path')
def init(path):
	_init(path)
	click.echo('Bench {} initialized'.format(path))

@click.command('get-app')
@click.argument('name')
@click.argument('git-url')
def get_app(name, git_url):
	_get_app(name, git_url)
	
@click.command('new-app')
@click.argument('app-name')
def new_app(app_name):
	_new_app(app_name)
	
@click.command('new-site')
@click.argument('site')
def new_site(site):
	_new_site(site)
	
@click.command('update')
@click.option('--pull', flag_value=True, type=bool)
@click.option('--patch',flag_value=True, type=bool)
@click.option('--build',flag_value=True, type=bool)
@click.option('--bench',flag_value=True, type=bool)
def update(pull=False, patch=False, build=False, bench=False):
	if not (pull or patch or build or bench):
		pull, patch, build, bench = True, True, True, True
	if bench and get_config().get('update_bench_on_update'):
		update_bench()
	if pull:
		pull_all_apps()
	if patch:
		patch_sites()
	if build:
		build_assets()

@click.command('restart')
def restart():
	exec_cmd("sudo supervisorctl restart frappe:")

## Setup
@click.group()
def setup():
	pass
	
@click.command('sudoers')
def setup_sudoers():
	_setup_sudoers()
	
@click.command('nginx')
def setup_nginx():
	generate_config('nginx', 'nginx.conf')
	
@click.command('supervisor')
def setup_supervisor():
	generate_config('supervisor', 'supervisor.conf')

@click.command('auto-update')
def setup_auto_update():
	_setup_auto_update()
	
@click.command('backups')
def setup_backups():
	_setup_backups()

@click.command('dnsmasq')
def setup_dnsmasq():
	pass

@click.command('env')
def setup_env():
	_setup_env()

setup.add_command(setup_nginx)
setup.add_command(setup_sudoers)
setup.add_command(setup_supervisor)
setup.add_command(setup_auto_update)
setup.add_command(setup_dnsmasq)
setup.add_command(setup_backups)
setup.add_command(setup_env)

#Bench commands

bench.add_command(init)
bench.add_command(get_app)
bench.add_command(new_app)
bench.add_command(new_site)
bench.add_command(setup)
bench.add_command(update)
bench.add_command(restart)

