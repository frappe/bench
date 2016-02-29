# wget setup_frappe.py | python
import os
import sys
import pwd
import stat
import subprocess
from distutils.spawn import find_executable
import string
from random import choice

def install_bench(args):
	# pre-requisites for bench repo cloning
	install_git()

	# which user to use for bench repo cloning
	user_password = add_user(args.user)

	# clone bench repo!

	# install pip

	# install bench

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

def parse_commandline_args():
	import argparse

	parser = argparse.ArgumentParser(description='Frappe Installer')
	parser.add_argument('--user', metavar='USER', dest='user', action='store',
						help="System user which will be used to start various processes required by Frappe framework. If this user doesn't exist, it will be created.")

	args = parser.parse_args()

	return args

if __name__ == "__main__":
	try:
		import argparse
	except ImportError:
		# install python2.7
		install_python27()

	args = parse_commandline_args()

	install_bench(args)
