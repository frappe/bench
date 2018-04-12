import os, getpass, click
import bench

def generate_systemd_config(bench_path, user=None, yes=False, stop=False):
	from bench.app import get_current_frappe_version, use_rq
	from bench.utils import get_bench_name, find_executable
	from bench.config.common_site_config import get_config, update_config, get_gunicorn_workers

	if not user:
		user = getpass.getuser()

	config = get_config(bench_path=bench_path)

	bench_dir = os.path.abspath(bench_path)
	bench_name = get_bench_name(bench_path)

	if stop:
		from bench.utils import exec_cmd
		exec_cmd('sudo systemctl stop -- $(systemctl show -p Requires {bench_name}.target | cut -d= -f2)'.format(bench_name=bench_name))
		return

	bench_info = {
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
	}

	if not yes:
		click.confirm('current systemd configuration will be overwritten. Do you want to continue?',
			abort=True)

	setup_systemd_directory(bench_path)
	setup_main_config(bench_info, bench_path)
	setup_workers_config(bench_info, bench_path)
	setup_web_config(bench_info, bench_path)
	setup_redis_config(bench_info, bench_path)

	update_config({'restart_systemd_on_update': True}, bench_path=bench_path)

def setup_systemd_directory(bench_path):
	if not os.path.exists(os.path.join(bench_path, 'config', 'systemd')):
		os.makedirs(os.path.join(bench_path, 'config', 'systemd'))

def setup_main_config(bench_info, bench_path):
	# Main config
	bench_template = bench.env.get_template('systemd/frappe-bench.target')
	bench_config = bench_template.render(**bench_info)
	bench_config_path = os.path.join(bench_path, 'config', 'systemd' , bench_info.get("bench_name") + '.target')

	with open(bench_config_path, 'w') as f:
		f.write(bench_config)

def setup_workers_config(bench_info, bench_path):
	# Worker Group
	bench_workers_target_template = bench.env.get_template('systemd/frappe-bench-workers.target')
	bench_default_worker_template = bench.env.get_template('systemd/frappe-bench-frappe-default-worker.service')
	bench_short_worker_template = bench.env.get_template('systemd/frappe-bench-frappe-short-worker.service')
	bench_long_worker_template = bench.env.get_template('systemd/frappe-bench-frappe-long-worker.service')
	bench_schedule_worker_template = bench.env.get_template('systemd/frappe-bench-frappe-schedule.service')

	bench_workers_target_config = bench_workers_target_template.render(**bench_info)
	bench_default_worker_config = bench_default_worker_template.render(**bench_info)
	bench_short_worker_config = bench_short_worker_template.render(**bench_info)
	bench_long_worker_config = bench_long_worker_template.render(**bench_info)
	bench_schedule_worker_config = bench_schedule_worker_template.render(**bench_info)

	bench_workers_target_config_path = os.path.join(bench_path, 'config', 'systemd' , bench_info.get("bench_name") + '-workers.target')
	bench_default_worker_config_path = os.path.join(bench_path, 'config', 'systemd' , bench_info.get("bench_name") + '-frappe-default-worker.service')
	bench_short_worker_config_path = os.path.join(bench_path, 'config', 'systemd' , bench_info.get("bench_name") + '-frappe-short-worker.service')
	bench_long_worker_config_path = os.path.join(bench_path, 'config', 'systemd' , bench_info.get("bench_name") + '-frappe-long-worker.service')
	bench_schedule_worker_config_path = os.path.join(bench_path, 'config', 'systemd' , bench_info.get("bench_name") + '-frappe-schedule.service')

	with open(bench_workers_target_config_path, 'w') as f:
		f.write(bench_workers_target_config)

	with open(bench_default_worker_config_path, 'w') as f:
		f.write(bench_default_worker_config)

	with open(bench_short_worker_config_path, 'w') as f:
		f.write(bench_short_worker_config)

	with open(bench_long_worker_config_path, 'w') as f:
		f.write(bench_long_worker_config)

	with open(bench_schedule_worker_config_path, 'w') as f:
		f.write(bench_schedule_worker_config)

def setup_web_config(bench_info, bench_path):
	# Web Group
	bench_web_target_template = bench.env.get_template('systemd/frappe-bench-web.target')
	bench_web_service_template = bench.env.get_template('systemd/frappe-bench-frappe-web.service')
	bench_node_socketio_template = bench.env.get_template('systemd/frappe-bench-node-socketio.service')

	bench_web_target_config = bench_web_target_template.render(**bench_info)
	bench_web_service_config = bench_web_service_template.render(**bench_info)
	bench_node_socketio_config = bench_node_socketio_template.render(**bench_info)

	bench_web_target_config_path = os.path.join(bench_path, 'config', 'systemd' , bench_info.get("bench_name") + '-web.target')
	bench_web_service_config_path = os.path.join(bench_path, 'config', 'systemd' , bench_info.get("bench_name") + '-frappe-web.service')
	bench_node_socketio_config_path = os.path.join(bench_path, 'config', 'systemd' , bench_info.get("bench_name") + '-node-socketio.service')

	with open(bench_web_target_config_path, 'w') as f:
		f.write(bench_web_target_config)

	with open(bench_web_service_config_path, 'w') as f:
		f.write(bench_web_service_config)

	with open(bench_node_socketio_config_path, 'w') as f:
		f.write(bench_node_socketio_config)

def setup_redis_config(bench_info, bench_path):
	# Redis Group
	bench_redis_target_template = bench.env.get_template('systemd/frappe-bench-redis.target')
	bench_redis_cache_template = bench.env.get_template('systemd/frappe-bench-redis-cache.service')
	bench_redis_queue_template = bench.env.get_template('systemd/frappe-bench-redis-queue.service')
	bench_redis_socketio_template = bench.env.get_template('systemd/frappe-bench-redis-socketio.service')

	bench_redis_target_config = bench_redis_target_template.render(**bench_info)
	bench_redis_cache_config = bench_redis_cache_template.render(**bench_info)
	bench_redis_queue_config = bench_redis_queue_template.render(**bench_info)
	bench_redis_socketio_config = bench_redis_socketio_template.render(**bench_info)

	bench_redis_target_config_path = os.path.join(bench_path, 'config', 'systemd' , bench_info.get("bench_name") + '-redis.target')
	bench_redis_cache_config_path = os.path.join(bench_path, 'config', 'systemd' , bench_info.get("bench_name") + '-redis-cache.service')
	bench_redis_queue_config_path = os.path.join(bench_path, 'config', 'systemd' , bench_info.get("bench_name") + '-redis-queue.service')
	bench_redis_socketio_config_path = os.path.join(bench_path, 'config', 'systemd' , bench_info.get("bench_name") + '-redis-socketio.service')

	with open(bench_redis_target_config_path, 'w') as f:
		f.write(bench_redis_target_config)

	with open(bench_redis_cache_config_path, 'w') as f:
		f.write(bench_redis_cache_config)

	with open(bench_redis_queue_config_path, 'w') as f:
		f.write(bench_redis_queue_config)

	with open(bench_redis_socketio_config_path, 'w') as f:
		f.write(bench_redis_socketio_config)
