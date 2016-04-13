import os
import sys
import subprocess
import logging
import itertools
import requests
import json
import platform
import select
import multiprocessing
from distutils.spawn import find_executable
import pwd, grp

class PatchError(Exception):
	pass


class CommandFailedError(Exception):
	pass

logger = logging.getLogger(__name__)


folders_in_bench = ('apps', 'sites', 'config', 'logs', 'config/pids')

def get_frappe(bench='.'):
	frappe = get_env_cmd('frappe', bench=bench)
	if not os.path.exists(frappe):
		print 'frappe app is not installed. Run the following command to install frappe'
		print 'bench get-app frappe https://github.com/frappe/frappe.git'
	return frappe

def get_env_cmd(cmd, bench='.'):
	return os.path.abspath(os.path.join(bench, 'env', 'bin', cmd))

def init(path, apps_path=None, no_procfile=False, no_backups=False,
		no_auto_update=False, frappe_path=None, frappe_branch=None, wheel_cache_dir=None,
		verbose=False):
	from .app import get_app, install_apps_from_path
	from .config.common_site_config import make_config
	from .config import redis
	from .config.procfile import setup_procfile
	global FRAPPE_VERSION

	if os.path.exists(path):
		print 'Directory {} already exists!'.format(path)
		raise Exception("Site directory already exists")
		# sys.exit(1)

	os.makedirs(path)
	for dirname in folders_in_bench:
		os.mkdir(os.path.join(path, dirname))

	setup_logging()

	setup_env(bench=path)

	make_config(path)

	if not frappe_path:
		frappe_path = 'https://github.com/frappe/frappe.git'
	get_app('frappe', frappe_path, branch=frappe_branch, bench=path, build_asset_files=False, verbose=verbose)

	if apps_path:
		install_apps_from_path(apps_path, bench=path)

	FRAPPE_VERSION = get_current_frappe_version(bench=path)
	if FRAPPE_VERSION > 5:
		setup_socketio(bench=path)

	build_assets(bench=path)
	redis.generate_config(path)

	if not no_procfile:
		setup_procfile(path)
	if not no_backups:
		setup_backups(bench=path)
	if not no_auto_update:
		setup_auto_update(bench=path)


def exec_cmd(cmd, cwd='.'):
	from .cli import from_command_line

	async = False if from_command_line else True
	if async:
		stderr = stdout = subprocess.PIPE
	else:
		stderr = stdout = None

	p = subprocess.Popen(cmd, cwd=cwd, shell=True, stdout=stdout, stderr=stderr)

	if async:
		return_code = print_output(p)
	else:
		return_code = p.wait()

	if return_code > 0:
		raise CommandFailedError(cmd)

def setup_env(bench='.'):
	exec_cmd('virtualenv -q {} -p {}'.format('env', sys.executable), cwd=bench)
	exec_cmd('./env/bin/pip -q install --upgrade pip', cwd=bench)
	exec_cmd('./env/bin/pip -q install wheel', cwd=bench)
	# exec_cmd('./env/bin/pip -q install https://github.com/frappe/MySQLdb1/archive/MySQLdb-1.2.5-patched.tar.gz', cwd=bench)
	exec_cmd('./env/bin/pip -q install -e git+https://github.com/frappe/python-pdfkit.git#egg=pdfkit', cwd=bench)

def setup_socketio(bench='.'):
	exec_cmd("npm install socket.io redis express superagent cookie", cwd=bench)

def new_site(site, mariadb_root_password=None, admin_password=None, bench='.'):
	import hashlib
	logger.info('creating new site {}'.format(site))
	mariadb_root_password_fragment = '--root_password {}'.format(mariadb_root_password) if mariadb_root_password else ''
	admin_password_fragment = '--admin_password {}'.format(admin_password) if admin_password else ''
	exec_cmd("{frappe} {site} --install {db_name} {mariadb_root_password_fragment} {admin_password_fragment}".format(
				frappe=get_frappe(bench=bench),
				site=site,
				db_name = hashlib.sha1(site).hexdigest()[:10],
				mariadb_root_password_fragment=mariadb_root_password_fragment,
				admin_password_fragment=admin_password_fragment
			), cwd=os.path.join(bench, 'sites'))
	if len(get_sites(bench=bench)) == 1:
		exec_cmd("{frappe} --use {site}".format(frappe=get_frappe(bench=bench), site=site), cwd=os.path.join(bench, 'sites'))

def patch_sites(bench='.'):
	try:
		if FRAPPE_VERSION == 4:
			exec_cmd("{frappe} --latest all".format(frappe=get_frappe(bench=bench)), cwd=os.path.join(bench, 'sites'))
		else:
			run_frappe_cmd('--site', 'all', 'migrate', bench=bench)
	except subprocess.CalledProcessError:
		raise PatchError

def build_assets(bench='.'):
	if FRAPPE_VERSION == 4:
		exec_cmd("{frappe} --build".format(frappe=get_frappe(bench=bench)), cwd=os.path.join(bench, 'sites'))
	else:
		run_frappe_cmd('build', bench=bench)

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
	bench_dir = get_bench_dir(bench=bench)
	if FRAPPE_VERSION == 4:
		backup_command = "cd {sites_dir} && {frappe} --backup all".format(frappe=get_frappe(bench=bench),)
	else:
		backup_command = "cd {bench_dir} && {bench} --site all backup".format(bench_dir=bench_dir, bench=sys.argv[0])

	add_to_crontab('0 */6 * * *  {backup_command} >> {logfile} 2>&1'.format(backup_command=backup_command,
		logfile=os.path.join(get_bench_dir(bench=bench), 'logs', 'backup.log')))

def add_to_crontab(line):
	current_crontab = read_crontab()
	if not line in current_crontab:
		cmd = ["crontab"]
		if platform.system() == 'FreeBSD':
			cmd = ["crontab", "-"]
		s = subprocess.Popen(cmd, stdin=subprocess.PIPE)
		s.stdin.write(current_crontab)
		s.stdin.write(line + '\n')
		s.stdin.close()

def read_crontab():
	s = subprocess.Popen(["crontab", "-l"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
	out = s.stdout.read()
	s.stdout.close()
	return out

def update_bench():
	logger.info('updating bench')

	# bench-repo folder
	cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

	exec_cmd("git pull", cwd=cwd)

def setup_sudoers(user):
	sudoers_file = '/etc/sudoers.d/frappe'
	with open(sudoers_file, 'w') as f:
		f.write("{user} ALL=(ALL) NOPASSWD: {supervisorctl}\n".format(
					user=user,
					supervisorctl=subprocess.check_output('which supervisorctl', shell=True).strip()))
	os.chmod(sudoers_file, 0440)

def setup_logging(bench='.'):
	if os.path.exists(os.path.join(bench, 'logs')):
		logger = logging.getLogger('bench')
		log_file = os.path.join(bench, 'logs', 'bench.log')
		formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
		hdlr = logging.FileHandler(log_file)
		hdlr.setFormatter(formatter)
		logger.addHandler(hdlr)
		logger.setLevel(logging.DEBUG)

def get_program(programs):
	program = None
	for p in programs:
		program = find_executable(p)
		if program:
			break
	return program

def get_process_manager():
	return get_program(['foreman', 'forego', 'honcho'])

def start(no_dev=False, concurrency=None):
	program = get_process_manager()
	if not program:
		raise Exception("No process manager found")
	os.environ['PYTHONUNBUFFERED'] = "true"
	if not no_dev:
		os.environ['DEV_SERVER'] = "true"

	command = [program, 'start']
	if concurrency:
		command.extend(['-c', concurrency])

	os.execv(program, command)

def check_cmd(cmd, cwd='.'):
	try:
		subprocess.check_call(cmd, cwd=cwd, shell=True)
		return True
	except subprocess.CalledProcessError:
		return False

def get_git_version():
	'''returns git version from `git --version`
	extracts version number from string `get version 1.9.1` etc'''
	version = get_cmd_output("git --version").strip().split()[2]
	version = '.'.join(version.split('.')[0:2])
	return float(version)

def check_git_for_shallow_clone():
	from .config.common_site_config import get_config
	if get_config(".").get('release_bench'):
		return False

	git_version = get_git_version()
	if git_version > 1.9:
		return True
	return False

def get_cmd_output(cmd, cwd='.'):
	try:
		return subprocess.check_output(cmd, cwd=cwd, shell=True, stderr=open(os.devnull, 'wb')).strip()
	except subprocess.CalledProcessError, e:
		if e.output:
			print e.output
		raise

def restart_supervisor_processes(bench='.'):
	from .config.common_site_config import get_config
	conf = get_config(bench=bench)
	bench_name = get_bench_name(bench)
	cmd = conf.get('supervisor_restart_cmd',
				   'sudo supervisorctl restart {bench_name}-processes:'.format(bench_name=bench_name))

	try:
		exec_cmd(cmd, cwd=bench)
	except CommandFailedError:
		if cmd.endswith('{bench_name}-processes:'.format(bench_name=bench_name)):
			# backward compatibility
			exec_cmd('sudo supervisorctl restart frappe:', cwd=bench)
		else:
			raise

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
	set_site_config_nginx_property(site, {"nginx_port": port}, bench=bench, gen_config=gen_config)

def set_ssl_certificate(site, ssl_certificate, bench='.', gen_config=True):
	set_site_config_nginx_property(site, {"ssl_certificate": ssl_certificate}, bench=bench, gen_config=gen_config)

def set_ssl_certificate_key(site, ssl_certificate_key, bench='.', gen_config=True):
	set_site_config_nginx_property(site, {"ssl_certificate_key": ssl_certificate_key}, bench=bench, gen_config=gen_config)

def set_site_config_nginx_property(site, config, bench='.', gen_config=True):
	from .config.nginx import make_nginx_conf
	if site not in get_sites(bench=bench):
		raise Exception("No such site")
	update_site_config(site, config, bench=bench)
	if gen_config:
		make_nginx_conf(bench_path=bench)

def set_url_root(site, url_root, bench='.'):
	update_site_config(site, {"host_name": url_root}, bench=bench)

def set_default_site(site, bench='.'):
	if not site in get_sites(bench=bench):
		raise Exception("Site not in bench")
	exec_cmd("{frappe} --use {site}".format(frappe=get_frappe(bench=bench), site=site),
			cwd=os.path.join(bench, 'sites'))

def update_requirements(bench='.'):
	pip = os.path.join(bench, 'env', 'bin', 'pip')

	# upgrade pip to latest
	exec_cmd("{pip} install --upgrade pip".format(pip=pip))

	apps_dir = os.path.join(bench, 'apps')
	for app in os.listdir(apps_dir):
		req_file = os.path.join(apps_dir, app, 'requirements.txt')
		if os.path.exists(req_file):
			exec_cmd("{pip} install -q -r {req_file}".format(pip=pip, req_file=req_file))

def backup_site(site, bench='.'):
	if FRAPPE_VERSION == 4:
		exec_cmd("{frappe} --backup {site}".format(frappe=get_frappe(bench=bench), site=site),
				cwd=os.path.join(bench, 'sites'))
	else:
		run_frappe_cmd('--site', site, 'backup', bench=bench)

def backup_all_sites(bench='.'):
	for site in get_sites(bench=bench):
		backup_site(site, bench=bench)

def is_root():
	if os.getuid() == 0:
		return True
	return False

def set_mariadb_host(host, bench='.'):
	update_common_site_config({'db_host': host}, bench=bench)

def update_common_site_config(ddict, bench='.'):
	update_json_file(os.path.join(bench, 'sites', 'common_site_config.json'), ddict)

def update_json_file(filename, ddict):
	if os.path.exists(filename):
		with open(filename, 'r') as f:
			content = json.load(f)

	else:
		content = {}

	content.update(ddict)
	with open(filename, 'w') as f:
		content = json.dump(content, f, indent=1, sort_keys=True)

def drop_privileges(uid_name='nobody', gid_name='nogroup'):
	# from http://stackoverflow.com/a/2699996
	if os.getuid() != 0:
		# We're not root so, like, whatever dude
		return

	# Get the uid/gid from the name
	running_uid = pwd.getpwnam(uid_name).pw_uid
	running_gid = grp.getgrnam(gid_name).gr_gid

	# Remove group privileges
	os.setgroups([])

	# Try setting the new uid/gid
	os.setgid(running_gid)
	os.setuid(running_uid)

	# Ensure a very conservative umask
	os.umask(022)

def fix_prod_setup_perms(bench='.', frappe_user=None):
	from .config.common_site_config import get_config
	files = [
		"logs/web.error.log",
		"logs/web.log",
		"logs/workerbeat.error.log",
		"logs/workerbeat.log",
		"logs/worker.error.log",
		"logs/worker.log",
		"config/nginx.conf",
		"config/supervisor.conf",
	]

	if not frappe_user:
		frappe_user = get_config(bench).get('frappe_user')

	if not frappe_user:
		print "frappe user not set"
		sys.exit(1)

	for path in files:
		if os.path.exists(path):
			uid = pwd.getpwnam(frappe_user).pw_uid
			gid = grp.getgrnam(frappe_user).gr_gid
			os.chown(path, uid, gid)

def fix_file_perms():
	for dir_path, dirs, files in os.walk('.'):
		for _dir in dirs:
			os.chmod(os.path.join(dir_path, _dir), 0755)
		for _file in files:
			os.chmod(os.path.join(dir_path, _file), 0644)
	bin_dir = './env/bin'
	if os.path.exists(bin_dir):
		for _file in os.listdir(bin_dir):
			if not _file.startswith('activate'):
				os.chmod(os.path.join(bin_dir, _file), 0755)

def get_current_frappe_version(bench='.'):
	from .app import get_current_frappe_version as fv
	return fv(bench=bench)

def run_frappe_cmd(*args, **kwargs):
	from .cli import from_command_line

	bench = kwargs.get('bench', '.')
	f = get_env_cmd('python', bench=bench)
	sites_dir = os.path.join(bench, 'sites')

	async = False if from_command_line else True
	if async:
		stderr = stdout = subprocess.PIPE
	else:
		stderr = stdout = None

	p = subprocess.Popen((f, '-m', 'frappe.utils.bench_helper', 'frappe') + args,
		cwd=sites_dir, stdout=stdout, stderr=stderr)

	if async:
		return_code = print_output(p)
	else:
		return_code = p.wait()

	if return_code > 0:
		raise CommandFailedError(args)

def get_frappe_cmd_output(*args, **kwargs):
	bench = kwargs.get('bench', '.')
	f = get_env_cmd('python', bench=bench)
	sites_dir = os.path.join(bench, 'sites')
	return subprocess.check_output((f, '-m', 'frappe.utils.bench_helper', 'frappe') + args, cwd=sites_dir)

def validate_upgrade(from_ver, to_ver, bench='.'):
	if to_ver >= 6:
		if not find_executable('npm') and not (find_executable('node') or find_executable('nodejs')):
			raise Exception("Please install nodejs and npm")

def pre_upgrade(from_ver, to_ver, bench='.'):
	from .migrate_to_v5 import remove_shopping_cart
	pip = os.path.join(bench, 'env', 'bin', 'pip')
	if from_ver <= 4 and to_ver >= 5:
		apps = ('frappe', 'erpnext')
		remove_shopping_cart(bench=bench)

		for app in apps:
			cwd = os.path.abspath(os.path.join(bench, 'apps', app))
			if os.path.exists(cwd):
				exec_cmd("git clean -dxf", cwd=cwd)
				exec_cmd("{pip} install --upgrade -e {app}".format(pip=pip, app=cwd))

def post_upgrade(from_ver, to_ver, bench='.'):
	from .config.common_site_config import get_config
	from .config import redis
	from .config.supervisor import generate_supervisor_config
	from .config.nginx import make_nginx_conf
	conf = get_config(bench=bench)
	print "-"*80
	print "Your bench was upgraded to version {0}".format(to_ver)

	if conf.get('restart_supervisor_on_update'):
		redis.generate_config(bench_path=bench)
		generate_supervisor_config(bench_path=bench)
		make_nginx_conf(bench_path=bench)

		if from_ver == 4 and to_ver == 5:
			setup_backups(bench=bench)

		if from_ver <= 5 and to_ver == 6:
			setup_socketio(bench=bench)

		print "As you have setup your bench for production, you will have to reload configuration for nginx and supervisor"
		print "To complete the migration, please run the following commands"
		print
		print "sudo service nginx restart"
		print "sudo supervisorctl reload"

def update_translations_p(args):
	try:
		update_translations(*args)
	except requests.exceptions.HTTPError:
		print 'Download failed for', args[0], args[1]

def download_translations_p():
	pool = multiprocessing.Pool(4)

	langs = get_langs()
	apps = ('frappe', 'erpnext')
	args = list(itertools.product(apps, langs))

	pool.map(update_translations_p, args)

def download_translations():
	langs = get_langs()
	apps = ('frappe', 'erpnext')
	for app, lang in itertools.product(apps, langs):
		update_translations(app, lang)

def get_langs():
	lang_file = 'apps/frappe/frappe/data/languages.txt'
	with open(lang_file) as f:
		lang_data = f.read()
	langs = [line.split()[0] for line in lang_data.splitlines()]
	langs.remove('en')
	return langs

def update_translations(app, lang):
	translations_dir = os.path.join('apps', app, app, 'translations')
	csv_file = os.path.join(translations_dir, lang + '.csv')
	url = "https://translate.erpnext.com/files/{}-{}.csv".format(app, lang)
	r = requests.get(url, stream=True)
	r.raise_for_status()

	with open(csv_file, 'wb') as f:
		for chunk in r.iter_content(chunk_size=1024):
			# filter out keep-alive new chunks
			if chunk:
				f.write(chunk)
				f.flush()

	print 'downloaded for', app, lang

def print_output(p):
	while p.poll() is None:
		readx = select.select([p.stdout.fileno(), p.stderr.fileno()], [], [])[0]
		send_buffer = []
		for fd in readx:
			if fd == p.stdout.fileno():
				while 1:
					buf = p.stdout.read(1)
					if not len(buf):
						break
					if buf == '\r' or buf == '\n':
						send_buffer.append(buf)
						log_line(''.join(send_buffer), 'stdout')
						send_buffer = []
					else:
						send_buffer.append(buf)

			if fd == p.stderr.fileno():
				log_line(p.stderr.readline(), 'stderr')
	return p.poll()


def log_line(data, stream):
	if stream == 'stderr':
		return sys.stderr.write(data)
	return sys.stdout.write(data)

def get_output(*cmd):
	s = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
	out = s.stdout.read()
	s.stdout.close()
	return out

FRAPPE_VERSION = get_current_frappe_version()

def before_update(bench, requirements):
	validate_pillow_dependencies(bench, requirements)

def validate_pillow_dependencies(bench, requirements):
	if not requirements:
		return

	try:
		pip = os.path.join(bench, 'env', 'bin', 'pip')
		exec_cmd("{pip} install Pillow".format(pip=pip))

	except CommandFailedError:
		distro = platform.linux_distribution()
		distro_name = distro[0].lower()
		if "centos" in distro_name or "fedora" in distro_name:
			print "Please install these dependencies using the command:"
			print "sudo yum install libtiff-devel libjpeg-devel libzip-devel freetype-devel lcms2-devel libwebp-devel tcl-devel tk-devel"

			raise

		elif "ubuntu" in distro_name or "elementary os" in distro_name or "debian" in distro_name:
			print "Please install these dependencies using the command:"

			if "ubuntu" in distro_name and distro[1]=="12.04":
				print "sudo apt-get install -y libtiff4-dev libjpeg8-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.5-dev tk8.5-dev python-tk"
			else:
				print "sudo apt-get install -y libtiff5-dev libjpeg8-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python-tk"

			raise

def get_bench_name(bench_path):
	return os.path.basename(os.path.abspath(bench_path))
