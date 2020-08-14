# imports - standard imports
import hashlib
import os
import random
import string

# imports - third party imports
import click
from six import string_types

# imports - module imports
import bench
from bench.utils import get_bench_name, get_sites


def make_nginx_conf(bench_path, yes=False):
	conf_path = os.path.join(bench_path, "config", "nginx.conf")

	if not yes and os.path.exists(conf_path):
		if not click.confirm('nginx.conf already exists and this will overwrite it. Do you want to continue?'):
			return

	template = bench.config.env.get_template('nginx.conf')
	bench_path = os.path.abspath(bench_path)
	sites_path = os.path.join(bench_path, "sites")

	config = bench.config.common_site_config.get_config(bench_path)
	sites = prepare_sites(config, bench_path)
	bench_name = get_bench_name(bench_path)

	allow_rate_limiting = config.get('allow_rate_limiting', False)

	template_vars = {
		"sites_path": sites_path,
		"http_timeout": config.get("http_timeout"),
		"sites": sites,
		"webserver_port": config.get('webserver_port'),
		"socketio_port": config.get('socketio_port'),
		"bench_name": bench_name,
		"error_pages": get_error_pages(),
		"allow_rate_limiting": allow_rate_limiting,
		# for nginx map variable
		"random_string": "".join(random.choice(string.ascii_lowercase) for i in range(7))
	}

	if allow_rate_limiting:
		template_vars.update({
			'bench_name_hash': hashlib.sha256(bench_name).hexdigest()[:16],
			'limit_conn_shared_memory': get_limit_conn_shared_memory()
		})

	nginx_conf = template.render(**template_vars)


	with open(conf_path, "w") as f:
		f.write(nginx_conf)

def make_bench_manager_nginx_conf(bench_path, yes=False, port=23624, domain=None):
	from bench.config.site_config import get_site_config
	from bench.config.common_site_config import get_config

	template = bench.config.env.get_template('bench_manager_nginx.conf')
	bench_path = os.path.abspath(bench_path)
	sites_path = os.path.join(bench_path, "sites")

	config = get_config(bench_path)
	site_config = get_site_config(domain, bench_path=bench_path)
	bench_name = get_bench_name(bench_path)

	template_vars = {
		"port": port,
		"domain": domain,
		"bench_manager_site_name": "bench-manager.local",
		"sites_path": sites_path,
		"http_timeout": config.get("http_timeout"),
		"webserver_port": config.get('webserver_port'),
		"socketio_port": config.get('socketio_port'),
		"bench_name": bench_name,
		"error_pages": get_error_pages(),
		"ssl_certificate": site_config.get('ssl_certificate'),
		"ssl_certificate_key": site_config.get('ssl_certificate_key')
	}

	bench_manager_nginx_conf = template.render(**template_vars)

	conf_path = os.path.join(bench_path, "config", "nginx.conf")

	if not yes and os.path.exists(conf_path):
		click.confirm('nginx.conf already exists and bench-manager configuration will be appended to it. Do you want to continue?',
			abort=True)

	with open(conf_path, "a") as myfile:
		myfile.write(bench_manager_nginx_conf)

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

	shared_port_exception_found = False
	sites_configs = get_sites_with_config(bench_path=bench_path)

	if config.get("cors_config"):
		# copy cors_config from common_site_config
		config["cors_config"] = parse_cors_config(config.get("cors_config"))
		for site in sites_configs:
			if not site.get("cors_config"):
				site["cors_config"] = config.get("cors_config")

	# preload all preset site ports to avoid conflicts

	if not dns_multitenant:
		for site in sites_configs:
			if site.get("port"):
				if not site["port"] in ports_in_use:
					ports_in_use[site["port"]] = []
				ports_in_use[site["port"]].append(site["name"])

	for site in sites_configs:
		if dns_multitenant:
			domain = site.get('domain')

			if domain:
				# when site's folder name is different than domain name
				domain_map[domain] = site['name']

			site['site_name'] = domain or site['name']

			if site.get('wildcard'):
				sites["that_use_wildcard_ssl"].append(site)

				if not sites.get('wildcard_ssl_certificate'):
					sites["wildcard_ssl_certificate"] = site['ssl_certificate']
					sites["wildcard_ssl_certificate_key"] = site['ssl_certificate_key']

			elif site.get("ssl_certificate") and site.get("ssl_certificate_key"):
				sites["that_use_ssl"].append(site)

			else:
				sites["that_use_dns"].append(site)

		else:
			if not site.get("port"):
				site["port"] = 80
				if site["port"] in ports_in_use:
					site["port"] = 8001
				while site["port"] in ports_in_use:
					site["port"] += 1

			if site["port"] in ports_in_use and not site["name"] in ports_in_use[site["port"]]:
				shared_port_exception_found = True
				ports_in_use[site["port"]].append(site["name"])
			else:
				ports_in_use[site["port"]] = []
				ports_in_use[site["port"]].append(site["name"])

			sites["that_use_port"].append(site)


	if not dns_multitenant and shared_port_exception_found:
		message = "Port conflicts found:"
		port_conflict_index = 0
		for port_number in ports_in_use:
			if len(ports_in_use[port_number]) > 1:
				port_conflict_index += 1
				message += "\n{0} - Port {1} is shared among sites:".format(port_conflict_index,port_number)
				for site_name in ports_in_use[port_number]:
					message += " {0}".format(site_name)
		raise Exception(message)

	if not dns_multitenant:
		message = "Port configuration list:"
		for site in sites_configs:
			message += "\n\nSite {0} assigned port: {1}".format(site["name"], site["port"])

		print(message)

	# Consolidate CORS configs
	if dns_multitenant:
		sites["that_use_wildcard_ssl"] = merge_cors_configs(sites["that_use_wildcard_ssl"])
		sites["that_use_dns"] = merge_cors_configs(sites["that_use_dns"])

	sites['domain_map'] = domain_map

	return sites

def get_sites_with_config(bench_path):
	from bench.config.common_site_config import get_config
	from bench.config.site_config import get_site_config

	sites = get_sites(bench_path=bench_path)
	dns_multitenant = get_config(bench_path).get('dns_multitenant')

	ret = []
	for site in sites:
		try:
			site_config = get_site_config(site, bench_path=bench_path)
		except Exception as e:
			strict_nginx = get_config(bench_path).get('strict_nginx')
			if strict_nginx:
				print("\n\nERROR: The site config for the site {} is broken.".format(site),
					"If you want this command to pass, instead of just throwing an error,",
					"You may remove the 'strict_nginx' flag from common_site_config.json or set it to 0",
					"\n\n")
				raise (e)
			else:
				print("\n\nWARNING: The site config for the site {} is broken.".format(site),
					"If you want this command to fail, instead of just showing a warning,",
					"You may add the 'strict_nginx' flag to common_site_config.json and set it to 1",
					"\n\n")
				continue

		ret.append({
			"name": site,
			"port": site_config.get('nginx_port'),
			"ssl_certificate": site_config.get('ssl_certificate'),
			"ssl_certificate_key": site_config.get('ssl_certificate_key'),
			"cors_config": parse_cors_config(site_config.get("cors_config", None))
		})

		if dns_multitenant and site_config.get('domains'):
			for domain in site_config.get('domains'):
				# domain can be a string or a dict with 'domain', 'ssl_certificate', 'ssl_certificate_key'
				if isinstance(domain, string_types):
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

	# If domain is set as "*" all domains will be included
	if domain.startswith('*'):
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
	total_vm = (os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')) / (1024 * 1024) # in MB

	return int(0.02 * total_vm)

def parse_cors_config(cors_config):
	if not cors_config:
		return cors_config

	parsed_config = {
		"random_string": "".join(random.choice(string.ascii_lowercase) for i in range(7)),
		"allow_credentials": {},
		"headers": {},
		"methods": {},
		"max_age": {},
		"expose_headers": {},
		"origins": {}
	}

	for origin, config in cors_config.items():
		if not config.get("enabled"):
			continue
		
		parsed_config["origins"][origin] = origin
		for prop in ("allow_credentials", "headers", "methods", "max_age", "expose_headers"):
			if not config.get(prop):
				continue
			v = config.get(prop)
			if isinstance(v, list):
				v = ", ".join(v)
			elif prop == "allow_credentials":
				v = "true" if v else "false"
			parsed_config[prop][origin] = v

		if not parsed_config["max_age"].get(origin):
			parsed_config["max_age"][origin] = 864000

	return parsed_config

def merge_cors_configs(sites):
	merged_sites = []

	def _compare(obj1, obj2):
		"""Custom object deep-value comparison"""
		if not obj1 and not obj2:
			return True
		elif not obj1 or not obj2:
			return False
		elif type(obj1) != type(obj2):
			return False
		
		if isinstance(obj1, dict):
			k1 = obj1.keys()
			k2 = obj2.keys()
			if len(k1) != len(k2) or set(k1) != set(k2):
				return False
			for k, v in obj1.items():
				if k == "random_string":
					continue
				if not _compare(v, obj2[k]):
					return False
			return True
		elif isinstance(obj1, (list, tuple)):
			return set(obj1) == set(obj2)
		else:
			return obj1 == obj2

	for s in sites:
		merged = False
		for _site in merged_sites:
			if not _compare(s.get("cors_config", None), _site.get("cors_config", None)):
				continue
			
			_site["server_names"].append(s["site_name"])
			merged = True
			break

		if not merged:
			merged_sites.append({
				"server_names": [s["site_name"]],
				"cors_config": s.get("cors_config", None)
			})
	
	return merged_sites