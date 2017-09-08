import os, sys, json, click
from bench.utils import run_playbook

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
	extra_vars.update(mysql_root_password)
	run_playbook('prerequisites/install_roles.yml', extra_vars=extra_vars, tag='maridb')

@click.command('wkhtmltopdf')
def install_wkhtmltopdf():
	run_playbook('prerequisites/install_roles.yml', extra_vars=extra_vars, tag='wkhtmltopdf')

@click.command('nodejs')
def install_nodejs():
	run_playbook('prerequisites/install_roles.yml', extra_vars=extra_vars, tag='nodejs')

@click.command('psutil')
def install_psutil():
	run_playbook('prerequisites/install_roles.yml', extra_vars=extra_vars, tag='psutil')

@click.command('nginx')
def install_nginx():
	run_playbook('prerequisites/install_roles.yml', extra_vars=extra_vars, tag='nginx')

@click.command('fail2ban')
def install_failtoban():
	run_playbook('prerequisites/install_roles.yml', extra_vars=extra_vars, tag='fail2ban')

install.add_command(install_prerequisites)
install.add_command(install_maridb)
install.add_command(install_wkhtmltopdf)
install.add_command(install_nodejs)
install.add_command(install_psutil)
install.add_command(install_nginx)
install.add_command(install_failtoban)