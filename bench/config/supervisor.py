import os, getpass, click
import bench

def generate_supervisor_config(bench_path, user=None, yes=False):
	from bench.app import get_current_frappe_version, use_rq
	from bench.utils import get_bench_name, find_executable
	from bench.config.common_site_config import get_config, update_config, get_gunicorn_workers

	template = bench.env.get_template('supervisor.conf')
	if not user:
		user = getpass.getuser()

	config = get_config(bench_path=bench_path)

	bench_dir = os.path.abspath(bench_path)

	config = template.render(**{
		"bench_dir": bench_dir,
		"sites_dir": os.path.join(bench_dir, 'sites'),
		"user": user,
		"frappe_version": get_current_frappe_version(bench_path),
		"use_rq": use_rq(bench_path),
		"http_timeout": config.get("http_timeout", 120),
		"redis_server": find_executable('redis-server'),
		"node": find_executable('node') or find_executable('nodejs'),
		"redis_cache_config": os.path.join(bench_dir, 'config', 'redis_cache.conf'),
		"redis_socketio_config": os.path.join(bench_dir, 'config', 'redis_socketio.conf'),
		"redis_queue_config": os.path.join(bench_dir, 'config', 'redis_queue.conf'),
		"webserver_port": config.get('webserver_port', 8000),
		"gunicorn_workers": config.get('gunicorn_workers', get_gunicorn_workers()["gunicorn_workers"]),
		"bench_name": get_bench_name(bench_path),
		"background_workers": config.get('background_workers') or 1,
		"bench_cmd": find_executable('bench')
	})

	conf_path = os.path.join(bench_path, 'config', 'supervisor.conf')
	if not yes and os.path.exists(conf_path):
		click.confirm('supervisor.conf already exists and this will overwrite it. Do you want to continue?',
			abort=True)

	with open(conf_path, 'w') as f:
		f.write(config)

	update_config({'restart_supervisor_on_update': True}, bench_path=bench_path)
	update_config({'restart_systemd_on_update': False}, bench_path=bench_path)

