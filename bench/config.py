import os
import getpass
from jinja2 import Environment, PackageLoader
from .utils import get_sites

env = Environment(loader=PackageLoader('bench', 'templates'), trim_blocks=True)

def generate_config(application, template_name, bench='.'):
	template = env.get_template(template_name)
	bench_dir = os.path.abspath(bench)
	sites_dir = os.path.join(bench_dir, "sites")
	sites = get_sites(bench=bench)
	user = getpass.getuser()
	with open("sites/currentsite.txt") as f:
		default_site = f.read().strip()

	config = template.render(**{
		"bench_dir": bench_dir,
		"sites_dir": sites_dir,
		"user": user,
		"default_site": default_site,
		"sites": sites
	})
	with open("config/{}.conf".format(application), 'w') as f:
		f.write(config)
