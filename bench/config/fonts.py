import os, shutil
from bench.utils import exec_cmd

def setup_fonts():
	fonts_path = os.path.join('/tmp', 'fonts')

	exec_cmd("git clone https://github.com/frappe/fonts.git", cwd='/tmp')
	os.rename('/usr/share/fonts', '/usr/share/fonts_backup')
	os.rename('/etc/fonts', '/etc/fonts_backup')
	os.rename(os.path.join(fonts_path, 'usr_share_fonts'), '/usr/share/fonts')
	os.rename(os.path.join(fonts_path, 'etc_fonts'), '/etc/fonts')
	shutil.rmtree(fonts_path)
	exec_cmd("fc-cache -fv")




