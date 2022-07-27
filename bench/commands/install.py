# imports - module imports
from bench.utils import run_playbook
from bench.utils.system import setup_sudoers

# imports - third party imports
import click


extra_vars = {"production": True}


@click.group(help="Install system dependencies for setting up Frappe environment")
def install():
	pass


@click.command(
	"prerequisites",
	help="Installs pre-requisite libraries, essential tools like b2zip, htop, screen, vim, x11-fonts, python libs, cups and Redis",
)
def install_prerequisites():
	run_playbook("site.yml", tag="common, redis")


@click.command(
	"mariadb", help="Install and setup MariaDB of specified version and root password"
)
@click.option("--mysql_root_password", "--mysql-root-password", default="")
@click.option("--version", default="10.3")
def install_maridb(mysql_root_password, version):
	if mysql_root_password:
		extra_vars.update(
			{
				"mysql_root_password": mysql_root_password,
			}
		)

	extra_vars.update({"mariadb_version": version})

	run_playbook("site.yml", extra_vars=extra_vars, tag="mariadb")


@click.command("wkhtmltopdf", help="Installs wkhtmltopdf v0.12.3 for linux")
def install_wkhtmltopdf():
	run_playbook("site.yml", extra_vars=extra_vars, tag="wkhtmltopdf")


@click.command("nodejs", help="Installs Node.js v8")
def install_nodejs():
	run_playbook("site.yml", extra_vars=extra_vars, tag="nodejs")


@click.command("psutil", help="Installs psutil via pip")
def install_psutil():
	run_playbook("site.yml", extra_vars=extra_vars, tag="psutil")


@click.command(
	"supervisor",
	help="Installs supervisor. If user is specified, sudoers is setup for that user",
)
@click.option("--user")
def install_supervisor(user=None):
	run_playbook("site.yml", extra_vars=extra_vars, tag="supervisor")
	if user:
		setup_sudoers(user)


@click.command(
	"nginx", help="Installs NGINX. If user is specified, sudoers is setup for that user"
)
@click.option("--user")
def install_nginx(user=None):
	run_playbook("site.yml", extra_vars=extra_vars, tag="nginx")
	if user:
		setup_sudoers(user)


@click.command("virtualbox", help="Installs supervisor")
def install_virtualbox():
	run_playbook("vm_build.yml", tag="virtualbox")


@click.command("packer", help="Installs Oracle virtualbox and packer 1.2.1")
def install_packer():
	run_playbook("vm_build.yml", tag="packer")


@click.command(
	"fail2ban",
	help="Install fail2ban, an intrusion prevention software framework that protects computer servers from brute-force attacks",
)
@click.option(
	"--maxretry",
	default=6,
	help="Number of matches (i.e. value of the counter) which triggers ban action on the IP.",
)
@click.option(
	"--bantime",
	default=600,
	help="The counter is set to zero if no match is found within 'findtime' seconds.",
)
@click.option(
	"--findtime",
	default=600,
	help='Duration (in seconds) for IP to be banned for. Negative number for "permanent" ban.',
)
def install_failtoban(**kwargs):
	extra_vars.update(kwargs)
	run_playbook("site.yml", extra_vars=extra_vars, tag="fail2ban")


install.add_command(install_prerequisites)
install.add_command(install_maridb)
install.add_command(install_wkhtmltopdf)
install.add_command(install_nodejs)
install.add_command(install_psutil)
install.add_command(install_supervisor)
install.add_command(install_nginx)
install.add_command(install_failtoban)
install.add_command(install_virtualbox)
install.add_command(install_packer)
