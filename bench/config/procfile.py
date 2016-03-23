import bench, os
from bench.utils import find_executable

def setup_procfile(bench_path):
	procfile = bench.env.get_template('Procfile').render(node=find_executable("node") \
		or find_executable("nodejs"))
	
	with open(os.path.join(bench_path, 'Procfile'), 'w') as f:
		f.write(procfile)
