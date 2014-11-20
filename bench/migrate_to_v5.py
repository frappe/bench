from .utils import exec_cmd, get_frappe
import os
import shutil
from .release import get_current_version

repos = ('frappe', 'erpnext')

def migrate_to_v5(bench='.'):
	from .cli import restart_update
	validate_v4(bench=bench)
	for repo in repos:
		checkout_v5(repo, bench=bench)
	remove_shopping_cart(bench=bench)
	restart_update({
			'patch': True,
			'build': True,
			'requirements': True,
			'restart-supervisor': True
	})

def remove_shopping_cart(bench='.'):
	exec_cmd("{pip} --no-input uninstall -y shopping_cart".format(pip=os.path.join(bench, 'env', 'bin', 'pip')))
	exec_cmd("{frappe} all --remove_from_installed_apps shopping_cart".format(frappe=get_frappe(bench=bench)))
	archived_apps_dir = os.path.join(bench, 'archived_apps')
	shopping_cart_dir = os.path.join(bench, 'apps', 'shopping_cart')
	if not os.path.exists(archived_apps_dir):
		os.mkdir(archived_apps_dir)
	shutil.move(shopping_cart_dir, archived_apps_dir)

def validate_v4(bench='.'):
	for repo in repos:
		path = os.path.join(bench, 'apps', repo)
		current_version = get_current_version(path)
		if not current_version.startswith('4'):
			raise Exception("{} is not v4.x.x")

def checkout_v5(repo, bench='.'):
	cwd = os.path.join(bench, 'apps', repo)
	exec_cmd("git fetch upstream", cwd=cwd)
	exec_cmd("git checkout v5.0", cwd=cwd)

