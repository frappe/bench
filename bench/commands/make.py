# imports - third party imports
import click


@click.command('init', help='Initialize a new bench instance in the specified path')
@click.argument('path')
@click.option('--python', type = str, default = 'python3', help = 'Path to Python Executable.')
@click.option('--ignore-exist', is_flag = True, default = False, help = "Ignore if Bench instance exists.")
@click.option('--apps_path', default=None, help="path to json files with apps to install after init")
@click.option('--frappe-path', default=None, help="path to frappe repo")
@click.option('--frappe-branch', default=None, help="path to frappe repo")
@click.option('--clone-from', default=None, help="copy repos from path")
@click.option('--clone-without-update', is_flag=True, help="copy repos from path without update")
@click.option('--no-procfile', is_flag=True, help="Pull changes in all the apps in bench")
@click.option('--no-backups',is_flag=True, help="Run migrations for all sites in the bench")
@click.option('--skip-redis-config-generation', is_flag=True, help="Skip redis config generation if already specifying the common-site-config file")
@click.option('--skip-assets',is_flag=True, default=False, help="Do not build assets")
@click.option('--verbose',is_flag=True, help="Verbose output during install")
def init(path, apps_path, frappe_path, frappe_branch, no_procfile, no_backups, clone_from, verbose, skip_redis_config_generation, clone_without_update, ignore_exist=False, skip_assets=False, python='python3'):
	from bench.utils import init, log

	try:
		init(
			path,
			apps_path=apps_path,
			no_procfile=no_procfile,
			no_backups=no_backups,
			frappe_path=frappe_path,
			frappe_branch=frappe_branch,
			verbose=verbose,
			clone_from=clone_from,
			skip_redis_config_generation=skip_redis_config_generation,
			clone_without_update=clone_without_update,
			ignore_exist=ignore_exist,
			skip_assets=skip_assets,
			python=python,
		)
		log('Bench {} initialized'.format(path), level=1)
	except SystemExit:
		pass
	except Exception as e:
		import os, shutil, time, six
		# add a sleep here so that the traceback of other processes doesnt overlap with the prompts
		time.sleep(1)
		print(e)
		log("There was a problem while creating {}".format(path), level=2)
		if six.moves.input("Do you want to rollback these changes? [Y/n]: ").lower() == "y":
			print('Rolling back Bench "{}"'.format(path))
			if os.path.exists(path):
				shutil.rmtree(path)


@click.command('get-app', help='Clone an app from the internet or filesystem and set it up in your bench')
@click.argument('name', nargs=-1) # Dummy argument for backward compatibility
@click.argument('git-url')
@click.option('--branch', default=None, help="branch to checkout")
@click.option('--overwrite', is_flag=True, default=False)
@click.option('--skip-assets', is_flag=True, default=False, help="Do not build assets")
def get_app(git_url, branch, name=None, overwrite=False, skip_assets=False):
	"clone an app from the internet and set it up in your bench"
	from bench.app import get_app
	get_app(git_url, branch=branch, skip_assets=skip_assets, overwrite=overwrite)


@click.command('new-app', help='Create a new Frappe application under apps folder')
@click.argument('app-name')
def new_app(app_name):
	from bench.app import new_app
	new_app(app_name)


@click.command('remove-app', help='Completely remove app from bench and re-build assets if not installed on any site')
@click.argument('app-name')
def remove_app(app_name):
	from bench.app import remove_app
	remove_app(app_name)


@click.command('exclude-app', help='Exclude app from updating')
@click.argument('app_name')
def exclude_app_for_update(app_name):
	from bench.app import add_to_excluded_apps_txt
	add_to_excluded_apps_txt(app_name)


@click.command('include-app', help='Include app for updating')
@click.argument('app_name')
def include_app_for_update(app_name):
	"Include app from updating"
	from bench.app import remove_from_excluded_apps_txt
	remove_from_excluded_apps_txt(app_name)


@click.command('pip', context_settings={"ignore_unknown_options": True}, help="For pip help use `bench pip help [COMMAND]` or `bench pip [COMMAND] -h`")
@click.argument('args', nargs=-1)
@click.pass_context
def pip(ctx, args):
	"Run pip commands in bench env"
	import os
	from bench.utils import get_env_cmd
	env_pip = get_env_cmd('pip')
	os.execv(env_pip, (env_pip,) + args)
