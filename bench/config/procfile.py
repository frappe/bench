import bench, os, click
from bench.utils import find_executable

def setup_procfile(bench_path, force=False):
	procfile_path = os.path.join(bench_path, 'Procfile')
	if not force and os.path.exists(procfile_path):
		click.confirm('A Procfile already exists and this will overwrite it. Do you want to continue?',
			abort=True)

	procfile = bench.env.get_template('Procfile').render(node=find_executable("node") \
		or find_executable("nodejs"))

	with open(procfile_path, 'w') as f:
		f.write(procfile)
