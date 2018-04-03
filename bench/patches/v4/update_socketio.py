import subprocess

def execute(bench_path):
	subprocess.check_output(['npm', 'install', 'socket.io'])