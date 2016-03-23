import click

@click.command()
@click.argument('path')
@click.option('--apps_path', default=None, help="path to json files with apps to install after init")
@click.option('--frappe-path', default=None, help="path to frappe repo")
@click.option('--frappe-branch', default=None, help="path to frappe repo")
@click.option('--no-procfile', is_flag=True, help="Pull changes in all the apps in bench")
@click.option('--no-backups',is_flag=True, help="Run migrations for all sites in the bench")
@click.option('--no-auto-update',is_flag=True, help="Build JS and CSS artifacts for the bench")
@click.option('--verbose',is_flag=True, help="Verbose output during install")
def init(path, apps_path, frappe_path, frappe_branch, no_procfile, no_backups,
		no_auto_update, verbose):
	"Create a new bench"
	from bench.utils import init
	init(path, apps_path=apps_path, no_procfile=no_procfile, no_backups=no_backups,
			no_auto_update=no_auto_update, frappe_path=frappe_path, frappe_branch=frappe_branch, verbose=verbose)
	click.echo('Bench {} initialized'.format(path))


@click.command('get-app')
@click.argument('name')
@click.argument('git-url')
@click.option('--branch', default=None, help="branch to checkout")
def get_app(name, git_url, branch):
	"clone an app from the internet and set it up in your bench"
	from bench.app import get_app
	get_app(name, git_url, branch=branch)


@click.command('new-app')
@click.argument('app-name')
def new_app(app_name):
	"start a new app"
	from bench.app import new_app
	new_app(app_name)


@click.command('new-site')
@click.option('--mariadb-root-password', help="MariaDB root password")
@click.option('--admin-password', help="admin password to set for site")
@click.argument('site')
def new_site(site, mariadb_root_password=None, admin_password=None):
	"Create a new site in the bench"
	from bench.utils import new_site
	new_site(site, mariadb_root_password=mariadb_root_password, admin_password=admin_password)


