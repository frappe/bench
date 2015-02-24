import os
import getpass
import json
import subprocess
from jinja2 import Environment, PackageLoader
from .utils import get_sites, get_config, update_config, get_redis_version

env = Environment(loader=PackageLoader('bench', 'templates'), trim_blocks=True)

def generate_supervisor_config(bench='.', user=None):
	from .app import get_current_frappe_version
	template = env.get_template('supervisor.conf')
	bench_dir = os.path.abspath(bench)
	sites_dir = os.path.join(bench_dir, "sites")
	sites = get_sites(bench=bench)
	if not user:
		user = getpass.getuser()
	config = get_config()

	config = template.render(**{
		"bench_dir": bench_dir,
		"sites_dir": sites_dir,
		"user": user,
		"http_timeout": config.get("http_timeout", 120),
		"redis_server": subprocess.check_output('which redis-server', shell=True).strip(),
		"redis_config": os.path.join(bench_dir, 'config', 'redis.conf'),
		"frappe_version": get_current_frappe_version()
	})
	with open("config/supervisor.conf", 'w') as f:
		f.write(config)
	update_config({'restart_supervisor_on_update': True})

def get_site_config(site, bench='.'):
	with open(os.path.join(bench, 'sites', site, 'site_config.json')) as f:
		return json.load(f)

def get_sites_with_config(bench='.'):
	sites = get_sites()
	ret = []
	for site in sites:
		site_config = get_site_config(site, bench=bench)
		ret.append({
			"name": site,
			"port": site_config.get('nginx_port'),
			"ssl_certificate": site_config.get('ssl_certificate'),
			"ssl_certificate_key": site_config.get('ssl_certificate_key')
		})
	return ret

def generate_nginx_config(bench='.'):
	template = env.get_template('nginx.conf')
	bench_dir = os.path.abspath(bench)
	sites_dir = os.path.join(bench_dir, "sites")
	sites = get_sites_with_config(bench=bench)
	user = getpass.getuser()

	if get_config().get('serve_default_site'):
		try:
			with open("sites/currentsite.txt") as f:
				default_site = {'name': f.read().strip()}
		except IOError:
			default_site = None
	else:
		default_site = None

	config = template.render(**{
		"sites_dir": sites_dir,
		"http_timeout": get_config().get("http_timeout", 120),
		"default_site": default_site,
		"dns_multitenant": get_config().get('dns_multitenant'),
		"sites": sites
	})
	with open("config/nginx.conf", 'w') as f:
		f.write(config)

def generate_redis_config(bench='.'):
	template = env.get_template('redis.conf')
	conf = {
		"maxmemory": get_config().get('cache_maxmemory', '50'),
		"port": get_config().get('redis_cache_port', '11311'),
		"redis_version": get_redis_version()
	}
	config = template.render(**conf)
	with open("config/redis.conf", 'w') as f:
		f.write(config)
