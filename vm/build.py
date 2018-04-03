"""
Builds a vm and puts it in ~/public with a latest.json that has its filename and md5sum
"""
import os
import subprocess
import json
import stat

OUTPUT_DIR = 'output-virtualbox-ovf'
PUBLIC_DIR = os.path.join(os.path.expanduser('~'),  'public')

def main():
	build_vm()
	update_latest()
	move_to_public()
	cleanup()

def build_vm():
	subprocess.check_call("./packer build vm.json", shell=True)

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
	md5 = subprocess.check_output("md5sum {}".format(get_filepath()), shell=True).split()[0]
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
