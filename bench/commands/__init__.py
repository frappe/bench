# imports - third party imports
import click

# imports - module imports
from bench.utils.cli import (
	MultiCommandGroup,
	print_bench_version,
	use_experimental_feature,
	setup_verbosity,
)


@click.group(cls=MultiCommandGroup)
@click.option(
	"--version",
	is_flag=True,
	is_eager=True,
	callback=print_bench_version,
	expose_value=False,
)
@click.option(
	"--use-feature",
	is_eager=True,
	callback=use_experimental_feature,
	expose_value=False,
)
@click.option(
	"-v",
	"--verbose",
	is_flag=True,
	callback=setup_verbosity,
	expose_value=False,
)
def bench_command(bench_path="."):
	import bench

	bench.set_frappe_version(bench_path=bench_path)


from bench.commands.make import (
	drop,
	exclude_app_for_update,
	get_app,
	include_app_for_update,
	init,
	new_app,
	pip,
	remove_app,
)

bench_command.add_command(init)
bench_command.add_command(drop)
bench_command.add_command(get_app)
bench_command.add_command(new_app)
bench_command.add_command(remove_app)
bench_command.add_command(exclude_app_for_update)
bench_command.add_command(include_app_for_update)
bench_command.add_command(pip)


from bench.commands.update import (
	retry_upgrade,
	switch_to_branch,
	switch_to_develop,
	update,
)

bench_command.add_command(update)
bench_command.add_command(retry_upgrade)
bench_command.add_command(switch_to_branch)
bench_command.add_command(switch_to_develop)


from bench.commands.utils import (
	backup_all_sites,
	bench_src,
	clear_command_cache,
	disable_production,
	download_translations,
	find_benches,
	generate_command_cache,
	migrate_env,
	renew_lets_encrypt,
	restart,
	set_mariadb_host,
	set_nginx_port,
	set_redis_cache_host,
	set_redis_queue_host,
	set_redis_socketio_host,
	set_ssl_certificate,
	set_ssl_certificate_key,
	set_url_root,
	start,
)

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
bench_command.add_command(download_translations)
bench_command.add_command(backup_all_sites)
bench_command.add_command(renew_lets_encrypt)
bench_command.add_command(disable_production)
bench_command.add_command(bench_src)
bench_command.add_command(find_benches)
bench_command.add_command(migrate_env)
bench_command.add_command(generate_command_cache)
bench_command.add_command(clear_command_cache)

from bench.commands.setup import setup

bench_command.add_command(setup)


from bench.commands.config import config

bench_command.add_command(config)

from bench.commands.git import remote_reset_url, remote_set_url, remote_urls

bench_command.add_command(remote_set_url)
bench_command.add_command(remote_reset_url)
bench_command.add_command(remote_urls)

from bench.commands.install import install

bench_command.add_command(install)
