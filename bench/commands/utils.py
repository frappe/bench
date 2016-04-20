import click
import sys, os, copy


@click.command('start')
@click.option('--no-dev', is_flag=True, default=False)
@click.option('--concurrency', '-c', type=str)
def start(no_dev, concurrency):
	"Start Frappe development processes"
	from bench.utils import start
	start(no_dev=no_dev, concurrency=concurrency)


@click.command('restart')
def restart():
	"Restart supervisor processes"
	from bench.utils import restart_supervisor_processes
	restart_supervisor_processes()


@click.command('set-nginx-port')
@click.argument('site')
@click.argument('port', type=int)
def set_nginx_port(site, port):
	"Set nginx port for site"
	from bench.utils import set_nginx_port
	set_nginx_port(site, port)


@click.command('set-ssl-certificate')
@click.argument('site')
@click.argument('ssl-certificate-path')
def set_ssl_certificate(site, ssl_certificate_path):
	"Set ssl certificate path for site"
	from bench.utils import set_ssl_certificate
	set_ssl_certificate(site, ssl_certificate_path)


@click.command('set-ssl-key')
@click.argument('site')
@click.argument('ssl-certificate-key-path')
def set_ssl_certificate_key(site, ssl_certificate_key_path):
	"Set ssl certificate private key path for site"
	from bench.utils import set_ssl_certificate_key
	set_ssl_certificate_key(site, ssl_certificate_key_path)


@click.command('set-url-root')
@click.argument('site')
@click.argument('url-root')
def set_url_root(site, url_root):
	"Set url root for site"
	from bench.utils import set_url_root
	set_url_root(site, url_root)


@click.command('set-mariadb-host')
@click.argument('host')
def set_mariadb_host(host):
	"Set MariaDB host for bench"
	from bench.utils import set_mariadb_host
	set_mariadb_host(host)


@click.command('set-default-site')
@click.argument('site')
def set_default_site(site):
	"Set default site for bench"
	from bench.utils import set_default_site
	set_default_site(site)


@click.command('download-translations')
def download_translations():
	"Download latest translations"
	from bench.utils import download_translations_p
	download_translations_p()


@click.command()
def shell(bench='.'):
	if not os.environ.get('SHELL'):
		print "Cannot get shell"
		sys.exit(1)
	if not os.path.exists('sites'):
		print "sites dir doesn't exist"
		sys.exit(1)
	env = copy.copy(os.environ)
	env['PS1'] = '(' + os.path.basename(os.path.dirname(os.path.abspath(__file__))) + ')' + env.get('PS1', '')
	env['PATH'] = os.path.dirname(os.path.abspath(os.path.join('env','bin')) + ':' + env['PATH'])
	os.chdir('sites')
	os.execve(env['SHELL'], [env['SHELL']], env)


@click.command('backup')
@click.argument('site')
def backup_site(site):
	"backup site"
	from bench.utils import get_sites, backup_site
	if not site in get_sites(bench='.'):
		print 'site not found'
		sys.exit(1)
	backup_site(site, bench='.')


@click.command('backup-all-sites')
def backup_all_sites():
	"backup all sites"
	from bench.utils import backup_all_sites
	backup_all_sites(bench='.')


@click.command('release')
@click.argument('app', type=click.Choice(['frappe', 'erpnext', 'erpnext_shopify', 'paypal_integration', 'schools']))
@click.argument('bump-type', type=click.Choice(['major', 'minor', 'patch']))
@click.option('--develop', default='develop')
@click.option('--master', default='master')
def release(app, bump_type, develop, master):
	"Release app (internal to the Frappe team)"
	from bench.release import release
	repo = os.path.join('apps', app)
	release(repo, bump_type, develop, master)

