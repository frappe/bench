from .utils import exec_cmd, get_frappe, run_frappe_cmd
from .release import get_current_version
from .app import remove_from_appstxt
import os
import shutil
import sys

repos = ('frappe', 'erpnext')

def migrate_to_v5(bench='.'):
	validate_v4(bench=bench)
	for repo in repos:
		checkout_v5(repo, bench=bench)
	remove_shopping_cart(bench=bench)
	exec_cmd("{bench} update".format(bench=sys.argv[0]))

def remove_shopping_cart(bench='.'):
	archived_apps_dir = os.path.join(bench, 'archived_apps')
	shopping_cart_dir = os.path.join(bench, 'apps', 'shopping_cart')

	if not os.path.exists(shopping_cart_dir):
		return

	run_frappe_cmd('--site', 'all', 'remove-from-installed-apps', 'shopping_cart', bench=bench)
	remove_from_appstxt('shopping_cart', bench=bench)
	exec_cmd("{pip} --no-input uninstall -y shopping_cart".format(pip=os.path.join(bench, 'env', 'bin', 'pip')))

	if not os.path.exists(archived_apps_dir):
		os.mkdir(archived_apps_dir)
	shutil.move(shopping_cart_dir, archived_apps_dir)

def validate_v4(bench='.'):
	for repo in repos:
		path = os.path.join(bench, 'apps', repo)
		if os.path.exists(path):
			current_version = get_current_version(path)
			if not current_version.startswith('4'):
				raise Exception("{} is not on v4.x.x".format(repo))

def checkout_v5(repo, bench='.'):
	cwd = os.path.join(bench, 'apps', repo)
	if os.path.exists(cwd):
		exec_cmd("git fetch upstream", cwd=cwd)
		exec_cmd("git checkout v5.0", cwd=cwd)
		exec_cmd("git clean -df", cwd=cwd)

