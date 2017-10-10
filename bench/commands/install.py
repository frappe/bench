import os, sys, json, click
from bench.utils import run_playbook, setup_sudoers

extra_vars = {"production": True}

@click.group()
def install():
	"Install system dependancies"
	pass

@click.command('prerequisites')
def install_prerequisites():
	"Install prerequisites"
	run_playbook('prerequisites/install_prerequisites.yml')

@click.command('mariadb')
@click.option('--mysql_root_password')
def install_maridb(mysql_root_password=''):
	"Install mariadb 10.1"
	if mysql_root_password:
		extra_vars.update({"mysql_root_password": mysql_root_password})

	run_playbook('prerequisites/install_roles.yml', extra_vars=extra_vars, tag='mariadb')

@click.command('wkhtmltopdf')
def install_wkhtmltopdf():
	run_playbook('prerequisites/install_roles.yml', extra_vars=extra_vars, tag='wkhtmltopdf')

@click.command('nodejs')
def install_nodejs():
	run_playbook('prerequisites/install_roles.yml', extra_vars=extra_vars, tag='nodejs')

@click.command('psutil')
def install_psutil():
	run_playbook('prerequisites/install_roles.yml', extra_vars=extra_vars, tag='psutil')

@click.command('supervisor')
@click.option('--user')
def install_supervisor(user=None):
	run_playbook('prerequisites/install_roles.yml', extra_vars=extra_vars, tag='supervisor')
	if user:
		setup_sudoers(user)

@click.command('nginx')
@click.option('--user')
def install_nginx(user=None):
	run_playbook('prerequisites/install_roles.yml', extra_vars=extra_vars, tag='nginx')
	if user:
		setup_sudoers(user)

@click.command('fail2ban')
def install_failtoban():
	run_playbook('prerequisites/install_roles.yml', extra_vars=extra_vars, tag='fail2ban')

install.add_command(install_prerequisites)
install.add_command(install_maridb)
install.add_command(install_wkhtmltopdf)
install.add_command(install_nodejs)
install.add_command(install_psutil)
install.add_command(install_supervisor)
install.add_command(install_nginx)
install.add_command(install_failtoban)