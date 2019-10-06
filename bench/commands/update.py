import click
import sys, os
from bench.config.common_site_config import get_config, update_config
from bench.app import pull_all_apps, is_version_upgrade, validate_branch
from bench.utils import (update_bench, validate_upgrade, pre_upgrade, post_upgrade, before_update,
	update_requirements, update_node_packages, backup_all_sites, patch_sites, build_assets,
	restart_supervisor_processes, restart_systemd_processes)
from bench import patches


@click.command('update')
@click.option('--pull', is_flag=True, help="Pull changes in all the apps in bench")
@click.option('--patch', is_flag=True, help="Run migrations for all sites in the bench")
@click.option('--build', is_flag=True, help="Build JS and CSS artifacts for the bench")
@click.option('--bench', is_flag=True, help="Update bench")
@click.option('--requirements', is_flag=True, help="Update requirements")
@click.option('--restart-supervisor', is_flag=True, help="restart supervisor processes after update")
@click.option('--restart-systemd', is_flag=True, help="restart systemd units after update")
@click.option('--auto', is_flag=True)
@click.option('--no-backup', is_flag=True)
@click.option('--force', is_flag=True)
@click.option('--reset', is_flag=True, help="Hard resets git branch's to their new states overriding any changes and overriding rebase on pull")
def update(pull=False, patch=False, build=False, bench=False, auto=False, restart_supervisor=False, restart_systemd=False, requirements=False, no_backup=False, force=False, reset=False):
	"Update bench"

	if not (pull or patch or build or bench or requirements):
		pull, patch, build, bench, requirements = True, True, True, True, True

	if auto:
		sys.exit(1)

	patches.run(bench_path='.')
	conf = get_config(".")

	if bench and conf.get('update_bench_on_update'):
		update_bench()
		restart_update({
				'pull': pull,
				'patch': patch,
				'build': build,
				'requirements': requirements,
				'no-backup': no_backup,
				'restart-supervisor': restart_supervisor,
				'reset': reset
		})

	if conf.get('release_bench'):
		print('Release bench, cannot update')
		sys.exit(1)

	validate_branch()

	version_upgrade = is_version_upgrade()
	if version_upgrade[0]:
		print()
		print()
		print("This update will cause a major version change in Frappe/ERPNext from {0} to {1}.".format(*version_upgrade[1:]))
		print("This would take significant time to migrate and might break custom apps.")
		click.confirm('Do you want to continue?', abort=True)

	_update(pull, patch, build, bench, auto, restart_supervisor, restart_systemd, requirements, no_backup, force=force, reset=reset)

def _update(pull=False, patch=False, build=False, update_bench=False, auto=False, restart_supervisor=False,
		restart_systemd=False, requirements=False, no_backup=False, bench_path='.', force=False, reset=False):
	conf = get_config(bench_path=bench_path)
	version_upgrade = is_version_upgrade(bench_path=bench_path)

	if version_upgrade[0] or (not version_upgrade[0] and force):
		validate_upgrade(version_upgrade[1], version_upgrade[2], bench_path=bench_path)

	before_update(bench_path=bench_path, requirements=requirements)

	conf.update({ "maintenance_mode": 1, "pause_scheduler": 1 })
	update_config(conf, bench_path=bench_path)

	if not no_backup:
		print('Backing up sites...')
		backup_all_sites(bench_path=bench_path)

	if pull:
		pull_all_apps(bench_path=bench_path, reset=reset)

	if requirements:
		update_requirements(bench_path=bench_path)
		update_node_packages(bench_path=bench_path)

	if version_upgrade[0] or (not version_upgrade[0] and force):
		pre_upgrade(version_upgrade[1], version_upgrade[2], bench_path=bench_path)
		import bench.utils, bench.app
		print('Reloading bench...')
		if sys.version_info >= (3, 4):
			import importlib
			importlib.reload(bench.utils)
			importlib.reload(bench.app)
		else:
			reload(bench.utils)
			reload(bench.app)

	if patch:
		print('Patching sites...')
		patch_sites(bench_path=bench_path)
	if build:
		build_assets(bench_path=bench_path)
	if version_upgrade[0] or (not version_upgrade[0] and force):
		post_upgrade(version_upgrade[1], version_upgrade[2], bench_path=bench_path)
	if restart_supervisor or conf.get('restart_supervisor_on_update'):
		restart_supervisor_processes(bench_path=bench_path)
	if restart_systemd or conf.get('restart_systemd_on_update'):
		restart_systemd_processes(bench_path=bench_path)

	conf.update({ "maintenance_mode": 0, "pause_scheduler": 0 })
	update_config(conf, bench_path=bench_path)

	print("_"*80)
	print("Bench: Deployment tool for Frappe and ERPNext (https://erpnext.org).")
	print("Open source depends on your contributions, so please contribute bug reports, patches, fixes or cash and be a part of the community")
	print()

@click.command('retry-upgrade')
@click.option('--version', default=5)
def retry_upgrade(version):
	pull_all_apps()
	patch_sites()
	build_assets()
	post_upgrade(version-1, version)

def restart_update(kwargs):
	args = ['--'+k for k, v in list(kwargs.items()) if v]
	os.execv(sys.argv[0], sys.argv[:2] + args)

@click.command('switch-to-branch')
@click.argument('branch')
@click.argument('apps', nargs=-1)
@click.option('--upgrade',is_flag=True)
def switch_to_branch(branch, apps, upgrade=False):
	"Switch all apps to specified branch, or specify apps separated by space"
	from bench.app import switch_to_branch
	switch_to_branch(branch=branch, apps=list(apps), upgrade=upgrade)
	print('Switched to ' + branch)
	print('Please run `bench update --patch` to be safe from any differences in database schema')

@click.command('switch-to-master')
def switch_to_master():
	"Switch frappe and erpnext to master branch"
	from bench.app import switch_to_master
	switch_to_master(apps=['frappe', 'erpnext'])
	print()
	print('Switched to master')
	print('Please run `bench update --patch` to be safe from any differences in database schema')

@click.command('switch-to-develop')
def switch_to_develop(upgrade=False):
	"Switch frappe and erpnext to develop branch"
	from bench.app import switch_to_develop
	switch_to_develop(apps=['frappe', 'erpnext'])
	print()
	print('Switched to develop')
	print('Please run `bench update --patch` to be safe from any differences in database schema')
