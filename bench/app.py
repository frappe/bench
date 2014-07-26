import os
from .utils import exec_cmd, get_frappe, check_git_for_shallow_clone, get_config, build_assets

import logging
import requests
import json

logger = logging.getLogger(__name__)

def get_apps(bench='.'):
	try:
		with open(os.path.join(bench, 'sites', 'apps.txt')) as f:
			return f.read().strip().split('\n')
	except IOError:
		return []

def add_to_appstxt(app, bench='.'):
	apps = get_apps(bench=bench)
	if app not in apps:
		apps.append(app)
		with open(os.path.join(bench, 'sites', 'apps.txt'), 'w') as f:
			return f.write('\n'.join(apps))

def get_app(app, git_url, bench='.'):
	logger.info('getting app {}'.format(app))
	shallow_clone = '--depth 1' if check_git_for_shallow_clone() and get_config().get('shallow_clone') else ''
	exec_cmd("git clone {git_url} {shallow_clone} --origin upstream {app}".format(git_url=git_url, app=app, shallow_clone=shallow_clone), cwd=os.path.join(bench, 'apps'))
	install_app(app, bench=bench)
	build_assets(bench=bench)

def new_app(app, bench='.'):
	logger.info('creating new app {}'.format(app))
	exec_cmd("{frappe} --make_app {apps}".format(frappe=get_frappe(bench=bench), apps=os.path.join(bench, 'apps')))
	install_app(app, bench=bench)

def install_app(app, bench='.'):
	logger.info('installing {}'.format(app))
	exec_cmd("{pip} install -e {app}".format(pip=os.path.join(bench, 'env', 'bin', 'pip'), app=os.path.join(bench, 'apps', app)))
	add_to_appstxt(app, bench=bench)

def pull_all_apps(bench='.'):
	apps_dir = os.path.join(bench, 'apps')
	apps = [app for app in os.listdir(apps_dir) if os.path.isdir(os.path.join(apps_dir, app))]
	rebase = '--rebase' if get_config().get('rebase_on_pull') else ''
	for app in apps:
		app_dir = os.path.join(apps_dir, app)
		if os.path.exists(os.path.join(app_dir, '.git')):
			logger.info('pulling {}'.format(app))
			exec_cmd("git pull {rebase} upstream HEAD".format(rebase=rebase), cwd=app_dir)

def install_apps_from_path(path, bench='.'):
	apps = get_apps_dict(path)
	for app, url in apps.items():
		get_app(app, url, bench=bench)

def get_apps_dict(path):
	if path.startswith('http'):
		r = requests.get(path)
		return r.json()
	else:
		with open(path) as f:
			return json.load(f)
