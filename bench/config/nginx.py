import os, json, click, random, string, hashlib
from bench.utils import get_sites, get_bench_name, exec_cmd

def make_nginx_conf(bench_path, yes=False):
	from bench import env
	from bench.config.common_site_config import get_config

	template = env.get_template('nginx.conf')
	bench_path = os.path.abspath(bench_path)
	sites_path = os.path.join(bench_path, "sites")

	config = get_config(bench_path)
	sites = prepare_sites(config, bench_path)

	bench_name = get_bench_name(bench_path)
	bench_name_hash = hashlib.sha256(bench_name).hexdigest()[:16]

	nginx_conf = template.render(**{
		"sites_path": sites_path,
		"http_timeout": config.get("http_timeout"),
		"sites": sites,
		"webserver_port": config.get('webserver_port'),
		"socketio_port": config.get('socketio_port'),
		"bench_name": bench_name,
		"bench_name_hash": bench_name_hash,
		"limit_conn_shared_memory": get_limit_conn_shared_memory(),
		"error_pages": get_error_pages(),

		# for nginx map variable
		"random_string": "".join(random.choice(string.ascii_lowercase) for i in xrange(7))
	})

	conf_path = os.path.join(bench_path, "config", "nginx.conf")
	if not yes and os.path.exists(conf_path):
		click.confirm('nginx.conf already exists and this will overwrite it. Do you want to continue?',
			abort=True)

	with open(conf_path, "w") as f:
		f.write(nginx_conf)

def prepare_sites(config, bench_path):
	sites = {
		"that_use_port": [],
		"that_use_dns": [],
		"that_use_ssl": [],
		"that_use_wildcard_ssl": []
	}

	domain_map = {}
	ports_in_use = {}

	dns_multitenant = config.get('dns_multitenant')

	for site in get_sites_with_config(bench_path=bench_path):
		if dns_multitenant:
			domain = site.get('domain')

			if domain:
				# when site's folder name is different than domain name
				domain_map[domain] = site['name']

			site_name = domain or site['name']

			if site.get('wildcard'):
				sites["that_use_wildcard_ssl"].append(site_name)

				if not sites.get('wildcard_ssl_certificate'):
					sites["wildcard_ssl_certificate"] = site['ssl_certificate']
					sites["wildcard_ssl_certificate_key"] = site['ssl_certificate_key']

			elif site.get("ssl_certificate") and site.get("ssl_certificate_key"):
				sites["that_use_ssl"].append(site)

			else:
				sites["that_use_dns"].append(site_name)

		else:
			if not site.get("port"):
				site["port"] = 80

			if site["port"] in ports_in_use:
				raise Exception("Port {0} is being used by another site {1}".format(site["port"], ports_in_use[site["port"]]))

			ports_in_use[site["port"]] = site["name"]
			sites["that_use_port"].append(site)

	sites['domain_map'] = domain_map

	return sites

def get_sites_with_config(bench_path):
	from bench.config.common_site_config import get_config
	from bench.config.site_config import get_site_config

	sites = get_sites(bench_path=bench_path)
	dns_multitenant = get_config(bench_path).get('dns_multitenant')

	ret = []
	for site in sites:
		site_config = get_site_config(site, bench_path=bench_path)
		ret.append({
			"name": site,
			"port": site_config.get('nginx_port'),
			"ssl_certificate": site_config.get('ssl_certificate'),
			"ssl_certificate_key": site_config.get('ssl_certificate_key')
		})

		if dns_multitenant and site_config.get('domains'):
			for domain in site_config.get('domains'):
				# domain can be a string or a dict with 'domain', 'ssl_certificate', 'ssl_certificate_key'
				if isinstance(domain, basestring):
					domain = { 'domain': domain }

				domain['name'] = site
				ret.append(domain)

	use_wildcard_certificate(bench_path, ret)

	return ret

def use_wildcard_certificate(bench_path, ret):
	'''
		stored in common_site_config.json as:
	    "wildcard": {
			"domain": "*.erpnext.com",
			"ssl_certificate": "/path/to/erpnext.com.cert",
			"ssl_certificate_key": "/path/to/erpnext.com.key"
		}
	'''
	from bench.config.common_site_config import get_config
	config = get_config(bench_path=bench_path)
	wildcard = config.get('wildcard')

	if not wildcard:
		return

	domain = wildcard['domain']
	ssl_certificate = wildcard['ssl_certificate']
	ssl_certificate_key = wildcard['ssl_certificate_key']

	if domain.startswith('*.'):
		domain = domain[1:]
	else:
		domain = '.' + domain

	for site in ret:
		if site.get('ssl_certificate'):
			continue

		if (site.get('domain') or site['name']).endswith(domain):
			# example: ends with .erpnext.com
			site['ssl_certificate'] = ssl_certificate
			site['ssl_certificate_key'] = ssl_certificate_key
			site['wildcard'] = 1

def get_error_pages():
	import bench
	bench_app_path = os.path.abspath(bench.__path__[0])
	templates = os.path.join(bench_app_path, 'config', 'templates')

	return {
		502: os.path.join(templates, '502.html')
	}

def get_limit_conn_shared_memory():
	"""Allocate 2 percent of total virtual memory as shared memory for nginx limit_conn_zone"""
	import psutil
	total_vm = (psutil.virtual_memory().total) / (1024 * 1024) # in MB

	return int(0.02 * total_vm)
