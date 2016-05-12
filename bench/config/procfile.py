import bench, os, click
from bench.utils import find_executable
from bench.app import use_rq
from bench.config.common_site_config import get_config

def setup_procfile(bench_path, force=False):
	config = get_config(bench=bench_path)
	procfile_path = os.path.join(bench_path, 'Procfile')
	if not force and os.path.exists(procfile_path):
		click.confirm('A Procfile already exists and this will overwrite it. Do you want to continue?',
			abort=True)

	procfile = bench.env.get_template('Procfile').render(
		node=find_executable("node") or find_executable("nodejs"),
		use_rq=use_rq(bench_path),
		webserver_port=config.get('webserver_port'))

	with open(procfile_path, 'w') as f:
		f.write(procfile)
