# imports - standard imports
import ast
import json

# imports - module imports
from bench.config.common_site_config import update_config, get_config, put_config

# imports - third party imports
import click



class AliasedGroup(click.Group):
	def get_command(self, ctx, cmd_name):
		try:
			cmd_name = ALIASES[cmd_name].name
		except KeyError:
			pass
		return super(AliasedGroup, self).get_command(ctx, cmd_name)


@click.group(cls=AliasedGroup, help='Change bench configuration')
def config():
	pass


@click.command('auto_update', help='Enable/Disable auto update for bench')
@click.argument('state', type=click.Choice(['on', 'off']))
def config_auto_update(state):
	state = True if state == 'on' else False
	update_config({'auto_update': state})


@click.command('restart_supervisor_on_update', help='Enable/Disable auto restart of supervisor processes')
@click.argument('state', type=click.Choice(['on', 'off']))
def config_restart_supervisor_on_update(state):
	state = True if state == 'on' else False
	update_config({'restart_supervisor_on_update': state})


@click.command('restart_systemd_on_update', help='Enable/Disable auto restart of systemd units')
@click.argument('state', type=click.Choice(['on', 'off']))
def config_restart_systemd_on_update(state):
	state = True if state == 'on' else False
	update_config({'restart_systemd_on_update': state})


@click.command('update_bench_on_update', help='Enable/Disable bench updates on running bench update')
@click.argument('state', type=click.Choice(['on', 'off']))
def config_update_bench_on_update(state):
	state = True if state == 'on' else False
	update_config({'update_bench_on_update': state})


@click.command('dns_multitenant', help='Enable/Disable bench multitenancy on running bench update')
@click.argument('state', type=click.Choice(['on', 'off']))
def config_dns_multitenant(state):
	state = True if state == 'on' else False
	update_config({'dns_multitenant': state})


@click.command('serve_default_site', help='Configure nginx to serve the default site on port 80')
@click.argument('state', type=click.Choice(['on', 'off']))
def config_serve_default_site(state):
	state = True if state == 'on' else False
	update_config({'serve_default_site': state})


@click.command('rebase_on_pull', help='Rebase repositories on pulling')
@click.argument('state', type=click.Choice(['on', 'off']))
def config_rebase_on_pull(state):
	state = True if state == 'on' else False
	update_config({'rebase_on_pull': state})


@click.command('http_timeout', help='Set HTTP timeout')
@click.argument('seconds', type=int)
def config_http_timeout(seconds):
	update_config({'http_timeout': seconds})


@click.command('set-common-config', help='Set value in common config')
@click.option('configs', '-c', '--config', multiple=True, type=(str, str))
def set_common_config(configs):
	common_site_config = {}
	for key, value in configs:
		if value in ("False", "True"):
			value = ast.literal_eval(value)

		elif "." in value:
			try:
				value = float(value)
			except ValueError:
				pass

		elif "{" in value or "[" in value:
			try:
				value = json.loads(value)
			except ValueError:
				pass

		else:
			try:
				value = int(value)
			except ValueError:
				pass

		common_site_config[key] = value

	update_config(common_site_config, bench_path='.')


@click.command('remove-common-config', help='Remove specific keys from current bench\'s common config')
@click.argument('keys', nargs=-1)
def remove_common_config(keys):
	common_site_config = get_config('.')
	for key in keys:
		if key in common_site_config:
			del common_site_config[key]

	put_config(common_site_config)


config.add_command(config_auto_update)
config.add_command(config_update_bench_on_update)
config.add_command(config_restart_supervisor_on_update)
config.add_command(config_restart_systemd_on_update)
config.add_command(config_dns_multitenant)
config.add_command(config_serve_default_site)
config.add_command(config_http_timeout)
config.add_command(set_common_config)
config.add_command(remove_common_config)

# aliases for _ seperated commands to - ones
ALIASES = {k.replace('_', '-'):v for k, v in config.commands.items() if '_' in k}
