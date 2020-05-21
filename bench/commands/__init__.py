import click


def print_bench_version(ctx, param, value):
	"""Prints current bench version"""
	if not value or ctx.resilient_parsing:
		return

	import bench
	click.echo(bench.VERSION)
	ctx.exit()

@click.group()
@click.option('--version', is_flag=True, is_eager=True, callback=print_bench_version, expose_value=False)
def bench_command(bench_path='.'):
	import bench
	bench.set_frappe_version(bench_path=bench_path)


from bench.commands.make import init, get_app, new_app, remove_app, exclude_app_for_update, include_app_for_update, pip
bench_command.add_command(init)
bench_command.add_command(get_app)
bench_command.add_command(new_app)
bench_command.add_command(remove_app)
bench_command.add_command(exclude_app_for_update)
bench_command.add_command(include_app_for_update)
bench_command.add_command(pip)


from bench.commands.update import update, retry_upgrade, switch_to_branch, switch_to_master, switch_to_develop
bench_command.add_command(update)
bench_command.add_command(retry_upgrade)
bench_command.add_command(switch_to_branch)
bench_command.add_command(switch_to_master)
bench_command.add_command(switch_to_develop)


from bench.commands.utils import (start, restart, set_nginx_port, set_ssl_certificate, set_ssl_certificate_key, set_url_root,
	set_mariadb_host, set_default_site, download_translations, backup_site, backup_all_sites, release, renew_lets_encrypt,
	disable_production, bench_src, prepare_beta_release, set_redis_cache_host, set_redis_queue_host, set_redis_socketio_host, find_benches, migrate_env,
	generate_command_cache, clear_command_cache)
bench_command.add_command(start)
bench_command.add_command(restart)
bench_command.add_command(set_nginx_port)
bench_command.add_command(set_ssl_certificate)
bench_command.add_command(set_ssl_certificate_key)
bench_command.add_command(set_url_root)
bench_command.add_command(set_mariadb_host)
bench_command.add_command(set_redis_cache_host)
bench_command.add_command(set_redis_queue_host)
bench_command.add_command(set_redis_socketio_host)
bench_command.add_command(set_default_site)
bench_command.add_command(download_translations)
bench_command.add_command(backup_site)
bench_command.add_command(backup_all_sites)
bench_command.add_command(release)
bench_command.add_command(renew_lets_encrypt)
bench_command.add_command(disable_production)
bench_command.add_command(bench_src)
bench_command.add_command(prepare_beta_release)
bench_command.add_command(find_benches)
bench_command.add_command(migrate_env)
bench_command.add_command(generate_command_cache)
bench_command.add_command(clear_command_cache)

from bench.commands.setup import setup
bench_command.add_command(setup)


from bench.commands.config import config
bench_command.add_command(config)

from bench.commands.git import remote_set_url, remote_reset_url, remote_urls
bench_command.add_command(remote_set_url)
bench_command.add_command(remote_reset_url)
bench_command.add_command(remote_urls)

from bench.commands.install import install
bench_command.add_command(install)
