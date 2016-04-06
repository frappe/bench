# wget setup_frappe.py | python
import os
import sys
import subprocess
import getpass
from distutils.spawn import find_executable

bench_repo = '/usr/local/frappe/bench-repo'

def install_bench(args):
	# pre-requisites for bench repo cloning
	success = run_os_command({
		'apt-get': [
			'sudo apt-get update',
			'sudo apt-get install -y git build-essential python-setuptools python-dev'
		],
		'yum': [
			'sudo yum groupinstall -y "Development tools"',
			'sudo yum install -y git python-setuptools python-devel'
		],
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

	success = run_os_command({
		'pip': 'sudo pip install ansible'
	})

	if not success:
		could_not_install('Ansible')

	if is_sudo_user():
		raise Exception('Please run this script as a non-root user with sudo privileges, but without using sudo')

	# clone bench repo
	clone_bench_repo()

	if args.develop:
		run_playbook('develop/install.yml', sudo=True)

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
		{'git': 'git clone https://github.com/frappe/bench {bench_repo} --depth 1'.format(bench_repo=bench_repo)}
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

def run_playbook(playbook_name, sudo=False):
	args = ['ansible-playbook', '-c', 'local',  playbook_name]
	if sudo:
		args.append('-K')

	success = subprocess.check_call(args, cwd=os.path.join(bench_repo, 'playbooks'))
	return success

def parse_commandline_args():
	import argparse

	parser = argparse.ArgumentParser(description='Frappe Installer')
	parser.add_argument('--develop', dest='develop', action='store_true', default=False,
						help='Install developer setup')
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
