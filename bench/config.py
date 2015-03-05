import os
import getpass
import json
import subprocess
import shutil
from jinja2 import Environment, PackageLoader
from .utils import get_sites, get_config, update_config, get_redis_version

env = Environment(loader=PackageLoader('bench', 'templates'), trim_blocks=True)

def write_config_file(bench, file_name, config):
	config_path = os.path.join(bench, 'config')
	file_path = os.path.join(config_path, file_name)
	number = (len([path for path in os.listdir(config_path) if path.startswith(file_name)]) -1 ) or ''
	if number:
		number = '.' + str(number)
	if os.path.exists(file_path):
		shutil.move(file_path, file_path + '.save' + number)

	with open(file_path, 'wb') as f:
		f.write(config)

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
	write_config_file(bench, 'supervisor.conf', config)
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
	write_config_file(bench, 'nginx.conf', config)

def generate_redis_config(bench='.'):
	template = env.get_template('redis.conf')
	conf = {
		"maxmemory": get_config().get('cache_maxmemory', '50'),
		"port": get_config().get('redis_cache_port', '11311'),
		"redis_version": get_redis_version()
	}
	config = template.render(**conf)
	write_config_file(bench, 'redis.conf', config)
