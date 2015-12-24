#!/usr/bin/python
import os
import subprocess
import json


def init_bench(path, frappe_branch):
    if not frappe_branch:
        frappe_branch = 'master'
    subprocess.check_call("bench init {} --frappe-branch {}".format(path, frappe_branch), shell=True)

def check_if_app_exists(app, bench_path):
    return os.path.exists(os.path.join(bench_path, 'apps', app))

def check_if_site_exists(site, bench_path):
    return os.path.exists(os.path.join(bench_path, 'sites', site))

def get_app(app, url, branch, bench_path):
    subprocess.check_call("bench get-app {} {} --branch {}".format(app, url, branch), cwd=bench_path, shell=True)

def install_site(site, mariadb_root_password, bench_path):
    admin_password = site.get('admin_password')
    site_name = site['name']
    subprocess.check_call("bench new-site {} --mariadb-root-password {} --admin-password {}".format(site_name, mariadb_root_password, admin_password), cwd=bench_path, shell=True)

    for app in site['apps']:
        subprocess.check_call("bench --site {} install-app {}".format(site['name'], app), cwd=bench_path, shell=True)

    site_config_path = os.path.join(bench_path, 'sites', site_name, 'site_config.json')
    with open(site_config_path) as f:
        site_config = json.load(f)
        site_config.update(site.get('site_config', {}))
        with open(site_config_path, 'wb') as f:
            json.dump(site_config, f)

def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(required=True),
            apps=dict(required=True),
            sites=dict(required=True),
            mariadb_root_password=dict(),
            frappe_branch=dict(),
        ),
        supports_check_mode=True
    )
    changed = False

    bench_path = module.params['path']
    if not os.path.exists(bench_path):
        if module.check_mode:
            module.exit_json(changed=True)

        init_bench(bench_path, module.params['frappe_branch'])
        changed = True


    for app in module.params['apps']:
        if not check_if_app_exists(app['name'], bench_path):
            if module.check_mode:
                module.exit_json(changed=True)

            get_app(app['name'], app['url'], app.get('branch', 'master'), bench_path)
            changed = True

    for site in module.params['sites']:
        if not check_if_site_exists(site['name'], bench_path):
            if module.check_mode:
                module.exit_json(changed=True)

            mariadb_root_password = module.params.get('mariadb_root_password')
            if not mariadb_root_password:
                module.fail_json(msg="MariaDB root password not passed")

            if not site.get('admin_password'):
                module.fail_json(msg="Admin password not passed for {}".format(site['name']))

            install_site(site, mariadb_root_password, bench_path)
            changed = True

    module.exit_json(changed=changed)

from ansible.module_utils.basic import *
main()
