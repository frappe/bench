import os, json, click
from bench.utils import get_sites, get_bench_name

def make_nginx_conf(bench_path, force=False):
	from bench import env
	from bench.config.common_site_config import get_config

	template = env.get_template('nginx.conf')
	bench_path = os.path.abspath(bench_path)
	sites_path = os.path.join(bench_path, "sites")

	config = get_config(bench_path)
	sites = prepare_sites(config, bench_path)

	nginx_conf = template.render(**{
		"sites_path": sites_path,
		"http_timeout": config.get("http_timeout"),
		"sites": sites,
		"webserver_port": config.get('webserver_port'),
		"socketio_port": config.get('socketio_port'),
		"bench_name": get_bench_name(bench_path)
	})

	conf_path = os.path.join(bench_path, "config", "nginx.conf")
	if not force and os.path.exists(conf_path):
		click.confirm('nginx.conf already exists and this will overwrite it. Do you want to continue?',
			abort=True)

	with open(conf_path, "w") as f:
		f.write(nginx_conf)

def prepare_sites(config, bench_path):
	sites = {
		"that_use_dns": [],
		"that_use_ssl": [],
		"that_use_port": []
	}
	ports_in_use = {}
	dns_multitenant = config.get('dns_multitenant')

	for site in get_sites_with_config(bench_path=bench_path):
		if dns_multitenant:
			# assumes site's folder name is same as the domain name

			if site.get("ssl_certificate") and site.get("ssl_certificate_key"):
				sites["that_use_ssl"].append(site)

			else:
				sites["that_use_dns"].append(site["name"])

		else:
			if not site.get("port"):
				site["port"] = 80

			if site["port"] in ports_in_use:
				raise Exception("Port {0} is being used by another site {1}".format(site["port"], ports_in_use[site["port"]]))

			ports_in_use[site["port"]] = site["name"]
			sites["that_use_port"].append(site)

	return sites

def get_sites_with_config(bench_path):
	sites = get_sites(bench=bench_path)
	ret = []
	for site in sites:
		site_config = get_site_config(site, bench_path=bench_path)
		ret.append({
			"name": site,
			"port": site_config.get('nginx_port'),
			"ssl_certificate": site_config.get('ssl_certificate'),
			"ssl_certificate_key": site_config.get('ssl_certificate_key')
		})
	return ret

def get_site_config(site, bench_path='.'):
	with open(os.path.join(bench_path, 'sites', site, 'site_config.json')) as f:
		return json.load(f)
