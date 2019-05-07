import os, sys, json, click
from bench.utils import run_playbook, setup_sudoers, is_root

extra_vars = {"production": True}

@click.group()
def install():
	"Install system dependancies"
	pass

@click.command('prerequisites')
def install_prerequisites():
	run_playbook('site.yml', tag='common, redis')

@click.command('mariadb')
@click.option('--mysql_root_password')
@click.option('--version', default="10.2")
def install_maridb(mysql_root_password='', version=''):
	if mysql_root_password:
		extra_vars.update({
			"mysql_root_password": mysql_root_password,
		})

	extra_vars.update({
		"mariadb_version": version
	})

	run_playbook('site.yml', extra_vars=extra_vars, tag='mariadb')

@click.command('wkhtmltopdf')
def install_wkhtmltopdf():
	run_playbook('site.yml', extra_vars=extra_vars, tag='wkhtmltopdf')

@click.command('nodejs')
def install_nodejs():
	run_playbook('site.yml', extra_vars=extra_vars, tag='nodejs')

@click.command('psutil')
def install_psutil():
	run_playbook('site.yml', extra_vars=extra_vars, tag='psutil')

@click.command('supervisor')
@click.option('--user')
def install_supervisor(user=None):
	run_playbook('site.yml', extra_vars=extra_vars, tag='supervisor')
	if user:
		setup_sudoers(user)

@click.command('nginx')
@click.option('--user')
def install_nginx(user=None):
	run_playbook('site.yml', extra_vars=extra_vars, tag='nginx')
	if user:
		setup_sudoers(user)

@click.command('virtualbox')
def install_virtualbox():
	run_playbook('vm_build.yml', tag='virtualbox')

@click.command('packer')
def install_packer():
	run_playbook('vm_build.yml', tag='packer')

@click.command('fail2ban')
@click.option('--maxretry', default=6, help="Number of matches (i.e. value of the counter) which triggers ban action on the IP.")
@click.option('--bantime', default=600, help="The counter is set to zero if no match is found within 'findtime' seconds.")
@click.option('--findtime', default=600, help='Duration (in seconds) for IP to be banned for. Negative number for "permanent" ban.')
def install_failtoban(**kwargs):
	extra_vars.update(kwargs)
	run_playbook('site.yml', extra_vars=extra_vars, tag='fail2ban')

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
