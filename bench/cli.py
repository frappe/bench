import click
from .utils import init as _init
from .utils import setup_env as _setup_env
from .utils import new_site as _new_site
from .utils import build_assets, patch_sites, get_sites_dir, get_bench_dir, get_frappe, exec_cmd
from .app import get_app as _get_app
from .app import new_app as _new_app
from .app import pull_all_apps
from .config import generate_config
import os

@click.group()
def bench():
	pass

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
def update(pull=False, patch=False, build=False):
	if not (pull or patch or build):
		pull, patch, build = True, True, True
	if pull:
		pull_all_apps()
	if patch:
		patch_sites()
	if build:
		build_assets()

## Setup
@click.group()
def setup():
	pass
	
@click.command('sudoers')
def setup_sudoers():
	pass
	
@click.command('nginx')
def setup_nginx():
	generate_config('nginx', 'nginx.conf')
	
@click.command('supervisor')
def setup_supervisor():
	generate_config('supervisor', 'supervisor.conf')

@click.command('auto-update')
def setup_auto_update():
	exec_cmd('echo \"`crontab -l`\" | uniq | sed -e \"a0 10 * * * cd {bench_dir} &&  {bench} update\" | grep -v "^$" | uniq | crontab'.format(bench_dir=get_bench_dir(),
	bench=os.path.join(get_bench_dir(), 'env', 'bin', 'bench')))
	
@click.command('backups')
def setup_backups():
	exec_cmd('echo \"`crontab -l`\" | uniq | sed -e \"a0 */6 * * * cd {sites_dir} &&  {frappe} --backup all\" | grep -v "^$" | uniq | crontab'.format(sites_dir=get_sites_dir(),
	frappe=get_frappe()))

@click.command('dnsmasq')
def setup_dnsmasq():
	pass

@click.command('env')
def setup_env():
	_setup_env()
	pass

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
