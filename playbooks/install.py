# wget setup_frappe.py | python
import os, sys, subprocess, getpass, json, multiprocessing, shutil
from distutils.spawn import find_executable

tmp_bench_repo = '/tmp/.bench'

def install_bench(args):
	# pre-requisites for bench repo cloning
	install_package('curl')
	install_package('wget')

	success = run_os_command({
		'apt-get': [
			'sudo apt-get update',
			'sudo apt-get install -y git build-essential python-setuptools python-dev libffi-dev libssl-dev'
		],
		'yum': [
			'sudo yum groupinstall -y "Development tools"',
			'sudo yum install -y epel-release redhat-lsb-core git python-setuptools python-devel openssl-devel libffi-devel'
		],
		# epel-release is required to install redis, so installing it before the playbook-run.
		# redhat-lsb-core is required, so that ansible can set ansible_lsb variable
	})

	if not find_executable("git"):
		success = run_os_command({
			'brew': 'brew install git'
		})

	if not success:
		print 'Could not install pre-requisites. Please check for errors or install them manually.'
		return

	# secure pip installation
	if find_executable('pip'):
		run_os_command({
			'yum': 'sudo pip install --upgrade setuptools pip',
			'apt-get': 'sudo pip install --upgrade setuptools pip',
			'brew': "sudo pip install --upgrade setuptools pip --user"
		})

	else:
		if not os.path.exists("get-pip.py"):
			run_os_command({
				'apt-get': 'wget https://bootstrap.pypa.io/get-pip.py',
				'yum': 'wget https://bootstrap.pypa.io/get-pip.py'
			})

		success = run_os_command({
			'apt-get': 'sudo python get-pip.py',
			'yum': 'sudo python get-pip.py',
		})

		if success:
			run_os_command({
				'pip': 'sudo pip install --upgrade pip setuptools',
			})

	# Restricting ansible version due to following bug in ansible 2.1
	# https://github.com/ansible/ansible-modules-core/issues/3752
	success = run_os_command({
		'pip': "sudo pip install 'ansible==2.0.2.0'"
	})

	if not success:
		could_not_install('Ansible')

	# clone bench repo
	if not args.run_travis:
		clone_bench_repo(args)

	if not args.user:
		if args.production:
			args.user = 'frappe'

		elif os.environ.has_key('SUDO_USER'):
			args.user = os.environ['SUDO_USER']

		else:
			args.user = getpass.getuser()

	if args.user == 'root':
		raise Exception('Please run this script as a non-root user with sudo privileges, but without using sudo or pass --user=USER')

	# create user if not exists
	extra_vars = vars(args)
	extra_vars.update(frappe_user=args.user)

	run_playbook('develop/create_user.yml', extra_vars=extra_vars)

	extra_vars.update(get_passwords(args.run_travis))
	if args.production:
		extra_vars.update(max_worker_connections=multiprocessing.cpu_count() * 1024)

	branch = 'master' if args.production else 'develop'
	extra_vars.update(branch=branch)

	if args.develop:
		run_playbook('develop/install.yml', sudo=True, extra_vars=extra_vars)

	elif args.production:
		run_playbook('production/install.yml', sudo=True, extra_vars=extra_vars)

	if os.path.exists(tmp_bench_repo):
		shutil.rmtree(tmp_bench_repo)

def install_python27():
	version = (sys.version_info[0], sys.version_info[1])

	if version == (2, 7):
		return

	print 'Installing Python 2.7'

	# install python 2.7
	success = run_os_command({
		'apt-get': 'sudo apt-get install -y python2.7',
		'yum': 'sudo yum install -y python27',
		'brew': 'brew install python'
	})

	if not success:
		could_not_install('Python 2.7')

	# replace current python with python2.7
	os.execvp('python2.7', ([] if is_sudo_user() else ['sudo']) + ['python2.7', __file__] + sys.argv[1:])

def install_package(package):
	package_exec = find_executable(package)

	if not package_exec:
		success = run_os_command({
			'apt-get': ['sudo apt-get install -y {0}'.format(package)],
			'yum': ['sudo yum install -y {0}'.format(package)]
		})
	else:
		return

	if not success:
		could_not_install(package)

def clone_bench_repo(args):
	'''Clones the bench repository in the user folder'''
	if os.path.exists(tmp_bench_repo):
		return 0

	branch = args.bench_branch or 'master'
	repo_url = args.repo_url or 'https://github.com/frappe/bench'

	success = run_os_command(
		{'git': 'git clone {repo_url} {bench_repo} --depth 1 --branch {branch}'.format(
			repo_url=repo_url, bench_repo=tmp_bench_repo, branch=branch)}
	)

	return success

def run_os_command(command_map):
	'''command_map is a dictionary of {'executable': command}. For ex. {'apt-get': 'sudo apt-get install -y python2.7'} '''
	success = True
	for executable, commands in command_map.items():
		if find_executable(executable):
			if isinstance(commands, basestring):
				commands = [commands]

			for command in commands:
				returncode = subprocess.check_call(command, shell=True)
				success = success and ( returncode == 0 )

			break

	return success

def could_not_install(package):
	raise Exception('Could not install {0}. Please install it manually.'.format(package))

def is_sudo_user():
	return os.geteuid() == 0

def get_passwords(run_travis=False):
	if not run_travis:
		mysql_root_password, admin_password = '', ''
		pass_set = True
		while pass_set:
			# mysql root password
			if not mysql_root_password:
				mysql_root_password = getpass.unix_getpass(prompt='Please enter mysql root password: ')
				conf_mysql_passwd = getpass.unix_getpass(prompt='Re-enter mysql root password: ')

				if mysql_root_password != conf_mysql_passwd:
					mysql_root_password = ''
					continue

			# admin password
			if not admin_password:
				admin_password = getpass.unix_getpass(prompt='Please enter Administrator password: ')
				conf_admin_passswd = getpass.unix_getpass(prompt='Re-enter Administrator password: ')

				if admin_password != conf_admin_passswd:
					admin_password = ''
					continue

			pass_set = False
	else:
		mysql_root_password = admin_password = 'travis'

	return {
		'mysql_root_password': mysql_root_password,
		'admin_password': admin_password
	}

def get_extra_vars_json(extra_args):
	# We need to pass production as extra_vars to the playbook to execute conditionals in the
	# playbook. Extra variables can passed as json or key=value pair. Here, we will use JSON.
	json_path = os.path.join('/tmp', 'extra_vars.json')
	extra_vars = dict(extra_args.items())
	with open(json_path, mode='w') as j:
		json.dump(extra_vars, j, indent=1, sort_keys=True)

	return ('@' + json_path)

def run_playbook(playbook_name, sudo=False, extra_vars=None):
	args = ['ansible-playbook', '-c', 'local',  playbook_name]

	if extra_vars:
		args.extend(['-e', get_extra_vars_json(extra_vars)])

		if extra_vars.get('verbosity'):
			args.append('-vvvv')

	if sudo:
		user = extra_vars.get('user') or getpass.getuser()
		args.extend(['--become', '--become-user={0}'.format(user)])

	success = subprocess.check_call(args, cwd=os.path.join(tmp_bench_repo, 'playbooks'))
	return success

def parse_commandline_args():
	import argparse

	parser = argparse.ArgumentParser(description='Frappe Installer')

	# Arguments develop and production are mutually exclusive both can't be specified together.
	# Hence, we need to create a group for discouraging use of both options at the same time.
	args_group = parser.add_mutually_exclusive_group()

	args_group.add_argument('--develop', dest='develop', action='store_true', default=False,
		help='Install developer setup')

	args_group.add_argument('--production', dest='production', action='store_true',
		default=False, help='Setup Production environment for bench')

	parser.add_argument('--site', dest='site', action='store', default='site1.local',
		help='Specifiy name for your first ERPNext site')

	parser.add_argument('--verbose', dest='verbosity', action='store_true', default=False,
		help='Run the script in verbose mode')

	parser.add_argument('--user', dest='user', help='Install frappe-bench for this user')

	parser.add_argument('--bench-branch', dest='bench_branch', help='Clone a particular branch of bench repository')

	parser.add_argument('--repo-url', dest='repo_url', help='Clone bench from the given url')

	# To enable testing of script using Travis, this should skip the prompt
	parser.add_argument('--run-travis', dest='run_travis', action='store_true', default=False,
		help=argparse.SUPPRESS)

	args = parser.parse_args()

	return args

if __name__ == '__main__':
	try:
		import argparse
	except ImportError:
		# install python2.7
		install_python27()

	args = parse_commandline_args()

	install_bench(args)
