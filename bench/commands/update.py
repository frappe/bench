# imports - third party imports
import click

# imports - module imports
from bench.app import pull_apps
from bench.utils import post_upgrade, patch_sites, build_assets


@click.command('update', help="Performs an update operation on current bench. Without any flags will backup, pull, setup requirements, build, run patches and restart bench. Using specific flags will only do certain tasks instead of all")
@click.option('--pull', is_flag=True, help="Pull updates for all the apps in bench")
@click.option('--apps', type=str)
@click.option('--patch', is_flag=True, help="Run migrations for all sites in the bench")
@click.option('--build', is_flag=True, help="Build JS and CSS assets for the bench")
@click.option('--requirements', is_flag=True, help="Update requirements. If run alone, equivalent to `bench setup requirements`")
@click.option('--restart-supervisor', is_flag=True, help="Restart supervisor processes after update")
@click.option('--restart-systemd', is_flag=True, help="Restart systemd units after update")
@click.option('--no-backup', is_flag=True, help="If this flag is set, sites won't be backed up prior to updates. Note: This is not recommended in production.")
@click.option('--force', is_flag=True, help="Forces major version upgrades")
@click.option('--reset', is_flag=True, help="Hard resets git branch's to their new states overriding any changes and overriding rebase on pull")
def update(pull, apps, patch, build, requirements, restart_supervisor, restart_systemd, no_backup, force, reset):
	from bench.utils import update
	update(pull=pull, apps=apps, patch=patch, build=build, requirements=requirements, restart_supervisor=restart_supervisor, restart_systemd=restart_systemd, backup=not no_backup, force=force, reset=reset)


@click.command('retry-upgrade', help="Retry a failed upgrade")
@click.option('--version', default=5)
def retry_upgrade(version):
	pull_apps()
	patch_sites()
	build_assets()
	post_upgrade(version-1, version)


@click.command('switch-to-branch', help="Switch all apps to specified branch, or specify apps separated by space")
@click.argument('branch')
@click.argument('apps', nargs=-1)
@click.option('--upgrade',is_flag=True)
def switch_to_branch(branch, apps, upgrade=False):
	from bench.app import switch_to_branch
	switch_to_branch(branch=branch, apps=list(apps), upgrade=upgrade)


@click.command('switch-to-master', help="[DEPRECATED]: Switch frappe and erpnext to master branch")
def switch_to_master():
	from bench.utils import log
	log("`switch-to-master` has been deprecated as master branches were renamed to version-11")


@click.command('switch-to-develop')
def switch_to_develop(upgrade=False):
	"Switch frappe and erpnext to develop branch"
	from bench.app import switch_to_develop
	switch_to_develop(apps=['frappe', 'erpnext'])
