# imports - module imports
from bench.config.common_site_config import update_config, put_config

# imports - third party imports
import click


@click.group(help="Change bench configuration")
def config():
	pass


@click.command(
	"restart_supervisor_on_update",
	help="Enable/Disable auto restart of supervisor processes",
)
@click.argument("state", type=click.Choice(["on", "off"]))
def config_restart_supervisor_on_update(state):
	update_config({"restart_supervisor_on_update": state == "on"})


@click.command(
	"restart_systemd_on_update", help="Enable/Disable auto restart of systemd units"
)
@click.argument("state", type=click.Choice(["on", "off"]))
def config_restart_systemd_on_update(state):
	update_config({"restart_systemd_on_update": state == "on"})


@click.command(
	"dns_multitenant", help="Enable/Disable bench multitenancy on running bench update"
)
@click.argument("state", type=click.Choice(["on", "off"]))
def config_dns_multitenant(state):
	update_config({"dns_multitenant": state == "on"})


@click.command(
	"serve_default_site", help="Configure nginx to serve the default site on port 80"
)
@click.argument("state", type=click.Choice(["on", "off"]))
def config_serve_default_site(state):
	update_config({"serve_default_site": state == "on"})


@click.command("rebase_on_pull", help="Rebase repositories on pulling")
@click.argument("state", type=click.Choice(["on", "off"]))
def config_rebase_on_pull(state):
	update_config({"rebase_on_pull": state == "on"})


@click.command("http_timeout", help="Set HTTP timeout")
@click.argument("seconds", type=int)
def config_http_timeout(seconds):
	update_config({"http_timeout": seconds})


@click.command("set-common-config", help="Set value in common config")
@click.option("configs", "-c", "--config", multiple=True, type=(str, str))
def set_common_config(configs):
	import ast

	common_site_config = {}
	for key, value in configs:
		if value in ("true", "false"):
			value = value.title()
		try:
			value = ast.literal_eval(value)
		except ValueError:
			pass

		common_site_config[key] = value

	update_config(common_site_config, bench_path=".")


@click.command(
	"remove-common-config", help="Remove specific keys from current bench's common config"
)
@click.argument("keys", nargs=-1)
def remove_common_config(keys):
	from bench.bench import Bench

	common_site_config = Bench(".").conf
	for key in keys:
		if key in common_site_config:
			del common_site_config[key]

	put_config(common_site_config)


config.add_command(config_restart_supervisor_on_update)
config.add_command(config_restart_systemd_on_update)
config.add_command(config_dns_multitenant)
config.add_command(config_rebase_on_pull)
config.add_command(config_serve_default_site)
config.add_command(config_http_timeout)
config.add_command(set_common_config)
config.add_command(remove_common_config)
