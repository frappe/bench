# wget setup_frappe.py | python
import os
import sys
import pwd
import stat
import subprocess
import string

from random import choice
from distutils.spawn import find_executable
from setuptools.command import easy_install as easy_install

def install_bench(args):
	# pre-requisites for bench repo cloning
	install_pip()
	install_ansible()
	install_git()

	# which user to use for bench repo cloning
	user_password = add_user(args.user)

	# stop install
	if args.skip_bench_setup:
		return

	# clone bench repo
	cloned = clone_bench_repo(args.user)

	# install pre-requisites
	installed = install_prerequisites(args.user)

	# install bench
	# if cloned:
	# 	install_bench_cmd(user)

def install_python27():
	version = (sys.version_info[0], sys.version_info[1])

	if version == (2, 7):
		return

	print "Installing Python 2.7"

	# install python 2.7
	success = run_os_command({
		"apt-get": "sudo apt-get install -y python2.7",
		"yum": "sudo yum install -y python27",
		"brew": "brew install python"
	})

	if not success:
		could_not_install("Python 2.7")

	# replace current python with python2.7
	os.execvp("python2.7", ([] if is_sudo_user() else ["sudo"]) + ["python2.7", __file__] + sys.argv[1:])

def install_git():
	if find_executable("git"):
		# git already installed
		return

	print "Installing Git"

	success = run_os_command({
		"apt-get": "sudo apt-get install -y git",
		"yum": "sudo yum install -y git",
		"brew": "brew install git"
	})

	if not success:
		could_not_install("Git")

def add_user(user):
	if user=="root":
		raise Exception("--user cannot be root")
	elif not user:
		raise Exception("Please pass --user USER. For example: --user frappe")

	user_password = None

	try:
		pwd.getpwnam(user)

	except KeyError:
		# user does not exist
		success = run_os_command({
			"adduser": "sudo adduser --create-home {user}".format(user=user)
		})

		if not success:
			raise Exception("Could not create user {0}. Please add the user manually.".format(user))

		user_password = get_random_string()
		subprocess.check_call(["chpasswd", "{user}:{password}".format(user=user, password=user_password)])

	finally:

		# give read and execute rights to "Others" for the user's folder
		user_folder = get_user_folder(user)
		user_folder_stat = os.stat(user_folder)
		os.chmod(user_folder, user_folder_stat.st_mode | stat.S_IROTH)
		os.chmod(user_folder, user_folder_stat.st_mode | stat.S_IXOTH)

		return user_password

def install_pip():
	"""Install pip for the user or upgrade to latest version if already present"""
	try:
		import pip
	except ImportError:
		easy_install.main(['pip'])

def install_ansible():
	try:
		import ansible
	except ImportError:
		import pip
		pip.main(["install", "ansible"])

def clone_bench_repo(user):
	"""Clones the bench repository in the user folder"""
	bench_repo = os.path.join(get_user_folder(user), 'bench-repo')

	success = run_os_command(
		{"git": "git clone https://github.com/frappe/bench {bench_repo}".format(bench_repo=bench_repo)}
	)

	return success

def install_dependencies():
	"""Installs the pre-requisites like mariadb, nginx, redis etc. for the user"""
	playbooks_path = get_playbooks_path()

	for playbook in os.listdir(playbooks_path):
		if playbook.endswith('.yml'):
			success = run_playbook(os.path.join(playbooks_path, playbook))

	return success

def run_os_command(command_map):
	"""command_map is a dictionary of {"executable": command}. For ex. {"apt-get": "sudo apt-get install -y python2.7"} """
	success = False
	for executable, command in command_map.items():
		if find_executable(executable):
			returncode = subprocess.check_call(command.split())
			success = ( returncode == 0 )
			break

	return success

def could_not_install(package):
	raise Exception("Could not install {0}. Please install it manually.".format(package))

def is_sudo_user():
	return os.geteuid() == 0

def get_user_folder(user):
	return os.path.expanduser("~{user}".format(user=user))

def get_random_string(length=16):
	"""generate a random string"""
	return ''.join([choice(string.letters + string.digits) for i in range(length)])

def get_playbooks_path():
	return os.path.abspath(os.path.join(os.getcwd(), 'bench-repo', 'installer', 'playbooks'))

def run_playbook(playbook_name):
	success = subprocess.check_call("{sudo} ansible-playbook -c local {playbook_name}"
		.format(playbook_name=playbook_name, sudo="sudo" if is_sudo_user() else "")
		.split())
	return success

def install_bench_cmd(user):
	"""Installs bench using pip from the bench-repo"""
	pass

def parse_commandline_args():
	import argparse

	parser = argparse.ArgumentParser(description='Frappe Installer')
	parser.add_argument('--user', metavar='USER', dest='user', action='store',
						help="System user which will be used to start various processes required by Frappe framework. If this user doesn't exist, it will be created.")
	parser.add_argument('--skip-bench-setup', dest='skip_bench_setup', action='store_true', default=False,
						help="Skip cloning and installation of bench.")
	parser.add_argument('--only-dependencies', dest='only_dependencies', action='store_true', default=False,
						help="Only install dependencies via ansible")
	args = parser.parse_args()

	return args

if __name__ == "__main__":
	try:
		import argparse
	except ImportError:
		# install python2.7
		install_python27()

	args = parse_commandline_args()

	if args.only_dependencies:
		install_dependencies()

	else:
		install_bench(args)
