# imports - standard imports
import os

# imports - third party imports
import click


@click.command("start", help="Start Frappe development processes")
@click.option("--no-dev", is_flag=True, default=False)
@click.option(
	"--no-prefix",
	is_flag=True,
	default=False,
	help="Hide process name from bench start log",
)
@click.option("--concurrency", "-c", type=str)
@click.option("--procfile", "-p", type=str)
@click.option("--man", "-m", help="Process Manager of your choice ;)")
def start(no_dev, concurrency, procfile, no_prefix, man):
	from bench.utils.system import start

	start(
		no_dev=no_dev,
		concurrency=concurrency,
		procfile=procfile,
		no_prefix=no_prefix,
		procman=man,
	)


@click.command("restart", help="Restart supervisor processes or systemd units")
@click.option("--web", is_flag=True, default=False)
@click.option("--supervisor", is_flag=True, default=False)
@click.option("--systemd", is_flag=True, default=False)
def restart(web, supervisor, systemd):
	from bench.bench import Bench

	if not systemd and not web:
		supervisor = True

	Bench(".").reload(web, supervisor, systemd)


@click.command("set-nginx-port", help="Set NGINX port for site")
@click.argument("site")
@click.argument("port", type=int)
def set_nginx_port(site, port):
	from bench.config.site_config import set_nginx_port

	set_nginx_port(site, port)


@click.command("set-ssl-certificate", help="Set SSL certificate path for site")
@click.argument("site")
@click.argument("ssl-certificate-path")
def set_ssl_certificate(site, ssl_certificate_path):
	from bench.config.site_config import set_ssl_certificate

	set_ssl_certificate(site, ssl_certificate_path)


@click.command("set-ssl-key", help="Set SSL certificate private key path for site")
@click.argument("site")
@click.argument("ssl-certificate-key-path")
def set_ssl_certificate_key(site, ssl_certificate_key_path):
	from bench.config.site_config import set_ssl_certificate_key

	set_ssl_certificate_key(site, ssl_certificate_key_path)


@click.command("set-url-root", help="Set URL root for site")
@click.argument("site")
@click.argument("url-root")
def set_url_root(site, url_root):
	from bench.config.site_config import set_url_root

	set_url_root(site, url_root)


@click.command("set-mariadb-host", help="Set MariaDB host for bench")
@click.argument("host")
def set_mariadb_host(host):
	from bench.utils.bench import set_mariadb_host

	set_mariadb_host(host)


@click.command("set-redis-cache-host", help="Set Redis cache host for bench")
@click.argument("host")
def set_redis_cache_host(host):
	"""
	Usage: bench set-redis-cache-host localhost:6379/1
	"""
	from bench.utils.bench import set_redis_cache_host

	set_redis_cache_host(host)


@click.command("set-redis-queue-host", help="Set Redis queue host for bench")
@click.argument("host")
def set_redis_queue_host(host):
	"""
	Usage: bench set-redis-queue-host localhost:6379/2
	"""
	from bench.utils.bench import set_redis_queue_host

	set_redis_queue_host(host)


@click.command("set-redis-socketio-host", help="Set Redis socketio host for bench")
@click.argument("host")
def set_redis_socketio_host(host):
	"""
	Usage: bench set-redis-socketio-host localhost:6379/3
	"""
	from bench.utils.bench import set_redis_socketio_host

	set_redis_socketio_host(host)


@click.command("download-translations", help="Download latest translations")
def download_translations():
	from bench.utils.translation import download_translations_p

	download_translations_p()


@click.command(
	"renew-lets-encrypt", help="Sets Up latest cron and Renew Let's Encrypt certificate"
)
def renew_lets_encrypt():
	from bench.config.lets_encrypt import renew_certs

	renew_certs()


@click.command("backup-all-sites", help="Backup all sites in current bench")
def backup_all_sites():
	from bench.utils.system import backup_all_sites

	backup_all_sites(bench_path=".")


@click.command(
	"disable-production", help="Disables production environment for the bench."
)
def disable_production():
	from bench.config.production_setup import disable_production

	disable_production(bench_path=".")


@click.command(
	"src", help="Prints bench source folder path, which can be used as: cd `bench src`"
)
def bench_src():
	from bench.cli import src

	print(os.path.dirname(src))


@click.command("find", help="Finds benches recursively from location")
@click.argument("location", default="")
def find_benches(location):
	from bench.utils import find_benches

	find_benches(directory=location)


@click.command(
	"migrate-env", help="Migrate Virtual Environment to desired Python Version"
)
@click.argument("python", type=str)
@click.option("--no-backup", "backup", is_flag=True, default=True)
def migrate_env(python, backup=True):
	from bench.utils.bench import migrate_env

	migrate_env(python=python, backup=backup)


@click.command("app-cache", help="View or remove items belonging to bench get-app cache")
@click.option("--clear", is_flag=True, default=False, help="Remove all items")
@click.option(
	"--remove-app",
	default="",
	help="Removes all items that match provided app name",
)
@click.option(
	"--remove-key",
	default="",
	help="Removes all items that matches provided cache key",
)
def app_cache_helper(clear=False, remove_app="", remove_key=""):
	from bench.utils.bench import cache_helper

	cache_helper(clear, remove_app, remove_key)


from pathlib import Path
from typing import List, Tuple
import click
import re
from bench.utils import get_bench_name

LISTEN_PORT_RE = re.compile(
    r'\blisten\b\s+(?:\[[^\]]+\]:|[0-9a-zA-Z\.\-]+:)?(?P<port>\d+)', re.IGNORECASE
)


@click.command("show-ports", help="Show which sites are configured on which ports")
@click.option("--site", "-s", required=False, help="Filter by site name")
def show_ports(site: str = None):
    """Show which sites are configured on which ports (safe, linear scan)."""
    bench_path = Path(os.getcwd())
    conf_path = bench_path / "config" / "nginx.conf"

    if not conf_path.exists():
        click.echo("No nginx.conf found. Try running `bench setup nginx` first.")
        return

    try:
        bench_name = get_bench_name(str(bench_path))
    except Exception:
        bench_name = "<unknown>"

    sites_ports: List[Tuple[str, int]] = []
    in_server_block = False
    current_names: List[str] = []
    current_listens: List[int] = []

    with conf_path.open("r", encoding="utf-8", errors="ignore") as fh:
        lines_iter = iter(fh)
        for raw in lines_iter:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("server") and "{" in line:
                in_server_block = True
                current_names.clear()
                current_listens.clear()
                continue

            if not in_server_block:
                continue

            if "listen" in line:
                m = LISTEN_PORT_RE.search(line)
                if m:
                    try:
                        current_listens.append(int(m.group("port")))
                    except (ValueError, TypeError):
                        pass

            if "server_name" in line:
                after = line.split("server_name", 1)[1]
                buf = after
                while ";" not in buf:
                    try:
                        buf += " " + next(lines_iter).strip()
                    except StopIteration:
                        break
                name_segment = buf.split(";", 1)[0].strip()
                if name_segment:
                    tokens = name_segment.split()
                    current_names.extend(t.strip() for t in tokens if t.strip())

            if "}" in line:
                names_to_use = current_names or ["<no server_name>"]
                for n in names_to_use:
                    for p in current_listens:
                        if (n, p) not in sites_ports:
                            sites_ports.append((n, p))
                in_server_block = False
                current_names.clear()
                current_listens.clear()

    if site:
        sites_ports = [(n, p) for (n, p) in sites_ports if n == site]

    if not sites_ports:
        click.echo("No matching sites/ports found in nginx.conf")
        return

    out_lines = [f"Site {n} → Port {p}" for (n, p) in sites_ports]
    click.echo(f"Bench {bench_name} sites and ports:\n" + "\n".join(out_lines))
