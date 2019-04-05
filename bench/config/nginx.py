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

	conf_path = os.path.join(bench_path, "config", "nginx.conf")
	if not yes and os.path.exists(conf_path):
		click.confirm('nginx.conf already exists and this will overwrite it. Do you want to continue?',
			abort=True)

	with open(conf_path, "w") as f:
		f.write(nginx_conf)

def make_bench_manager_nginx_conf(bench_path, yes=False, port=23624, domain=None):
	from bench import env
	from bench.config.site_config import get_site_config
	from bench.config.common_site_config import get_config

	template = env.get_template('bench_manager_nginx.conf')
	bench_path = os.path.abspath(bench_path)
	sites_path = os.path.join(bench_path, "sites")

	config = get_config(bench_path)
	site_config = get_site_config(domain, bench_path=bench_path)
	sites = prepare_sites(config, bench_path)
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
					site["port"] = 8001
				while site["port"] in ports_in_use:
					site["port"] += 1

#			if site["port"] in ports_in_use:
#				raise Exception("Port {0} is being used by another site {1}".format(site["port"], ports_in_use[site["port"]]))

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
		port_config_index = 0
		for site in sites_configs:
			port_config_index += 1
			message += "\n\nSite {0} assigned port: {1}".format(site["name"], site["port"])

		print(message)


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
			"ssl_certificate_key": site_config.get('ssl_certificate_key')
		})

		if dns_multitenant and site_config.get('domains'):
			for domain in site_config.get('domains'):
				# domain can be a string or a dict with 'domain', 'ssl_certificate', 'ssl_certificate_key'
				if isinstance(domain, str) or isinstance(domain, unicode):
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
