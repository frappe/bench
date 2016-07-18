import click

def print_bench_version(ctx, param, value):
	"""Prints current bench version"""
	if not value or ctx.resilient_parsing:
		return

	import bench
	click.echo(bench.__version__)
	ctx.exit()

@click.group()
@click.option('--version', is_flag=True, is_eager=True, callback=print_bench_version, expose_value=False)
def bench_command(bench_path='.'):
	"""Bench manager for Frappe"""
	import bench
	from bench.app import get_current_frappe_version
	from bench.utils import setup_logging

	bench.set_frappe_version(bench_path=bench_path)
	setup_logging(bench_path=bench_path)


from bench.commands.make import init, get_app, new_app, remove_app, new_site
bench_command.add_command(init)
bench_command.add_command(get_app)
bench_command.add_command(new_app)
bench_command.add_command(remove_app)
bench_command.add_command(new_site)


from bench.commands.update import update, retry_upgrade, switch_to_branch, switch_to_master, switch_to_develop, switch_to_v4, switch_to_v5
bench_command.add_command(update)
bench_command.add_command(retry_upgrade)
bench_command.add_command(switch_to_branch)
bench_command.add_command(switch_to_master)
bench_command.add_command(switch_to_develop)
bench_command.add_command(switch_to_v4)
bench_command.add_command(switch_to_v5)


from bench.commands.utils import (start, restart, set_nginx_port, set_ssl_certificate, set_ssl_certificate_key, set_url_root,
	set_mariadb_host, set_default_site, download_translations, shell, backup_site, backup_all_sites, release, renew_lets_encrypt,
	disable_production, bench_src)
bench_command.add_command(start)
bench_command.add_command(restart)
bench_command.add_command(set_nginx_port)
bench_command.add_command(set_ssl_certificate)
bench_command.add_command(set_ssl_certificate_key)
bench_command.add_command(set_url_root)
bench_command.add_command(set_mariadb_host)
bench_command.add_command(set_default_site)
bench_command.add_command(download_translations)
bench_command.add_command(shell)
bench_command.add_command(backup_site)
bench_command.add_command(backup_all_sites)
bench_command.add_command(release)
bench_command.add_command(renew_lets_encrypt)
bench_command.add_command(disable_production)
bench_command.add_command(bench_src)

from bench.commands.setup import setup
bench_command.add_command(setup)


from bench.commands.config import config
bench_command.add_command(config)
