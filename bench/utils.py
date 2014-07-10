import os
import sys
import subprocess

def get_frappe(bench='.'):
	frappe = os.path.abspath(os.path.join(bench, 'env', 'bin', 'frappe'))
	if not os.path.exists(frappe):
		print 'frappe app is not installed. Run the following command to install frappe'
		print 'bench get-app frappe https://github.com/frappe/frappe.git'
	return frappe

def init(path):
	if os.path.exists(path):
		print 'Directory {} already exists!'.format(path)
		sys.exit(1)

	os.mkdir(path)
	for dirname in ('apps', 'sites', 'config', 'logs'):
		os.mkdir(os.path.join(path, dirname))
	setup_env(bench=path)

def exec_cmd(cmd, cwd='.'):
	try:
		subprocess.check_call(cmd, cwd=cwd, shell=True)
	except subprocess.CalledProcessError, e:
		print "Error:", e.output
		raise

def setup_env(bench='.'):
	exec_cmd('virtualenv {} -p {}'.format('env', sys.executable), cwd=bench)

def new_site(site, bench='.'):
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
