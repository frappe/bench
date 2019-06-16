"""
Builds a vm and puts it in ~/public with a latest.json that has its filename and md5sum
"""

# imports - standard imports
import 	os
import 	json
import 	stat
import  errno
from    shutil     import rmtree
from    distutils  import spawn
from 	subprocess import check_output

NEW_FILES  = []
BUILDS     = ['Production', 'Developer']
PUBLIC_DIR = os.path.join(os.path.expanduser('~'), 'Public')
SYMLINKS   = ['ERPNext-Production.ova', 'ERPNext-Dev.ova', 'ERPNext-Vagrant.box',
	'ERPNext-Production.ova.md5', 'ERPNext-Dev.ova.md5', 'ERPNext-Vagrant.box.md5']

def main():
	install_virtualbox()
	install_packer()
	cleanup()
	build_vm()
	generate_md5_hashes()
	generate_symlinks()
	delete_old_vms()
	move_current_vms()
	cleanup()

def install_virtualbox():
	if not spawn.find_executable("virtualbox"):
		check_output(['bench', 'install', 'virtualbox'])

def install_packer():
	if not spawn.find_executable("packer") and not os.path.exists(os.path.join('/', 'opt', 'packer')):
		check_output(['bench', 'install', 'packer'])

def silent_remove(name, is_dir=False):
	'''
	Method to safely remove a file or directory,
	without throwing error if file doesn't exist

	By default takes in file as input, for directory:
	is_dir = True
	'''
	try:
		if is_dir:
			rmtree(name)
		else:
			os.remove(name)
	except OSError as e:
		if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
			raise 					# re-raise exception if a different error occurred

def cleanup():
	silent_remove("Production Builds", is_dir=True)
	silent_remove("Developer Builds", is_dir=True)
	silent_remove("packer_virtualbox-iso_virtualbox-iso_md5.checksum")

def build_vm():
	check_output(["packer", "build", "vm-production.json"])
	check_output(["packer", "build", "vm-develop.json"])

def md5(build, file):
	return check_output("md5sum '{} Builds/{}'".format(build, file), shell=True).split()[0]

def move_to_public(build, file):
	NEW_FILES.append(file)
	src  = os.path.join('{} Builds/{}'.format(build, file))
	dest = os.path.join(PUBLIC_DIR, file)
	os.rename(src, dest)
	# Make Public folder readable by others
	st = os.stat(dest)
	os.chmod(dest, st.st_mode | stat.S_IROTH)

def generate_md5_hashes():
	for build in BUILDS:
		for file in os.listdir('{} Builds'.format(build)):
			if file.endswith(".ova") or file.endswith(".box"):
				with open('{} Builds/{}.md5'.format(build, file), 'w') as f:
					f.write(md5(build, file))
				move_to_public(build, file)
				move_to_public(build, '{}.md5'.format(file))

def generate_symlinks():
	for file in NEW_FILES:
		if 'md5' in file:
			if 'Vagrant' in file:
				silent_remove(os.path.join(PUBLIC_DIR, 'ERPNext-Vagrant.box.md5'))
				os.symlink(os.path.join(PUBLIC_DIR, file),
					os.path.join(PUBLIC_DIR, 'ERPNext-Vagrant.box.md5'))
			elif 'Production' in file:
				silent_remove(os.path.join(PUBLIC_DIR, 'ERPNext-Production.ova.md5'))
				os.symlink(os.path.join(PUBLIC_DIR, file),
					os.path.join(PUBLIC_DIR, 'ERPNext-Production.ova.md5'))
			else: # Develop
				silent_remove(os.path.join(PUBLIC_DIR, 'ERPNext-Dev.ova.md5'))
				os.symlink(os.path.join(PUBLIC_DIR, file),
					os.path.join(PUBLIC_DIR, 'ERPNext-Dev.ova.md5'))
		else: # ova/box files
			if 'Vagrant' in file:
				silent_remove(os.path.join(PUBLIC_DIR, 'ERPNext-Vagrant.box'))
				os.symlink(os.path.join(PUBLIC_DIR, file),
					os.path.join(PUBLIC_DIR, 'ERPNext-Vagrant.box'))
			elif 'Production' in file:
				silent_remove(os.path.join(PUBLIC_DIR, 'ERPNext-Production.ova'))
				os.symlink(os.path.join(PUBLIC_DIR, file),
					os.path.join(PUBLIC_DIR, 'ERPNext-Production.ova'))
			else: # Develop
				silent_remove(os.path.join(PUBLIC_DIR, 'ERPNext-Dev.ova'))
				os.symlink(os.path.join(PUBLIC_DIR, file),
					os.path.join(PUBLIC_DIR, 'ERPNext-Dev.ova'))

def delete_old_vms():
	silent_remove(os.path.join(PUBLIC_DIR, 'BACKUPS'), is_dir=True)

def move_current_vms():
	os.mkdir(os.path.join(PUBLIC_DIR, 'BACKUPS'))
	for file in os.listdir(PUBLIC_DIR):
		if file in NEW_FILES or file in SYMLINKS or file == 'BACKUPS':
			continue
		src  = os.path.join(PUBLIC_DIR, '{}'.format(file))
		dest = os.path.join(PUBLIC_DIR, 'BACKUPS/{}'.format(file))
		os.rename(src, dest)

if __name__ == "__main__":
	main()
