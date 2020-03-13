# imports - standard imports
import os
import sys

# imports - module imports
from bench.utils import exec_cmd

# imports - third party imports
from six import PY3
import click


@click.group(help="Setup command group for enabling setting up a Frappe environment")
def setup():
	pass


@click.command("sudoers", help="Add commands to sudoers list for execution without password")
@click.argument("user")
def setup_sudoers(user):
	from bench.utils import setup_sudoers
	setup_sudoers(user)


@click.command("nginx", help="Generate configuration files for NGINX")
@click.option("--yes", help="Yes to regeneration of nginx config file", default=False, is_flag=True)
def setup_nginx(yes=False):
	from bench.config.nginx import make_nginx_conf
	make_nginx_conf(bench_path=".", yes=yes)


@click.command("reload-nginx", help="Checks NGINX config file and reloads service")
def reload_nginx():
	from bench.config.production_setup import reload_nginx
	reload_nginx()


@click.command("supervisor", help="Generate configuration for supervisor")
@click.option("--user", help="optional user argument")
@click.option("--yes", help="Yes to regeneration of supervisor config", is_flag=True, default=False)
def setup_supervisor(user=None, yes=False):
	from bench.config.supervisor import generate_supervisor_config
	generate_supervisor_config(bench_path=".", user=user, yes=yes)


@click.command("redis", help="Generates configuration for Redis")
def setup_redis():
	from bench.config.redis import generate_config
	generate_config(".")


@click.command("fonts", help="Add Frappe fonts to system")
def setup_fonts():
	from bench.utils import setup_fonts
	setup_fonts()


@click.command("production", help="Setup Frappe production environment for specific user")
@click.argument("user")
@click.option("--yes", help="Yes to regeneration config", is_flag=True, default=False)
def setup_production(user, yes=False):
	from bench.config.production_setup import setup_production
	# Install prereqs for production
	from distutils.spawn import find_executable
	if not find_executable("ansible"):
		exec_cmd("sudo -H {0} -m pip install ansible".format(sys.executable))
	if not find_executable("fail2ban-client"):
		exec_cmd("bench setup role fail2ban")
	if not find_executable("nginx"):
		exec_cmd("bench setup role nginx")
	if not find_executable("supervisord"):
		exec_cmd("bench setup role supervisor")
	setup_production(user=user, yes=yes)


@click.command("backups", help="Add cronjob for bench backups")
def setup_backups():
	from bench.utils import setup_backups
	setup_backups()


@click.command("env", help="Setup virtualenv for bench")
@click.option("--python", type = str, default = "python3", help = "Path to Python Executable.")
def setup_env(python="python3"):
	from bench.utils import setup_env
	setup_env(python=python)


@click.command("firewall", help="Setup firewall for system")
@click.option("--ssh_port")
@click.option("--force")
def setup_firewall(ssh_port=None, force=False):
	from bench.utils import run_playbook

	if not force:
		click.confirm("Setting up the firewall will block all ports except 80, 443 and {0}\nDo you want to continue?".format(ssh_port), abort=True)

	if not ssh_port:
		ssh_port = 22

	run_playbook("roles/bench/tasks/setup_firewall.yml", {"ssh_port": ssh_port})


@click.command("ssh-port", help="Set SSH Port for system")
@click.argument("port")
@click.option("--force")
def set_ssh_port(port, force=False):
	from bench.utils import run_playbook

	if not force:
		click.confirm("This will change your SSH Port to {}\nDo you want to continue?".format(port), abort=True)

	run_playbook("roles/bench/tasks/change_ssh_port.yml", {"ssh_port": port})


@click.command("lets-encrypt", help="Setup lets-encrypt SSL for site")
@click.argument("site")
@click.option("--custom-domain")
@click.option('-n', '--non-interactive', default=False, is_flag=True, help="Run command non-interactively. This flag restarts nginx and runs certbot non interactively. Shouldn't be used on 1'st attempt")
def setup_letsencrypt(site, custom_domain, non_interactive):
	from bench.config.lets_encrypt import setup_letsencrypt
	setup_letsencrypt(site, custom_domain, bench_path=".", interactive=not non_interactive)


@click.command("wildcard-ssl", help="Setup wildcard SSL certificate for multi-tenant bench")
@click.argument("domain")
@click.option("--email")
@click.option("--exclude-base-domain", default=False, is_flag=True, help="SSL Certificate not applicable for base domain")
def setup_wildcard_ssl(domain, email, exclude_base_domain):
	from bench.config.lets_encrypt import setup_wildcard_ssl
	setup_wildcard_ssl(domain, email, bench_path=".", exclude_base_domain=exclude_base_domain)


@click.command("procfile", help="Generate Procfile for bench start")
def setup_procfile():
	from bench.config.procfile import setup_procfile
	setup_procfile(".")


@click.command("socketio", help="Setup node dependencies for socketio server")
def setup_socketio():
	from bench.utils import setup_socketio
	setup_socketio()


@click.command("requirements", help="Setup Python and Node dependencies")
@click.option("--node", help="Update only Node packages", default=False, is_flag=True)
@click.option("--python", help="Update only Python packages", default=False, is_flag=True)
def setup_requirements(node=False, python=False):
	if not node:
		from bench.utils import update_requirements as setup_python_packages
		setup_python_packages()

	if not python:
		from bench.utils import update_node_packages as setup_node_packages
		setup_node_packages()


@click.command("manager", help="Setup bench-manager.local site with the bench_manager app installed on it")
@click.option("--yes", help="Yes to regeneration of nginx config file", default=False, is_flag=True)
@click.option("--port", help="Port on which you want to run bench manager", default=23624)
@click.option("--domain", help="Domain on which you want to run bench manager")
def setup_manager(yes=False, port=23624, domain=None):
	from six.moves import input
	from bench.utils import get_sites
	from bench.config.common_site_config import get_config
	from bench.config.nginx import make_bench_manager_nginx_conf

	create_new_site = True

	if "bench-manager.local" in os.listdir("sites"):
		ans = input("Site already exists. Overwrite existing site? [Y/n]: ").lower()
		while ans not in ("y", "n", ""):
			ans = input("Please enter 'y' or 'n'. Site already exists. Overwrite existing site? [Y/n]: ").lower()
		if ans == "n":
			create_new_site = False

	if create_new_site:
		exec_cmd("bench new-site --force bench-manager.local")

	if "bench_manager" in os.listdir("apps"):
		print("App already exists. Skipping app download.")
	else:
		exec_cmd("bench get-app bench_manager")

	exec_cmd("bench --site bench-manager.local install-app bench_manager")

	bench_path = "."
	conf = get_config(bench_path)

	if conf.get("restart_supervisor_on_update") or conf.get("restart_systemd_on_update"):
		# implicates a production setup or so I presume
		if not domain:
			print("Please specify the site name on which you want to host bench-manager using the 'domain' flag")
			sys.exit(1)

		if domain not in get_sites(bench_path):
			raise Exception("No such site")

		make_bench_manager_nginx_conf(bench_path, yes=yes, port=port, domain=domain)


@click.command("config", help="Generate or over-write sites/common_site_config.json")
def setup_config():
	from bench.config.common_site_config import make_config
	make_config(".")


@click.command("add-domain", help="Add a custom domain to a particular site")
@click.argument("domain")
@click.option("--site", prompt=True)
@click.option("--ssl-certificate", help="Absolute path to SSL Certificate")
@click.option("--ssl-certificate-key", help="Absolute path to SSL Certificate Key")
def add_domain(domain, site=None, ssl_certificate=None, ssl_certificate_key=None):
	"""Add custom domain to site"""
	from bench.config.site_config import add_domain

	if not site:
		print("Please specify site")
		sys.exit(1)

	add_domain(site, domain, ssl_certificate, ssl_certificate_key, bench_path=".")


@click.command("remove-domain", help="Remove custom domain from a site")
@click.argument("domain")
@click.option("--site", prompt=True)
def remove_domain(domain, site=None):
	from bench.config.site_config import remove_domain

	if not site:
		print("Please specify site")
		sys.exit(1)

	remove_domain(site, domain, bench_path=".")


@click.command("sync-domains", help="Check if there is a change in domains. If yes, updates the domains list.")
@click.option("--domain", multiple=True)
@click.option("--site", prompt=True)
def sync_domains(domain=None, site=None):
	from bench.config.site_config import sync_domains

	if not site:
		print("Please specify site")
		sys.exit(1)

	try:
		domains = list(map(str, domain))
	except Exception:
		print("Domains should be a json list of strings or dictionaries")
		sys.exit(1)

	changed = sync_domains(site, domains, bench_path=".")

	# if changed, success, else failure
	sys.exit(0 if changed else 1)


@click.command("role", help="Install dependencies via ansible roles")
@click.argument("role")
@click.option("--admin_emails", default="")
@click.option("--mysql_root_password")
@click.option("--container", is_flag=True, default=False)
def setup_roles(role, **kwargs):
	from bench.utils import run_playbook

	extra_vars = {"production": True}
	extra_vars.update(kwargs)

	if role:
		run_playbook("site.yml", extra_vars=extra_vars, tag=role)
	else:
		run_playbook("site.yml", extra_vars=extra_vars)


@click.command("fail2ban", help="Setup fail2ban, an intrusion prevention software framework that protects computer servers from brute-force attacks")
@click.option("--maxretry", default=6, help="Number of matches (i.e. value of the counter) which triggers ban action on the IP. Default is 6 seconds" )
@click.option("--bantime", default=600, help="The counter is set to zero if no match is found within 'findtime' seconds. Default is 600 seconds")
@click.option("--findtime", default=600, help="Duration (in seconds) for IP to be banned for. Negative number for 'permanent' ban. Default is 600 seconds")
def setup_nginx_proxy_jail(**kwargs):
	from bench.utils import run_playbook
	run_playbook("roles/fail2ban/tasks/configure_nginx_jail.yml", extra_vars=kwargs)


@click.command("systemd", help="Generate configuration for systemd")
@click.option("--user", help="Optional user argument")
@click.option("--yes", help="Yes to regeneration of systemd config files", is_flag=True, default=False)
@click.option("--stop", help="Stop bench services", is_flag=True, default=False)
@click.option("--create-symlinks", help="Create Symlinks", is_flag=True, default=False)
@click.option("--delete-symlinks", help="Delete Symlinks", is_flag=True, default=False)
def setup_systemd(user=None, yes=False, stop=False, create_symlinks=False, delete_symlinks=False):
	from bench.config.systemd import generate_systemd_config
	generate_systemd_config(bench_path=".", user=user, yes=yes,
		stop=stop, create_symlinks=create_symlinks, delete_symlinks=delete_symlinks)


setup.add_command(setup_sudoers)
setup.add_command(setup_nginx)
setup.add_command(reload_nginx)
setup.add_command(setup_supervisor)
setup.add_command(setup_redis)
setup.add_command(setup_letsencrypt)
setup.add_command(setup_wildcard_ssl)
setup.add_command(setup_production)
setup.add_command(setup_backups)
setup.add_command(setup_env)
setup.add_command(setup_procfile)
setup.add_command(setup_socketio)
setup.add_command(setup_requirements)
setup.add_command(setup_manager)
setup.add_command(setup_config)
setup.add_command(setup_fonts)
setup.add_command(add_domain)
setup.add_command(remove_domain)
setup.add_command(sync_domains)
setup.add_command(setup_firewall)
setup.add_command(set_ssh_port)
setup.add_command(setup_roles)
setup.add_command(setup_nginx_proxy_jail)
setup.add_command(setup_systemd)
