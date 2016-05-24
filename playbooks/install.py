# wget setup_frappe.py | python
import os
import sys
import subprocess
import getpass
import json, multiprocessing
from distutils.spawn import find_executable

bench_repo = '/usr/local/frappe/bench-repo'

def install_bench(args):
	# pre-requisites for bench repo cloning
	success = run_os_command({
		'apt-get': [
			'sudo apt-get update',
			'sudo apt-get install -y git build-essential python-setuptools python-dev libffi-dev libssl-dev'
		],
		'yum': [
			'sudo yum groupinstall -y "Development tools"',
			'sudo yum install -y git python-setuptools python-devel openssl-devel libffi-devel'
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
	if not os.path.exists("get-pip.py"):
		run_os_command({
			'apt-get': 'wget https://bootstrap.pypa.io/get-pip.py',
			'yum': 'wget https://bootstrap.pypa.io/get-pip.py'
		})

	run_os_command({
		'apt-get': 'sudo python get-pip.py',
		'yum': 'sudo python get-pip.py',
	})

	# In some cases setup_tools are not updated, We will force update it.
	run_os_command({
		'pip': 'sudo pip install --upgrade setuptools'
	})

	success = run_os_command({
		'pip': 'sudo pip install ansible'
	})

	if not success:
		could_not_install('Ansible')

	if is_sudo_user():
		raise Exception('Please run this script as a non-root user with sudo privileges, but without using sudo')

	# clone bench repo
	clone_bench_repo()

	# args is namespace, but we would like to use it as dict in calling function, so use vars()
	if args.develop:
		run_playbook('develop/install.yml', sudo=True, extra_args=vars(args))
	elif args.setup_production:
		run_playbook('production/install.yml', sudo=True, extra_args=vars(args))

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

def clone_bench_repo():
	'''Clones the bench repository in the user folder'''

	if os.path.exists(bench_repo):
		return 0

	run_os_command({
		'brew': 'mkdir -p /usr/local/frappe',
		'apt-get': 'sudo mkdir -p /usr/local/frappe',
		'yum': 'sudo mkdir -p /usr/local/frappe',
	})

	# change user
	run_os_command({
		'ls': 'sudo chown -R {user}:{user} /usr/local/frappe'.format(user=getpass.getuser()),
	})

	success = run_os_command(
		{'git': 'git clone https://github.com/shreyasp/bench {bench_repo} --depth 1 --branch test-ansible-installer'.format(bench_repo=bench_repo)}
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

def get_extra_vars_json(extra_args, run_travis=False):
	# We need to pass setup_production as extra_vars to the playbook to execute conditionals in the
	# playbook. Extra variables can passed as json or key=value pair. Here, we will use JSON.
	json_path = os.path.join(os.path.abspath(os.path.expanduser('~')), 'extra_vars.json')
	extra_vars = dict(extra_args.items())

	# Get mysql root password and admin password
	run_travis = extra_args.get('run_travis')
	extra_vars.update(get_passwords(run_travis))

	# Decide for branch to be cloned depending upon whether we setting up production
	branch = 'master' if extra_args.get('setup_production') else 'develop'
	extra_vars.update(branch=branch)

	# Get max worker_connections in nginx.
	# https://www.digitalocean.com/community/tutorials/how-to-optimize-nginx-configuration
	# The amount of clients that can be served can be multiplied by the amount of cores.
 	extra_vars.update(max_worker_connections=multiprocessing.cpu_count() * 1024)

	with open(json_path, mode='w') as j:
		json.dump(extra_vars, j, indent=1, sort_keys=True)

	return ('@' + json_path)

def run_playbook(playbook_name, sudo=False, extra_args=None):
	extra_vars = get_extra_vars_json(extra_args)
	args = ['ansible-playbook', '-c', 'local',  playbook_name, '-e', extra_vars]

	if sudo:
		args.extend(['--become', '--become-user=frappe'])

	if extra_args.get('verbosity'):
		args.append('-vvvv')

	success = subprocess.check_call(args, cwd=os.path.join(bench_repo, 'playbooks'))
	return success

def parse_commandline_args():
	import argparse

	parser = argparse.ArgumentParser(description='Frappe Installer')

	# Arguments develop and setup-production are mutually exclusive both can't be specified together.
	# Hence, we need to create a group for discouraging use of both options at the same time.
	args_group = parser.add_mutually_exclusive_group()

	args_group.add_argument('--develop', dest='develop', action='store_true', default=False,
		help='Install developer setup')

	args_group.add_argument('--setup-production', dest='setup_production', action='store_true',
		default=False, help='Setup Production environment for bench')

	parser.add_argument('--site', dest='site', action='store', default='site1.local',
		help='Specifiy name for your first ERPNext site')

	parser.add_argument('--verbose', dest='verbosity', action='store_true', default=False,
		help='Run the script in verbose mode')

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
