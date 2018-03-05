"""
Builds a vm and puts it in ~/public with a latest.json that has its filename and md5sum
"""

# imports - standard imports
import 	os
import 	json
import 	stat
import  errno
from 	subprocess import check_output

OUTPUT_DIR = 'output-virtualbox-ovf'
PUBLIC_DIR = os.path.join(os.path.expanduser('~'),  'public')

def main():
	install_virtualbox()
	install_packer()
	build_vm()
	update_latest()
	move_to_public()
	cleanup()

def install_virtualbox():
	check_output(['bench', 'install', 'virtualbox'])

def install_packer():
	check_output(['bench', 'install', 'packer'])

def build_vm():
	download_latest_ubuntu_ova()
	check_output("/opt/packer build vm.json", shell=True)

def download_latest_ubuntu_ova():
	silent_remove('/tmp/ubuntu-16.04-server-cloudimg-amd64.ova')
	check_output(['wget', 'https://cloud-images.ubuntu.com/releases/16.04/release/ubuntu-16.04-server-cloudimg-amd64.ova'], cwd='/tmp/')

def silent_remove(filename):
    try:
        os.remove(filename)
    except OSError as e: 			# this would be "except OSError, e:" before Python 2.6
        if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
            raise 					# re-raise exception if a different error occurred

def move_to_public():
	src = get_filepath()
	dest = os.path.join(PUBLIC_DIR, os.path.join(PUBLIC_DIR, get_filename()))
	os.rename(src, dest)
	st = os.stat(dest)
	os.chmod(dest, st.st_mode | stat.S_IROTH)

def update_latest():
	with open(os.path.join(PUBLIC_DIR, "latest.json"), 'w') as f:
		json.dump(get_latest(), f)

def get_latest():
	md5 = check_output("md5sum {}".format(get_filepath()), shell=True).split()[0]
	return {
		"filename": get_filename(),
		"md5": md5
	}

def get_filename():
	return os.listdir(OUTPUT_DIR)[0]

def get_filepath():
	filename = os.listdir(OUTPUT_DIR)[0]
	return os.path.join(OUTPUT_DIR, filename)

def cleanup():
	os.rmdir(OUTPUT_DIR)

if __name__ == "__main__":
	main()
