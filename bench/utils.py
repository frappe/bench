import os
import sys
import subprocess
import getpass
import logging
import json

logger = logging.getLogger(__name__)

default_config = {
	'restart_supervisor_on_update': True,
	'update_bench_on_update': True
}

def get_frappe(bench='.'):
	frappe = os.path.abspath(os.path.join(bench, 'env', 'bin', 'frappe'))
	if not os.path.exists(frappe):
		print 'frappe app is not installed. Run the following command to install frappe'
		print 'bench get-app frappe https://github.com/frappe/frappe.git'
	return frappe

def init(path):
	from .app import get_app
	if os.path.exists(path):
		print 'Directory {} already exists!'.format(path)
		sys.exit(1)

	os.mkdir(path)
	for dirname in ('apps', 'sites', 'config', 'logs'):
		os.mkdir(os.path.join(path, dirname))

	setup_logging()

	setup_env(bench=path)
	put_config(default_config, bench=path)
	get_app('frappe', 'https://github.com/frappe/frappe.git', bench=path)
	setup_backups(bench=path)
	setup_auto_update(bench=path)

def exec_cmd(cmd, cwd='.'):
	try:
		subprocess.check_call(cmd, cwd=cwd, shell=True)
	except subprocess.CalledProcessError, e:
		print "Error:", e.output
		raise

def setup_env(bench='.'):
	exec_cmd('virtualenv {} -p {}'.format('env', sys.executable), cwd=bench)

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
	exec_cmd('echo \"`crontab -l`\" | uniq | sed -e \"a0 10 * * * cd {bench_dir} &&  {bench} update\" | grep -v "^$" | uniq | crontab'.format(bench_dir=get_bench_dir(bench=bench),
	bench=os.path.join(get_bench_dir(bench=bench), 'env', 'bin', 'bench')))

def setup_backups(bench='.'):
	logger.info('setting up backups')
	exec_cmd('echo \"`crontab -l`\" | uniq | sed -e \"a0 */6 * * * cd {sites_dir} &&  {frappe} --backup all\" | grep -v "^$" | uniq | crontab'.format(sites_dir=get_sites_dir(bench=bench),
	frappe=get_frappe(bench=bench)))

def update_bench():
	logger.info('setting up sudoers')
	cwd = os.path.dirname(os.path.abspath(__file__))
	exec_cmd("git pull", cwd=cwd)

def setup_sudoers():
	with open('/etc/sudoers.d/frappe', 'w') as f:
		f.write("{user} ALL=(ALL) NOPASSWD: {supervisorctl} restart frappe\:\n".format(
					user=getpass.getuser()),
					supervisorctl=subprocess.check_output('which supervisorctl', shell=True).strip())

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
	with open(os.path.join(bench, 'config.json')) as f:
		return json.load(f)

def put_config(config, bench='.'):
	with open(os.path.join(bench, 'config.json'), 'w') as f:
		return json.dump(config, f)
