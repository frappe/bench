# imports - standard imports
import os
import sys

# imports - third party imports
import click


@click.command('start', help="Start Frappe development processes")
@click.option('--no-dev', is_flag=True, default=False)
@click.option('--no-prefix', is_flag=True, default=False, help="Hide process name from bench start log")
@click.option('--concurrency', '-c', type=str)
@click.option('--procfile', '-p', type=str)
def start(no_dev, concurrency, procfile, no_prefix):
	from bench.utils import start
	start(no_dev=no_dev, concurrency=concurrency, procfile=procfile, no_prefix=no_prefix)


@click.command('restart', help="Restart supervisor processes or systemd units")
@click.option('--web', is_flag=True, default=False)
@click.option('--supervisor', is_flag=True, default=False)
@click.option('--systemd', is_flag=True, default=False)
def restart(web, supervisor, systemd):
	from bench.utils import restart_supervisor_processes, restart_systemd_processes
	from bench.config.common_site_config import get_config
	if get_config('.').get('restart_supervisor_on_update') or supervisor:
		restart_supervisor_processes(bench_path='.', web_workers=web)
	if get_config('.').get('restart_systemd_on_update') or systemd:
		restart_systemd_processes(bench_path='.', web_workers=web)


@click.command('set-nginx-port', help="Set NGINX port for site")
@click.argument('site')
@click.argument('port', type=int)
def set_nginx_port(site, port):
	from bench.config.site_config import set_nginx_port
	set_nginx_port(site, port)


@click.command('set-ssl-certificate', help="Set SSL certificate path for site")
@click.argument('site')
@click.argument('ssl-certificate-path')
def set_ssl_certificate(site, ssl_certificate_path):
	from bench.config.site_config import set_ssl_certificate
	set_ssl_certificate(site, ssl_certificate_path)


@click.command('set-ssl-key', help="Set SSL certificate private key path for site")
@click.argument('site')
@click.argument('ssl-certificate-key-path')
def set_ssl_certificate_key(site, ssl_certificate_key_path):
	from bench.config.site_config import set_ssl_certificate_key
	set_ssl_certificate_key(site, ssl_certificate_key_path)


@click.command('set-url-root', help="Set URL root for site")
@click.argument('site')
@click.argument('url-root')
def set_url_root(site, url_root):
	from bench.config.site_config import set_url_root
	set_url_root(site, url_root)


@click.command('set-mariadb-host', help="Set MariaDB host for bench")
@click.argument('host')
def set_mariadb_host(host):
	from bench.utils import set_mariadb_host
	set_mariadb_host(host)


@click.command('set-redis-cache-host', help="Set Redis cache host for bench")
@click.argument('host')
def set_redis_cache_host(host):
	"""
	Usage: bench set-redis-cache-host localhost:6379/1
	"""
	from bench.utils import set_redis_cache_host
	set_redis_cache_host(host)


@click.command('set-redis-queue-host', help="Set Redis queue host for bench")
@click.argument('host')
def set_redis_queue_host(host):
	"""
	Usage: bench set-redis-queue-host localhost:6379/2
	"""
	from bench.utils import set_redis_queue_host
	set_redis_queue_host(host)


@click.command('set-redis-socketio-host', help="Set Redis socketio host for bench")
@click.argument('host')
def set_redis_socketio_host(host):
	"""
	Usage: bench set-redis-socketio-host localhost:6379/3
	"""
	from bench.utils import set_redis_socketio_host
	set_redis_socketio_host(host)


@click.command('set-default-site', help="Set default site for bench")
@click.argument('site')
def set_default_site(site):
	from bench.utils import set_default_site
	set_default_site(site)


@click.command('download-translations', help="Download latest translations")
def download_translations():
	from bench.utils import download_translations_p
	download_translations_p()


@click.command('renew-lets-encrypt', help="Renew Let's Encrypt certificate")
def renew_lets_encrypt():
	from bench.config.lets_encrypt import renew_certs
	renew_certs()


@click.command('backup', help="Backup single site")
@click.argument('site')
def backup_site(site):
	from bench.utils import get_sites, backup_site
	if site not in get_sites(bench_path='.'):
		print('Site `{0}` not found'.format(site))
		sys.exit(1)
	backup_site(site, bench_path='.')


@click.command('backup-all-sites', help="Backup all sites in current bench")
def backup_all_sites():
	from bench.utils import backup_all_sites
	backup_all_sites(bench_path='.')


@click.command('release', help="Release a Frappe app (internal to the Frappe team)")
@click.argument('app')
@click.argument('bump-type', type=click.Choice(['major', 'minor', 'patch', 'stable', 'prerelease']))
@click.option('--from-branch', default='develop')
@click.option('--to-branch', default='master')
@click.option('--remote', default='upstream')
@click.option('--owner', default='frappe')
@click.option('--repo-name')
@click.option('--dont-frontport', is_flag=True, default=False, help='Front port fixes to new branches, example merging hotfix(v10) into staging-fixes(v11)')
def release(app, bump_type, from_branch, to_branch, owner, repo_name, remote, dont_frontport):
	from bench.release import release
	frontport = not dont_frontport
	release(bench_path='.', app=app, bump_type=bump_type, from_branch=from_branch, to_branch=to_branch, remote=remote, owner=owner, repo_name=repo_name, frontport=frontport)


@click.command('prepare-beta-release', help="Prepare major beta release from develop branch")
@click.argument('app')
@click.option('--owner', default='frappe')
def prepare_beta_release(app, owner):
	from bench.prepare_beta_release import prepare_beta_release
	prepare_beta_release(bench_path='.', app=app, owner=owner)


@click.command('disable-production', help="Disables production environment for the bench.")
def disable_production():
	from bench.config.production_setup import disable_production
	disable_production(bench_path='.')


@click.command('src', help="Prints bench source folder path, which can be used as: cd `bench src`")
def bench_src():
	from bench.cli import src
	print(os.path.dirname(src))


@click.command('find', help="Finds benches recursively from location")
@click.argument('location', default='')
def find_benches(location):
	from bench.utils import find_benches
	find_benches(directory=location)


@click.command('migrate-env', help="Migrate Virtual Environment to desired Python Version")
@click.argument('python', type=str)
@click.option('--no-backup', 'backup', is_flag=True, default=True)
def migrate_env(python, backup=True):
	from bench.utils import migrate_env
	migrate_env(python=python, backup=backup)


@click.command('generate-command-cache', help="Caches Frappe Framework commands")
def generate_command_cache(bench_path='.'):
	from bench.utils import generate_command_cache
	return generate_command_cache(bench_path=bench_path)


@click.command('clear-command-cache', help="Clears Frappe Framework cached commands")
def clear_command_cache(bench_path='.'):
	from bench.utils import clear_command_cache
	return clear_command_cache(bench_path=bench_path)
