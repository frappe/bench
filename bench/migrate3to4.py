from frappe.installer import add_to_installed_apps
from frappe.cli import latest, backup
from frappe.modules.patch_handler import executed
from frappe.installer import make_site_dirs
import frappe
import argparse
import os
import imp
import json
import shutil
import subprocess

sites_path = os.environ.get('SITES_PATH', 'sites')
last_3_patch = 'patches.1401.fix_planned_qty'


def get_frappe(bench='.'):
	frappe = os.path.abspath(os.path.join(bench, 'env', 'bin', 'frappe'))
	if not os.path.exists(frappe):
		print 'frappe app is not installed. Run the following command to install frappe'
		print 'bench get-app frappe https://github.com/frappe/frappe.git'
	return frappe

def get_sites(bench='.'):
	sites_dir = os.path.join(bench, "sites")
	sites = [site for site in os.listdir(sites_dir) 
		if os.path.isdir(os.path.join(sites_dir, site)) and site not in ('assets',)]
	return sites

def exec_cmd(cmd, cwd='.'):
	try:
		subprocess.check_call(cmd, cwd=cwd, shell=True)
	except subprocess.CalledProcessError, e:
		print "Error:", e.output
		raise

def main(path):
	site = copy_site(path)
	migrate(site)

def copy_site(path):
	if not os.path.exists(path):
		raise Exception("Source site does not exist")
	site = os.path.basename(path)
	site_path = os.path.join(sites_path, site)
	confpy_path = os.path.join(path, 'conf.py')
	confjson_path = os.path.join(path, 'site_config.json')
	if os.path.exists(site_path):
		raise Exception("Site already exists")

	os.mkdir(site_path)
	print os.path.join(path, 'public')
	if os.path.exists(os.path.join(path, 'public')):
		exec_cmd("cp -r {src} {dest}".format(
					src=os.path.join(path, 'public'),
					dest=os.path.join(site_path, 'public')))

	if os.path.exists(confpy_path):
		with open(os.path.join(site_path, 'site_config.json'), 'w') as f:
			f.write(module_to_json(confpy_path, indent=1))
	if os.path.exists(confjson_path):
		shutil.copy(confjson_path, os.path.join(site_path, 'site_config.json'))
	if len(get_sites()) == 1:
		exec_cmd("{frappe} --use {site}".format(frappe=get_frappe(), site=site), cwd='sites')
	return site

def validate(site):
        frappe.init(site=site, sites_path=sites_path)
        make_site_dirs()
        backup()
        frappe.init(site=site, sites_path=sites_path)
        frappe.connect()
        if not executed(last_3_patch):
                raise Exception, "site not ready to migrate to version 4"
        frappe.destroy()


def migrate(site):
        validate(site)
        os.chdir(sites_path)
        frappe.init(site=site)
        frappe.connect()
        add_to_installed_apps('frappe', rebuild_website=False)
        add_to_installed_apps('erpnext', rebuild_website=False)
        add_to_installed_apps('shopping_cart', rebuild_website=False)
        latest()

def module_to_json(module_path, indent=None, keys=None):
	module = imp.load_source('tempmod', module_path)
	json_keys = [x for x in dir(module) if not x.startswith('_')]

	if keys:
		json_keys = [x for x in json_keys if x in keys]
	if 'unicode_literals' in json_keys:
		json_keys.remove('unicode_literals')
	if 'backup_path' in json_keys:
		json_keys.remove('backup_path')

	module = {x:getattr(module, x) for x in json_keys}
	return json.dumps(module, indent=indent)

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('site')
	args = parser.parse_args()
	main(args.site)
