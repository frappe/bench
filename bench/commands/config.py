import click
from bench.config.common_site_config import update_config

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
