import click
global FRAPPE_VERSION

@click.group()
def bench_command(bench='.'):
	"Bench manager for Frappe"
	from bench.app import get_current_frappe_version
	from bench.utils import setup_logging

	# TODO add bench path context
	global FRAPPE_VERSION
	FRAPPE_VERSION = get_current_frappe_version()
	setup_logging(bench=bench)


from bench.commands.make import init, get_app, new_app, new_site
bench_command.add_command(init)
bench_command.add_command(get_app)
bench_command.add_command(new_app)
bench_command.add_command(new_site)


from bench.commands.update import update, retry_upgrade, switch_to_master, switch_to_develop, switch_to_v4, switch_to_v5
bench_command.add_command(update)
bench_command.add_command(retry_upgrade)
bench_command.add_command(switch_to_master)
bench_command.add_command(switch_to_develop)
bench_command.add_command(switch_to_v4)
bench_command.add_command(switch_to_v5)


from bench.commands.utils import (start, restart, set_nginx_port, set_ssl_certificate, set_ssl_certificate_key, set_url_root,
	set_mariadb_host, set_default_site, download_translations, shell, backup_site, backup_all_sites, release)
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


from bench.commands.setup import setup
bench_command.add_command(setup)

from bench.commands.config import config
bench_command.add_command(config)
