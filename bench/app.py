import os
from .utils import exec_cmd, get_frappe


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
	exec_cmd("git clone {} --origin upstream {}".format(git_url, app), cwd=os.path.join(bench, 'apps'))
	install_app(app, bench=bench)

def new_app(app, bench='.'):
	exec_cmd("{frappe} --make_app {apps}".format(frappe=get_frappe(bench=bench), apps=os.path.join(bench, 'apps')))
	install_app(app, bench=bench)

def install_app(app, bench='.'):
	exec_cmd("{pip} install -e {app}".format(pip=os.path.join(bench, 'env', 'bin', 'pip'), app=os.path.join(bench, 'apps', app)))
	add_to_appstxt(app, bench=bench)

def pull_all_apps(bench='.'):
	apps_dir = os.path.join(bench, 'apps')
	apps = [app for app in os.listdir(apps_dir) if os.path.isdir(os.path.join(apps_dir, app))]
	for app in apps:
		app_dir = os.path.join(apps_dir, app)
		if os.path.exists(os.path.join(app_dir, '.git')):
			exec_cmd("git pull --rebase upstream HEAD", cwd=app_dir)
