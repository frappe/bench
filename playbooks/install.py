#!/usr/bin/env python3
from __future__ import print_function
import os
import sys
import subprocess
import getpass
import json
import multiprocessing
import shutil
import platform
import warnings
import datetime


tmp_bench_repo = os.path.join('/', 'tmp', '.bench')
tmp_log_folder = os.path.join('/', 'tmp', 'logs')
execution_timestamp = datetime.datetime.utcnow()
execution_day = "{:%Y-%m-%d}".format(execution_timestamp)
execution_time = "{:%H:%M}".format(execution_timestamp)
log_file_name = "easy-install__{0}__{1}.log".format(execution_day, execution_time.replace(':', '-'))
log_path = os.path.join(tmp_log_folder, log_file_name)
log_stream = sys.stdout


def log(message, level=0):
	levels = {
		0: '\033[94m',	# normal
		1: '\033[92m',	# success
		2: '\033[91m',	# fail
		3: '\033[93m'	# warn/suggest
	}
	start = levels.get(level) or ''
	end = '\033[0m'
	print(start + message + end)


def setup_log_stream(args):
	global log_stream
	sys.stderr = sys.stdout

	if not args.verbose:
		if not os.path.exists(tmp_log_folder):
			os.makedirs(tmp_log_folder)
		log_stream = open(log_path, 'w')
		log("Logs are saved under {0}".format(log_path), level=3)
		print("Install script run at {0} on {1}\n\n".format(execution_time, execution_day), file=log_stream)


def check_environment():
	needed_environ_vars = ['LANG', 'LC_ALL']
	message = ''

	for var in needed_environ_vars:
		if var not in os.environ:
			message += "\nexport {0}=C.UTF-8".format(var)

	if message:
		log("Bench's CLI needs these to be defined!", level=3)
		log("Run the following commands in shell: {0}".format(message), level=2)
		sys.exit()


def check_system_package_managers():
	if 'Darwin' in os.uname():
		if not shutil.which('brew'):
			raise Exception('''
			Please install brew package manager before proceeding with bench setup. Please run following
			to install brew package manager on your machine,

			/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
			''')
	if 'Linux' in os.uname():
		if not any([shutil.which(x) for x in ['apt-get', 'yum']]):
			raise Exception('Cannot find any compatible package manager!')


def check_distribution_compatibility():
	dist_name, dist_version = get_distribution_info()
	supported_dists = {
		'macos': [10.9, 10.10, 10.11, 10.12],
		'ubuntu': [14, 15, 16, 18, 19],
		'debian': [8, 9],
		'centos': [7]
	}

	log("Checking System Compatibility...")
	if dist_name in supported_dists:
		if float(dist_version) in supported_dists[dist_name]:
			log("{0} {1} is compatible!".format(dist_name, dist_version), level=1)
		else:
			log("{0} {1} is detected".format(dist_name, dist_version), level=1)
			log("Install on {0} {1} instead".format(dist_name, supported_dists[dist_name][-1]), level=3)
	else:
		log("Sorry, the installer doesn't support {0}. Aborting installation!".format(dist_name), level=2)


def get_distribution_info():
	# return distribution name and major version
	if platform.system() == "Linux":
		current_dist = platform.dist()
		return current_dist[0].lower(), current_dist[1].rsplit('.')[0]

	elif platform.system() == "Darwin":
		current_dist = platform.mac_ver()
		return "macos", current_dist[0].rsplit('.', 1)[0]


def run_os_command(command_map):
	'''command_map is a dictionary of {'executable': command}. For ex. {'apt-get': 'sudo apt-get install -y python2.7'}'''
	success = True

	for executable, commands in command_map.items():
		if shutil.which(executable):
			if isinstance(commands, str):
				commands = [commands]

			for command in commands:
				returncode = subprocess.check_call(command, shell=True, stdout=log_stream, stderr=sys.stderr)
				success = success and (returncode == 0)

	return success


def install_prerequisites():
	# pre-requisites for bench repo cloning
	run_os_command({
		'apt-get': [
			'sudo apt-get update',
			'sudo apt-get install -y git build-essential python3-setuptools python3-dev libffi-dev'
		],
		'yum': [
			'sudo yum groupinstall -y "Development tools"',
			'sudo yum install -y epel-release redhat-lsb-core git python-setuptools python-devel openssl-devel libffi-devel'
		]
	})

	install_package('curl')
	install_package('wget')
	install_package('git')
	install_package('pip3', 'python3-pip')

	success = run_os_command({
		'python3': "sudo -H python3 -m pip install --upgrade setuptools cryptography ansible==2.8.5 pip"
	})

	if not (success or shutil.which('ansible')):
		could_not_install('Ansible')


def could_not_install(package):
	raise Exception('Could not install {0}. Please install it manually.'.format(package))


def is_sudo_user():
	return os.geteuid() == 0


def install_package(package, package_name=None):
	if shutil.which(package):
		log("{0} already installed!".format(package), level=1)
	else:
		log("Installing {0}...".format(package))
		package_name = package_name or package
		success = run_os_command({
			'apt-get': ['sudo apt-get install -y {0}'.format(package_name)],
			'yum': ['sudo yum install -y {0}'.format(package_name)],
			'brew': ['brew install {0}'.format(package_name)]
		})
		if success:
			log("{0} installed!".format(package), level=1)
			return success
		could_not_install(package)


def install_bench(args):
	# clone bench repo
	if not args.run_travis:
		clone_bench_repo(args)

	if not args.user:
		if args.production:
			args.user = 'frappe'

		elif 'SUDO_USER' in os.environ:
			args.user = os.environ['SUDO_USER']

		else:
			args.user = getpass.getuser()

	if args.user == 'root':
		raise Exception('Please run this script as a non-root user with sudo privileges, but without using sudo or pass --user=USER')

	# Python executable
	dist_name, dist_version = get_distribution_info()
	if dist_name=='centos':
		args.python = 'python3.6'
	else:
		args.python = 'python3'

	# create user if not exists
	extra_vars = vars(args)
	extra_vars.update(frappe_user=args.user)

	if os.path.exists(tmp_bench_repo):
		repo_path = tmp_bench_repo

	else:
		repo_path = os.path.join(os.path.expanduser('~'), 'bench')

	extra_vars.update(repo_path=repo_path)
	run_playbook('create_user.yml', extra_vars=extra_vars)

	extra_vars.update(get_passwords(args))
	if args.production:
		extra_vars.update(max_worker_connections=multiprocessing.cpu_count() * 1024)

	frappe_branch = 'version-12'
	erpnext_branch = 'version-12'

	if args.version:
		if args.version <= 10:
			frappe_branch = "{0}.x.x".format(args.version)
			erpnext_branch = "{0}.x.x".format(args.version)
		else:
			frappe_branch = "version-{0}".format(args.version)
			erpnext_branch = "version-{0}".format(args.version)
	else:
		if args.frappe_branch:
			frappe_branch = args.frappe_branch

		if args.erpnext_branch:
			erpnext_branch = args.erpnext_branch

	extra_vars.update(frappe_branch=frappe_branch)
	extra_vars.update(erpnext_branch=erpnext_branch)

	bench_name = 'frappe-bench' if not args.bench_name else args.bench_name
	extra_vars.update(bench_name=bench_name)

	# Will install ERPNext production setup by default
	run_playbook('site.yml', sudo=True, extra_vars=extra_vars)

	if os.path.exists(tmp_bench_repo):
		shutil.rmtree(tmp_bench_repo)


def clone_bench_repo(args):
	'''Clones the bench repository in the user folder'''
	branch = args.bench_branch or 'master'
	repo_url = args.repo_url or 'https://github.com/frappe/bench'

	if os.path.exists(tmp_bench_repo):
		return 0
	elif args.without_bench_setup:
		clone_path = os.path.join(os.path.expanduser('~'), 'bench')
	else:
		clone_path = tmp_bench_repo

	success = run_os_command(
		{'git': 'git clone --quiet {repo_url} {bench_repo} --depth 1 --branch {branch}'.format(
			repo_url=repo_url, bench_repo=clone_path, branch=branch)}
	)

	return success


def passwords_didnt_match(context=''):
	log("{} passwords did not match!".format(context), level=3)


def get_passwords(args):
	"""
	Returns a dict of passwords for further use
	and creates passwords.txt in the bench user's home directory
	"""
	log("Input MySQL and Frappe Administrator passwords:")
	ignore_prompt = args.run_travis or args.without_bench_setup
	mysql_root_password, admin_password = '', ''
	passwords_file_path = os.path.join(os.path.expanduser('~' + args.user), 'passwords.txt')

	if not ignore_prompt:
		# set passwords from existing passwords.txt
		if os.path.isfile(passwords_file_path):
			with open(passwords_file_path, 'r') as f:
				passwords = json.load(f)
				mysql_root_password, admin_password = passwords['mysql_root_password'], passwords['admin_password']

		# set passwords from cli args
		if args.mysql_root_password:
			mysql_root_password = args.mysql_root_password
		if args.admin_password:
			admin_password = args.admin_password

		# prompt for passwords
		pass_set = True
		while pass_set:
			# mysql root password
			if not mysql_root_password:
				mysql_root_password = getpass.unix_getpass(prompt='Please enter mysql root password: ')
				conf_mysql_passwd = getpass.unix_getpass(prompt='Re-enter mysql root password: ')

				if mysql_root_password != conf_mysql_passwd or mysql_root_password == '':
					passwords_didnt_match("MySQL")
					mysql_root_password = ''
					continue

			# admin password
			if not admin_password:
				admin_password = getpass.unix_getpass(prompt='Please enter the default Administrator user password: ')
				conf_admin_passswd = getpass.unix_getpass(prompt='Re-enter Administrator password: ')

				if admin_password != conf_admin_passswd or admin_password == '':
					passwords_didnt_match("Administrator")
					admin_password = ''
					continue

			pass_set = False
	else:
		mysql_root_password = admin_password = 'travis'

	passwords = {
		'mysql_root_password': mysql_root_password,
		'admin_password': admin_password
	}

	if not ignore_prompt:
		with open(passwords_file_path, 'w') as f:
			json.dump(passwords, f, indent=1)

		log('Passwords saved at ~/passwords.txt')

	return passwords


def get_extra_vars_json(extra_args):
	# We need to pass production as extra_vars to the playbook to execute conditionals in the
	# playbook. Extra variables can passed as json or key=value pair. Here, we will use JSON.
	json_path = os.path.join('/', 'tmp', 'extra_vars.json')
	extra_vars = dict(list(extra_args.items()))

	with open(json_path, mode='w') as j:
		json.dump(extra_vars, j, indent=1, sort_keys=True)

	return ('@' + json_path)


def run_playbook(playbook_name, sudo=False, extra_vars=None):
	args = ['ansible-playbook', '-c', 'local',  playbook_name , '-vvvv']

	if extra_vars:
		args.extend(['-e', get_extra_vars_json(extra_vars)])

	if sudo:
		user = extra_vars.get('user') or getpass.getuser()
		args.extend(['--become', '--become-user={0}'.format(user)])

	if os.path.exists(tmp_bench_repo):
		cwd = tmp_bench_repo
	else:
		cwd = os.path.join(os.path.expanduser('~'), 'bench')

	success = subprocess.check_call(args, cwd=os.path.join(cwd, 'playbooks'), stdout=log_stream, stderr=sys.stderr)
	return success


def parse_commandline_args():
	import argparse

	parser = argparse.ArgumentParser(description='Frappe Installer')
	# Arguments develop and production are mutually exclusive both can't be specified together.
	# Hence, we need to create a group for discouraging use of both options at the same time.
	args_group = parser.add_mutually_exclusive_group()

	args_group.add_argument('--develop', dest='develop', action='store_true', default=False, help='Install developer setup')
	args_group.add_argument('--production', dest='production', action='store_true', default=False, help='Setup Production environment for bench')
	parser.add_argument('--site', dest='site', action='store', default='site1.local', help='Specifiy name for your first ERPNext site')
	parser.add_argument('--without-site', dest='without_site', action='store_true', default=False)
	parser.add_argument('--verbose', dest='verbose', action='store_true', default=False, help='Run the script in verbose mode')
	parser.add_argument('--user', dest='user', help='Install frappe-bench for this user')
	parser.add_argument('--bench-branch', dest='bench_branch', help='Clone a particular branch of bench repository')
	parser.add_argument('--repo-url', dest='repo_url', help='Clone bench from the given url')
	parser.add_argument('--frappe-repo-url', dest='frappe_repo_url', action='store', default='https://github.com/frappe/frappe', help='Clone frappe from the given url')
	parser.add_argument('--frappe-branch', dest='frappe_branch', action='store', help='Clone a particular branch of frappe')
	parser.add_argument('--erpnext-repo-url', dest='erpnext_repo_url', action='store', default='https://github.com/frappe/erpnext', help='Clone erpnext from the given url')
	parser.add_argument('--erpnext-branch', dest='erpnext_branch', action='store', help='Clone a particular branch of erpnext')
	parser.add_argument('--without-erpnext', dest='without_erpnext', action='store_true', default=False, help='Prevent fetching ERPNext')
	# direct provision to install versions
	parser.add_argument('--version', dest='version', action='store', default='12', type=int, help='Clone particular version of frappe and erpnext')
	# To enable testing of script using Travis, this should skip the prompt
	parser.add_argument('--run-travis', dest='run_travis', action='store_true', default=False, help=argparse.SUPPRESS)
	parser.add_argument('--without-bench-setup', dest='without_bench_setup', action='store_true', default=False, help=argparse.SUPPRESS)
	# whether to overwrite an existing bench
	parser.add_argument('--overwrite', dest='overwrite', action='store_true', default=False, help='Whether to overwrite an existing bench')
	# set passwords
	parser.add_argument('--mysql-root-password', dest='mysql_root_password', help='Set mysql root password')
	parser.add_argument('--mariadb-version', dest='mariadb_version', default='10.2', help='Specify mariadb version')
	parser.add_argument('--admin-password', dest='admin_password', help='Set admin password')
	parser.add_argument('--bench-name', dest='bench_name', help='Create bench with specified name. Default name is frappe-bench')
	# Python interpreter to be used
	parser.add_argument('--python', dest='python', default='python3', help=argparse.SUPPRESS)
	# LXC Support
	parser.add_argument('--container', dest='container', default=False, action='store_true', help='Use if you\'re creating inside LXC')
	args = parser.parse_args()

	return args

if __name__ == '__main__':
	if sys.version[0] == '2':
		if not os.environ.get('CI'):
			if not raw_input("It is recommended to run this script with Python 3\nDo you still wish to continue? [Y/n]: ").lower() == "y":
				sys.exit()

		try:
			from distutils.spawn import find_executable
		except ImportError:
			try:
				subprocess.check_call('pip install --upgrade setuptools')
			except subprocess.CalledProcessError:
				print("Install distutils or use Python3 to run the script")
				sys.exit(1)

		shutil.which = find_executable

	if not is_sudo_user():
		log("Please run this script as a non-root user with sudo privileges", level=3)
		sys.exit()

	args = parse_commandline_args()

	with warnings.catch_warnings():
		warnings.simplefilter("ignore")
		setup_log_stream(args)
		check_distribution_compatibility()
		check_system_package_managers()
		check_environment()
		install_prerequisites()
		install_bench(args)

	log("Bench + Frappe + ERPNext has been successfully installed!")
