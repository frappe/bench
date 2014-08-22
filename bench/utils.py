import os
import sys
import subprocess
import getpass
import logging
import json
from distutils.spawn import find_executable

logger = logging.getLogger(__name__)

default_config = {
	'restart_supervisor_on_update': False,
	'auto_update': True,
	'serve_default_site': True,
	'rebase_on_pull': False,
	'update_bench_on_update': True,
	'shallow_clone': True
}

def get_frappe(bench='.'):
	frappe = os.path.abspath(os.path.join(bench, 'env', 'bin', 'frappe'))
	if not os.path.exists(frappe):
		print 'frappe app is not installed. Run the following command to install frappe'
		print 'bench get-app frappe https://github.com/frappe/frappe.git'
	return frappe

def init(path, apps_path=None, no_procfile=False, no_backups=False,
		no_auto_update=False, frappe_path=None):
	from .app import get_app, install_apps_from_path
	if os.path.exists(path):
		print 'Directory {} already exists!'.format(path)
		sys.exit(1)

	os.mkdir(path)
	for dirname in ('apps', 'sites', 'config', 'logs'):
		os.mkdir(os.path.join(path, dirname))

	setup_logging()

	setup_env(bench=path)
	put_config(default_config, bench=path)
	if not frappe_path:
		frappe_path = 'https://github.com/frappe/frappe.git'
	get_app('frappe', frappe_path, bench=path)
	if not no_procfile:
		setup_procfile(bench=path)
	if not no_backups:
		setup_backups(bench=path)
	if not no_auto_update:
		setup_auto_update(bench=path)
	if apps_path:
		install_apps_from_path(apps_path, bench=path)

def exec_cmd(cmd, cwd='.'):
	try:
		subprocess.check_call(cmd, cwd=cwd, shell=True)
	except subprocess.CalledProcessError, e:
		print "Error:", getattr(e, "output", None) or getattr(e, "error", None)
		raise

def setup_env(bench='.'):
	exec_cmd('virtualenv {} -p {}'.format('env', sys.executable), cwd=bench)

def setup_procfile(bench='.'):
	with open(os.path.join(bench, 'Procfile'), 'w') as f:
		f.write("""web: ./env/bin/frappe --serve --sites_path sites
worker: sh -c 'cd sites && exec ../env/bin/python -m frappe.celery_app worker'
workerbeat: sh -c 'cd sites && exec ../env/bin/python -m frappe.celery_app beat -s scheduler.schedule'""")

def new_site(site, bench='.'):
	logger.info('creating new site {}'.format(site))
	exec_cmd("{frappe} --install {site} {site}".format(frappe=get_frappe(bench=bench), site=site), cwd=os.path.join(bench, 'sites'))
	if len(get_sites(bench=bench)) == 1:
		exec_cmd("{frappe} --use {site}".format(frappe=get_frappe(bench=bench), site=site), cwd=os.path.join(bench, 'sites'))

def patch_sites(bench='.'):
	exec_cmd("{frappe} --latest all".format(frappe=get_frappe(bench=bench)), cwd=os.path.join(bench, 'sites'))

def build_assets(bench='.'):
	exec_cmd("{frappe} --build".format(frappe=get_frappe(bench=bench)), cwd=os.path.join(bench, 'sites'))

def get_sites(bench='.'):
	sites_dir = os.path.join(bench, "sites")
	sites = [site for site in os.listdir(sites_dir) 
		if os.path.isdir(os.path.join(sites_dir, site)) and site not in ('assets',)]
	return sites

def get_sites_dir(bench='.'):
	return os.path.abspath(os.path.join(bench, 'sites'))

def get_bench_dir(bench='.'):
	return os.path.abspath(bench)

def setup_auto_update(bench='.'):
	logger.info('setting up auto update')
	add_to_crontab('0 10 * * * cd {bench_dir} &&  {bench} update --auto >> {logfile} 2>&1'.format(bench_dir=get_bench_dir(bench=bench),
		bench=os.path.join(get_bench_dir(bench=bench), 'env', 'bin', 'bench'),
		logfile=os.path.join(get_bench_dir(bench=bench), 'logs', 'auto_update_log.log')))

def setup_backups(bench='.'):
	logger.info('setting up backups')
	add_to_crontab('0 */6 * * * cd {sites_dir} &&  {frappe} --backup all >> {logfile} 2>&1'.format(sites_dir=get_sites_dir(bench=bench),
		frappe=get_frappe(bench=bench),
		logfile=os.path.join(get_bench_dir(bench=bench), 'logs', 'backup.log')))

def add_to_crontab(line):
	current_crontab = read_crontab()
	if not line in current_crontab:
		s = subprocess.Popen("crontab", stdin=subprocess.PIPE)
		s.stdin.write(current_crontab)
		s.stdin.write(line + '\n')
		s.stdin.close()

def read_crontab():
	s = subprocess.Popen(["crontab", "-l"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
	out = s.stdout.read()
	s.stdout.close()
	return out

def update_bench():
	logger.info('setting up sudoers')
	cwd = os.path.dirname(os.path.abspath(__file__))
	exec_cmd("git pull", cwd=cwd)

def setup_sudoers():
	with open('/etc/sudoers.d/frappe', 'w') as f:
		f.write("{user} ALL=(ALL) NOPASSWD: {supervisorctl} restart frappe\:\n".format(
					user=getpass.getuser(),
					supervisorctl=subprocess.check_output('which supervisorctl', shell=True).strip()))

def setup_logging(bench='.'):
	if os.path.exists(os.path.join(bench, 'logs')):
		logger = logging.getLogger('bench')
		log_file = os.path.join(bench, 'logs', 'bench.log')
		formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
		hdlr = logging.FileHandler(log_file)
		hdlr.setFormatter(formatter)
		logger.addHandler(hdlr)
		logger.setLevel(logging.DEBUG)

def get_config(bench='.'):
	config_path = os.path.join(bench, 'config.json')
	if not os.path.exists(config_path):
		return {}
	with open(config_path) as f:
		return json.load(f)

def put_config(config, bench='.'):
	with open(os.path.join(bench, 'config.json'), 'w') as f:
		return json.dump(config, f, indent=1)

def update_config(new_config, bench='.'):
	config = get_config(bench=bench)
	config.update(new_config)
	put_config(config, bench=bench)

def get_process_manager():
	programs = ['foreman', 'forego', 'honcho']
	program = None
	for p in programs:
		program = find_executable(p)
		if program:
			break
	return program

def start():
	program = get_process_manager()
	if not program:
		raise Exception("No process manager found")
	os.execv(program, [program, 'start'])

def check_cmd(cmd, cwd='.'):
	try:
		subprocess.check_call(cmd, cwd=cwd, shell=True)
		return True
	except subprocess.CalledProcessError, e:
		return False

def get_git_version():
	version = get_cmd_output("git --version")
	return version.strip().split()[-1]

def check_git_for_shallow_clone():
	git_version = get_git_version()
	if '1.9' in git_version or '2.0' in git_version:
		return True
	return False

def get_cmd_output(cmd, cwd='.'):
	try:
		return subprocess.check_output(cmd, cwd=cwd, shell=True)
	except subprocess.CalledProcessError, e:
		print "Error:", e.output
		raise

def restart_supervisor_processes():
	exec_cmd("sudo supervisorctl restart frappe:")

def get_site_config(site, bench='.'):
	config_path = os.path.join(bench, 'sites', site, 'site_config.json')
	if not os.path.exists(config_path):
		return {}
	with open(config_path) as f:
		return json.load(f)

def put_site_config(site, config, bench='.'):
	config_path = os.path.join(bench, 'sites', site, 'site_config.json')
	with open(config_path, 'w') as f:
		return json.dump(config, f, indent=1)

def update_site_config(site, new_config, bench='.'):
	config = get_site_config(site, bench=bench)
	config.update(new_config)
	put_site_config(site, config, bench=bench)

def set_nginx_port(site, port, bench='.', gen_config=True):
	from .config import generate_nginx_config
	if site not in get_sites(bench=bench):
		raise Exception("No such site")
	update_site_config(site, {"nginx_port": port}, bench=bench)
	if gen_config:
		generate_nginx_config()

def set_default_site(site, bench='.'):
	if not site in get_sites(bench=bench):
		raise Exception("Site not in bench")
	exec_cmd("{frappe} --use {site}".format(frappe=get_frappe(bench=bench), site=site),
			cwd=os.path.join(bench, 'sites'))

def update_requirements(bench='.'):
	pip = os.path.join(bench, 'env', 'bin', 'pip')
	apps_dir = os.path.join(bench, 'apps')
	for app in os.listdir(apps_dir):
		req_file = os.path.join(apps_dir, app, 'requirements.txt')
		if os.path.exists(req_file):
			exec_cmd("{pip} install -r {req_file}".format(pip=pip, req_file=req_file))
