import click, sys, json

@click.group()
def setup():
	"Setup bench"
	pass


@click.command('sudoers')
@click.argument('user')
def setup_sudoers(user):
	"Add commands to sudoers list for execution without password"
	from bench.utils import setup_sudoers
	setup_sudoers(user)


@click.command('nginx')
@click.option('--yes', help='Yes to regeneration of nginx config file', default=False, is_flag=True)
def setup_nginx(yes=False):
	"generate config for nginx"
	from bench.config.nginx import make_nginx_conf
	make_nginx_conf(bench_path=".", yes=yes)

@click.command('reload-nginx')
def reload_nginx():
	from bench.config.production_setup import reload_nginx
	reload_nginx()

@click.command('supervisor')
@click.option('--user')
@click.option('--yes', help='Yes to regeneration of supervisor config', is_flag=True, default=False)
def setup_supervisor(user=None, yes=False):
	"generate config for supervisor with an optional user argument"
	from bench.config.supervisor import generate_supervisor_config
	generate_supervisor_config(bench_path=".", user=user, yes=yes)

@click.command('redis')
def setup_redis():
	"generate config for redis cache"
	from bench.config.redis import generate_config
	generate_config('.')


@click.command('fonts')
def setup_fonts():
	"Add frappe fonts to system"
	from bench.utils import setup_fonts
	setup_fonts()


@click.command('production')
@click.argument('user')
def setup_production(user):
	"setup bench for production"
	from bench.config.production_setup import setup_production
	setup_production(user=user)


@click.command('auto-update')
def setup_auto_update():
	"Add cronjob for bench auto update"
	from bench.utils import setup_auto_update
	setup_auto_update()


@click.command('backups')
def setup_backups():
	"Add cronjob for bench backups"
	from bench.utils import setup_backups
	setup_backups()

@click.command('env')
def setup_env():
	"Setup virtualenv for bench"
	from bench.utils import setup_env
	setup_env()


@click.command('lets-encrypt')
@click.argument('site')
def setup_letsencrypt(site):
	"Setup lets-encrypt for site"
	from bench.config.lets_encrypt import setup_letsencrypt
	setup_letsencrypt(site, bench_path='.')


@click.command('procfile')
def setup_procfile():
	"Setup Procfile for bench start"
	from bench.config.procfile import setup_procfile
	setup_procfile('.')


@click.command('socketio')
def setup_socketio():
	"Setup node deps for socketio server"
	from bench.utils import setup_socketio
	setup_socketio()


@click.command('config')
def setup_config():
	"overwrite or make config.json"
	from bench.config.common_site_config import make_config
	make_config('.')


@click.command('add-domain')
@click.argument('domain')
@click.option('--site', prompt=True)
@click.option('--ssl-certificate', help="Absolute path to SSL Certificate")
@click.option('--ssl-certificate-key', help="Absolute path to SSL Certificate Key")
def add_domain(domain, site=None, ssl_certificate=None, ssl_certificate_key=None):
	"""Add custom domain to site"""
	from bench.config.site_config import add_domain

	if not site:
		print "Please specify site"
		sys.exit(1)

	add_domain(site, domain, ssl_certificate, ssl_certificate_key, bench_path='.')

@click.command('remove-domain')
@click.argument('domain')
@click.option('--site', prompt=True)
def remove_domain(domain, site=None):
	"""Remove custom domain from a site"""
	from bench.config.site_config import remove_domain

	if not site:
		print "Please specify site"
		sys.exit(1)

	remove_domain(site, domain, bench_path='.')

@click.command('sync-domains')
@click.argument('domains')
@click.option('--site', prompt=True)
def sync_domains(domains, site=None):
	from bench.config.site_config import sync_domains

	if not site:
		print "Please specify site"
		sys.exit(1)

	domains = json.loads(domains)
	if not isinstance(domains, list):
		print "Domains should be a json list of strings or dictionaries"
		sys.exit(1)

	changed = sync_domains(site, domains, bench_path='.')

	# if changed, success, else failure
	sys.exit(0 if changed else 1)

setup.add_command(setup_sudoers)
setup.add_command(setup_nginx)
setup.add_command(reload_nginx)
setup.add_command(setup_supervisor)
setup.add_command(setup_redis)
setup.add_command(setup_letsencrypt)
setup.add_command(setup_production)
setup.add_command(setup_auto_update)
setup.add_command(setup_backups)
setup.add_command(setup_env)
setup.add_command(setup_procfile)
setup.add_command(setup_socketio)
setup.add_command(setup_config)
setup.add_command(setup_fonts)
setup.add_command(add_domain)
setup.add_command(remove_domain)
setup.add_command(sync_domains)
