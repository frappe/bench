import bench, os, click
from bench.utils import find_executable
from bench.app import use_rq
from bench.config.common_site_config import get_config

def setup_procfile(bench_path, yes=False, skip_redis=False):
	config = get_config(bench_path=bench_path)
	procfile_path = os.path.join(bench_path, 'Procfile')
	if not yes and os.path.exists(procfile_path):
		click.confirm('A Procfile already exists and this will overwrite it. Do you want to continue?',
			abort=True)

	procfile = bench.env.get_template('Procfile').render(
		node=find_executable("node") or find_executable("nodejs"),
		use_rq=use_rq(bench_path),
		webserver_port=config.get('webserver_port'),
		CI=os.environ.get('CI'),
		skip_redis=skip_redis)

	with open(procfile_path, 'w') as f:
		f.write(procfile)
