import os, sys, shutil, subprocess, logging, itertools, requests, json, platform, select, pwd, grp, multiprocessing
from distutils.spawn import find_executable
import bench
from bench import env

class PatchError(Exception):
	pass

class CommandFailedError(Exception):
	pass

logger = logging.getLogger(__name__)

folders_in_bench = ('apps', 'sites', 'config', 'logs', 'config/pids')

def get_frappe(bench_path='.'):
	frappe = get_env_cmd('frappe', bench_path=bench_path)
	if not os.path.exists(frappe):
		print 'frappe app is not installed. Run the following command to install frappe'
		print 'bench get-app https://github.com/frappe/frappe.git'
	return frappe

def get_env_cmd(cmd, bench_path='.'):
	return os.path.abspath(os.path.join(bench_path, 'env', 'bin', cmd))

def init(path, apps_path=None, no_procfile=False, no_backups=False,
		no_auto_update=False, frappe_path=None, frappe_branch=None, wheel_cache_dir=None,
		verbose=False):
	from .app import get_app, install_apps_from_path
	from .config.common_site_config import make_config
	from .config import redis
	from .config.procfile import setup_procfile
	from bench.patches import set_all_patches_executed

	if os.path.exists(path):
		print 'Directory {} already exists!'.format(path)
		raise Exception("Site directory already exists")
		# sys.exit(1)

	os.makedirs(path)
	for dirname in folders_in_bench:
		os.mkdir(os.path.join(path, dirname))

	setup_logging()

	setup_env(bench_path=path)

	make_config(path)

	if not frappe_path:
		frappe_path = 'https://github.com/frappe/frappe.git'

	get_app(frappe_path, branch=frappe_branch, bench_path=path, build_asset_files=False, verbose=verbose)

	if apps_path:
		install_apps_from_path(apps_path, bench_path=path)

	bench.set_frappe_version(bench_path=path)
	if bench.FRAPPE_VERSION > 5:
		setup_socketio(bench_path=path)

	set_all_patches_executed(bench_path=path)
	build_assets(bench_path=path)
	redis.generate_config(path)

	if not no_procfile:
		setup_procfile(path)
	if not no_backups:
		setup_backups(bench_path=path)
	if not no_auto_update:
		setup_auto_update(bench_path=path)


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

def setup_env(bench_path='.'):
	exec_cmd('virtualenv -q {} -p {}'.format('env', sys.executable), cwd=bench_path)
	exec_cmd('./env/bin/pip -q install --upgrade pip', cwd=bench_path)
	exec_cmd('./env/bin/pip -q install wheel', cwd=bench_path)
	# exec_cmd('./env/bin/pip -q install https://github.com/frappe/MySQLdb1/archive/MySQLdb-1.2.5-patched.tar.gz', cwd=bench_path)
	exec_cmd('./env/bin/pip -q install -e git+https://github.com/frappe/python-pdfkit.git#egg=pdfkit', cwd=bench_path)

def setup_socketio(bench_path='.'):
	exec_cmd("npm install socket.io redis express superagent cookie", cwd=bench_path)

def new_site(site, mariadb_root_password=None, admin_password=None, bench_path='.'):
	import hashlib
	logger.info('creating new site {}'.format(site))
	mariadb_root_password_fragment = '--root_password {}'.format(mariadb_root_password) if mariadb_root_password else ''
	admin_password_fragment = '--admin_password {}'.format(admin_password) if admin_password else ''
	exec_cmd("{frappe} {site} --install {db_name} {mariadb_root_password_fragment} {admin_password_fragment}".format(
				frappe=get_frappe(bench_path=bench_path),
				site=site,
				db_name = hashlib.sha1(site).hexdigest()[:10],
				mariadb_root_password_fragment=mariadb_root_password_fragment,
				admin_password_fragment=admin_password_fragment
			), cwd=os.path.join(bench_path, 'sites'))
	if len(get_sites(bench_path=bench_path)) == 1:
		exec_cmd("{frappe} --use {site}".format(frappe=get_frappe(bench_path=bench_path), site=site), cwd=os.path.join(bench_path, 'sites'))

def patch_sites(bench_path='.'):
	bench.set_frappe_version(bench_path=bench_path)

	try:
		if bench.FRAPPE_VERSION == 4:
			exec_cmd("{frappe} --latest all".format(frappe=get_frappe(bench_path=bench_path)), cwd=os.path.join(bench_path, 'sites'))
		else:
			run_frappe_cmd('--site', 'all', 'migrate', bench_path=bench_path)
	except subprocess.CalledProcessError:
		raise PatchError

def build_assets(bench_path='.'):
	bench.set_frappe_version(bench_path=bench_path)

	if bench.FRAPPE_VERSION == 4:
		exec_cmd("{frappe} --build".format(frappe=get_frappe(bench_path=bench_path)), cwd=os.path.join(bench_path, 'sites'))
	else:
		run_frappe_cmd('build', bench_path=bench_path)

def get_sites(bench_path='.'):
	sites_dir = os.path.join(bench_path, "sites")
	sites = [site for site in os.listdir(sites_dir)
		if os.path.isdir(os.path.join(sites_dir, site)) and site not in ('assets',)]
	return sites

def get_sites_dir(bench_path='.'):
	return os.path.abspath(os.path.join(bench_path, 'sites'))

def get_bench_dir(bench_path='.'):
	return os.path.abspath(bench_path)

def setup_auto_update(bench_path='.'):
	logger.info('setting up auto update')
	add_to_crontab('0 10 * * * cd {bench_dir} &&  {bench} update --auto >> {logfile} 2>&1'.format(bench_dir=get_bench_dir(bench_path=bench_path),
		bench=os.path.join(get_bench_dir(bench_path=bench_path), 'env', 'bin', 'bench'),
		logfile=os.path.join(get_bench_dir(bench_path=bench_path), 'logs', 'auto_update_log.log')))

def setup_backups(bench_path='.'):
	logger.info('setting up backups')
	bench_dir = get_bench_dir(bench_path=bench_path)
	bench.set_frappe_version(bench_path=bench_path)

	if bench.FRAPPE_VERSION == 4:
		backup_command = "cd {sites_dir} && {frappe} --backup all".format(frappe=get_frappe(bench_path=bench_path),)
	else:
		backup_command = "cd {bench_dir} && {bench} --site all backup".format(bench_dir=bench_dir, bench=sys.argv[0])

	add_to_crontab('0 */6 * * *  {backup_command} >> {logfile} 2>&1'.format(backup_command=backup_command,
		logfile=os.path.join(get_bench_dir(bench_path=bench_path), 'logs', 'backup.log')))

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
	if not os.path.exists('/etc/sudoers.d'):
		os.makedirs('/etc/sudoers.d')

		set_permissions = False
		if not os.path.exists('/etc/sudoers'):
			set_permissions = True

		with open('/etc/sudoers', 'a') as f:
			f.write('\n#includedir /etc/sudoers.d\n')

		if set_permissions:
			os.chmod('/etc/sudoers', 0440)

	sudoers_file = '/etc/sudoers.d/frappe'

	template = env.get_template('frappe_sudoers')
	frappe_sudoers = template.render(**{
		'user': user,
		'service': find_executable('service'),
		'systemctl': find_executable('systemctl'),
		'supervisorctl': find_executable('supervisorctl'),
		'nginx': find_executable('nginx'),
		'bench': find_executable('bench')
	})

	with open(sudoers_file, 'w') as f:
		f.write(frappe_sudoers.encode('utf-8'))

	os.chmod(sudoers_file, 0440)

def setup_logging(bench_path='.'):
	if os.path.exists(os.path.join(bench_path, 'logs')):
		logger = logging.getLogger('bench')
		log_file = os.path.join(bench_path, 'logs', 'bench.log')
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

def restart_supervisor_processes(bench_path='.'):
	from .config.common_site_config import get_config
	conf = get_config(bench_path=bench_path)
	bench_name = get_bench_name(bench_path)

	cmd = conf.get('supervisor_restart_cmd')
	if cmd:
		exec_cmd(cmd, cwd=bench_path)

	else:
		supervisor_status = subprocess.check_output(['sudo', 'supervisorctl', 'status'], cwd=bench_path)

		if '{bench_name}-workers:'.format(bench_name=bench_name) in supervisor_status:
			group = '{bench_name}-workers: {bench_name}-web:'.format(bench_name=bench_name)

		# backward compatibility
		elif '{bench_name}-processes:'.format(bench_name=bench_name) in supervisor_status:
			group = '{bench_name}-processes:'.format(bench_name=bench_name)

		# backward compatibility
		else:
			group = 'frappe:'

		exec_cmd('sudo supervisorctl restart {group}'.format(group=group), cwd=bench_path)

def set_default_site(site, bench_path='.'):
	if not site in get_sites(bench_path=bench_path):
		raise Exception("Site not in bench")
	exec_cmd("{frappe} --use {site}".format(frappe=get_frappe(bench_path=bench_path), site=site),
			cwd=os.path.join(bench_path, 'sites'))

def update_requirements(bench_path='.'):
	pip = os.path.join(bench_path, 'env', 'bin', 'pip')

	# upgrade pip to latest
	exec_cmd("{pip} install --upgrade pip".format(pip=pip))

	apps_dir = os.path.join(bench_path, 'apps')

	# Update bench requirements
	bench_req_file = os.path.join(os.path.dirname(bench.__path__[0]), 'requirements.txt')
	install_requirements(pip, bench_req_file)

	for app in os.listdir(apps_dir):
		req_file = os.path.join(apps_dir, app, 'requirements.txt')
		install_requirements(pip, req_file)

def install_requirements(pip, req_file):
	if os.path.exists(req_file):
		exec_cmd("{pip} install -q -r {req_file}".format(pip=pip, req_file=req_file))

def backup_site(site, bench_path='.'):
	bench.set_frappe_version(bench_path=bench_path)

	if bench.FRAPPE_VERSION == 4:
		exec_cmd("{frappe} --backup {site}".format(frappe=get_frappe(bench_path=bench_path), site=site),
				cwd=os.path.join(bench_path, 'sites'))
	else:
		run_frappe_cmd('--site', site, 'backup', bench_path=bench_path)

def backup_all_sites(bench_path='.'):
	for site in get_sites(bench_path=bench_path):
		backup_site(site, bench_path=bench_path)

def is_root():
	if os.getuid() == 0:
		return True
	return False

def set_mariadb_host(host, bench_path='.'):
	update_common_site_config({'db_host': host}, bench_path=bench_path)

def update_common_site_config(ddict, bench_path='.'):
	update_json_file(os.path.join(bench_path, 'sites', 'common_site_config.json'), ddict)

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

def fix_prod_setup_perms(bench_path='.', frappe_user=None):
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
		frappe_user = get_config(bench_path).get('frappe_user')

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

def get_current_frappe_version(bench_path='.'):
	from .app import get_current_frappe_version as fv
	return fv(bench_path=bench_path)

def run_frappe_cmd(*args, **kwargs):
	from .cli import from_command_line

	bench_path = kwargs.get('bench_path', '.')
	f = get_env_cmd('python', bench_path=bench_path)
	sites_dir = os.path.join(bench_path, 'sites')

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
	bench_path = kwargs.get('bench_path', '.')
	f = get_env_cmd('python', bench_path=bench_path)
	sites_dir = os.path.join(bench_path, 'sites')
	return subprocess.check_output((f, '-m', 'frappe.utils.bench_helper', 'frappe') + args, cwd=sites_dir)

def validate_upgrade(from_ver, to_ver, bench_path='.'):
	if to_ver >= 6:
		if not find_executable('npm') and not (find_executable('node') or find_executable('nodejs')):
			raise Exception("Please install nodejs and npm")

def pre_upgrade(from_ver, to_ver, bench_path='.'):
	pip = os.path.join(bench_path, 'env', 'bin', 'pip')

	if from_ver <= 4 and to_ver >= 5:
		from .migrate_to_v5 import remove_shopping_cart
		apps = ('frappe', 'erpnext')
		remove_shopping_cart(bench_path=bench_path)

		for app in apps:
			cwd = os.path.abspath(os.path.join(bench_path, 'apps', app))
			if os.path.exists(cwd):
				exec_cmd("git clean -dxf", cwd=cwd)
				exec_cmd("{pip} install --upgrade -e {app}".format(pip=pip, app=cwd))

def post_upgrade(from_ver, to_ver, bench_path='.'):
	from .config.common_site_config import get_config
	from .config import redis
	from .config.supervisor import generate_supervisor_config
	from .config.nginx import make_nginx_conf
	conf = get_config(bench_path=bench_path)
	print "-"*80
	print "Your bench was upgraded to version {0}".format(to_ver)

	if conf.get('restart_supervisor_on_update'):
		redis.generate_config(bench_path=bench_path)
		generate_supervisor_config(bench_path=bench_path)
		make_nginx_conf(bench_path=bench_path)

		if from_ver == 4 and to_ver == 5:
			setup_backups(bench_path=bench_path)

		if from_ver <= 5 and to_ver == 6:
			setup_socketio(bench_path=bench_path)

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

def before_update(bench_path, requirements):
	validate_pillow_dependencies(bench_path, requirements)

def validate_pillow_dependencies(bench_path, requirements):
	if not requirements:
		return

	try:
		pip = os.path.join(bench_path, 'env', 'bin', 'pip')
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

def setup_fonts():
	fonts_path = os.path.join('/tmp', 'fonts')

	if os.path.exists('/etc/fonts_backup'):
		return

	exec_cmd("git clone https://github.com/frappe/fonts.git", cwd='/tmp')
	os.rename('/etc/fonts', '/etc/fonts_backup')
	os.rename('/usr/share/fonts', '/usr/share/fonts_backup')
	os.rename(os.path.join(fonts_path, 'etc_fonts'), '/etc/fonts')
	os.rename(os.path.join(fonts_path, 'usr_share_fonts'), '/usr/share/fonts')
	shutil.rmtree(fonts_path)
	exec_cmd("fc-cache -fv")
