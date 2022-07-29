# imports - standard imports
import getpass
import os

# imports - third partyimports
import click

# imports - module imports
import bench
from bench.app import use_rq
from bench.bench import Bench
from bench.config.common_site_config import get_gunicorn_workers, update_config
from bench.utils import exec_cmd, which, get_bench_name


def generate_systemd_config(
	bench_path,
	user=None,
	yes=False,
	stop=False,
	create_symlinks=False,
	delete_symlinks=False,
):

	if not user:
		user = getpass.getuser()

	config = Bench(bench_path).conf

	bench_dir = os.path.abspath(bench_path)
	bench_name = get_bench_name(bench_path)

	if stop:
		exec_cmd(
			f"sudo systemctl stop -- $(systemctl show -p Requires {bench_name}.target | cut -d= -f2)"
		)
		return

	if create_symlinks:
		_create_symlinks(bench_path)
		return

	if delete_symlinks:
		_delete_symlinks(bench_path)
		return

	number_of_workers = config.get("background_workers") or 1
	background_workers = []
	for i in range(number_of_workers):
		background_workers.append(
			get_bench_name(bench_path) + "-frappe-default-worker@" + str(i + 1) + ".service"
		)

	for i in range(number_of_workers):
		background_workers.append(
			get_bench_name(bench_path) + "-frappe-short-worker@" + str(i + 1) + ".service"
		)

	for i in range(number_of_workers):
		background_workers.append(
			get_bench_name(bench_path) + "-frappe-long-worker@" + str(i + 1) + ".service"
		)

	bench_info = {
		"bench_dir": bench_dir,
		"sites_dir": os.path.join(bench_dir, "sites"),
		"user": user,
		"use_rq": use_rq(bench_path),
		"http_timeout": config.get("http_timeout", 120),
		"redis_server": which("redis-server"),
		"node": which("node") or which("nodejs"),
		"redis_cache_config": os.path.join(bench_dir, "config", "redis_cache.conf"),
		"redis_socketio_config": os.path.join(bench_dir, "config", "redis_socketio.conf"),
		"redis_queue_config": os.path.join(bench_dir, "config", "redis_queue.conf"),
		"webserver_port": config.get("webserver_port", 8000),
		"gunicorn_workers": config.get(
			"gunicorn_workers", get_gunicorn_workers()["gunicorn_workers"]
		),
		"bench_name": get_bench_name(bench_path),
		"worker_target_wants": " ".join(background_workers),
		"bench_cmd": which("bench"),
	}

	if not yes:
		click.confirm(
			"current systemd configuration will be overwritten. Do you want to continue?",
			abort=True,
		)

	setup_systemd_directory(bench_path)
	setup_main_config(bench_info, bench_path)
	setup_workers_config(bench_info, bench_path)
	setup_web_config(bench_info, bench_path)
	setup_redis_config(bench_info, bench_path)

	update_config({"restart_systemd_on_update": True}, bench_path=bench_path)
	update_config({"restart_supervisor_on_update": False}, bench_path=bench_path)


def setup_systemd_directory(bench_path):
	if not os.path.exists(os.path.join(bench_path, "config", "systemd")):
		os.makedirs(os.path.join(bench_path, "config", "systemd"))


def setup_main_config(bench_info, bench_path):
	# Main config
	bench_template = bench.config.env().get_template("systemd/frappe-bench.target")
	bench_config = bench_template.render(**bench_info)
	bench_config_path = os.path.join(
		bench_path, "config", "systemd", bench_info.get("bench_name") + ".target"
	)

	with open(bench_config_path, "w") as f:
		f.write(bench_config)


def setup_workers_config(bench_info, bench_path):
	# Worker Group
	bench_workers_target_template = bench.config.env().get_template(
		"systemd/frappe-bench-workers.target"
	)
	bench_default_worker_template = bench.config.env().get_template(
		"systemd/frappe-bench-frappe-default-worker.service"
	)
	bench_short_worker_template = bench.config.env().get_template(
		"systemd/frappe-bench-frappe-short-worker.service"
	)
	bench_long_worker_template = bench.config.env().get_template(
		"systemd/frappe-bench-frappe-long-worker.service"
	)
	bench_schedule_worker_template = bench.config.env().get_template(
		"systemd/frappe-bench-frappe-schedule.service"
	)

	bench_workers_target_config = bench_workers_target_template.render(**bench_info)
	bench_default_worker_config = bench_default_worker_template.render(**bench_info)
	bench_short_worker_config = bench_short_worker_template.render(**bench_info)
	bench_long_worker_config = bench_long_worker_template.render(**bench_info)
	bench_schedule_worker_config = bench_schedule_worker_template.render(**bench_info)

	bench_workers_target_config_path = os.path.join(
		bench_path, "config", "systemd", bench_info.get("bench_name") + "-workers.target"
	)
	bench_default_worker_config_path = os.path.join(
		bench_path,
		"config",
		"systemd",
		bench_info.get("bench_name") + "-frappe-default-worker@.service",
	)
	bench_short_worker_config_path = os.path.join(
		bench_path,
		"config",
		"systemd",
		bench_info.get("bench_name") + "-frappe-short-worker@.service",
	)
	bench_long_worker_config_path = os.path.join(
		bench_path,
		"config",
		"systemd",
		bench_info.get("bench_name") + "-frappe-long-worker@.service",
	)
	bench_schedule_worker_config_path = os.path.join(
		bench_path,
		"config",
		"systemd",
		bench_info.get("bench_name") + "-frappe-schedule.service",
	)

	with open(bench_workers_target_config_path, "w") as f:
		f.write(bench_workers_target_config)

	with open(bench_default_worker_config_path, "w") as f:
		f.write(bench_default_worker_config)

	with open(bench_short_worker_config_path, "w") as f:
		f.write(bench_short_worker_config)

	with open(bench_long_worker_config_path, "w") as f:
		f.write(bench_long_worker_config)

	with open(bench_schedule_worker_config_path, "w") as f:
		f.write(bench_schedule_worker_config)


def setup_web_config(bench_info, bench_path):
	# Web Group
	bench_web_target_template = bench.config.env().get_template(
		"systemd/frappe-bench-web.target"
	)
	bench_web_service_template = bench.config.env().get_template(
		"systemd/frappe-bench-frappe-web.service"
	)
	bench_node_socketio_template = bench.config.env().get_template(
		"systemd/frappe-bench-node-socketio.service"
	)

	bench_web_target_config = bench_web_target_template.render(**bench_info)
	bench_web_service_config = bench_web_service_template.render(**bench_info)
	bench_node_socketio_config = bench_node_socketio_template.render(**bench_info)

	bench_web_target_config_path = os.path.join(
		bench_path, "config", "systemd", bench_info.get("bench_name") + "-web.target"
	)
	bench_web_service_config_path = os.path.join(
		bench_path, "config", "systemd", bench_info.get("bench_name") + "-frappe-web.service"
	)
	bench_node_socketio_config_path = os.path.join(
		bench_path,
		"config",
		"systemd",
		bench_info.get("bench_name") + "-node-socketio.service",
	)

	with open(bench_web_target_config_path, "w") as f:
		f.write(bench_web_target_config)

	with open(bench_web_service_config_path, "w") as f:
		f.write(bench_web_service_config)

	with open(bench_node_socketio_config_path, "w") as f:
		f.write(bench_node_socketio_config)


def setup_redis_config(bench_info, bench_path):
	# Redis Group
	bench_redis_target_template = bench.config.env().get_template(
		"systemd/frappe-bench-redis.target"
	)
	bench_redis_cache_template = bench.config.env().get_template(
		"systemd/frappe-bench-redis-cache.service"
	)
	bench_redis_queue_template = bench.config.env().get_template(
		"systemd/frappe-bench-redis-queue.service"
	)
	bench_redis_socketio_template = bench.config.env().get_template(
		"systemd/frappe-bench-redis-socketio.service"
	)

	bench_redis_target_config = bench_redis_target_template.render(**bench_info)
	bench_redis_cache_config = bench_redis_cache_template.render(**bench_info)
	bench_redis_queue_config = bench_redis_queue_template.render(**bench_info)
	bench_redis_socketio_config = bench_redis_socketio_template.render(**bench_info)

	bench_redis_target_config_path = os.path.join(
		bench_path, "config", "systemd", bench_info.get("bench_name") + "-redis.target"
	)
	bench_redis_cache_config_path = os.path.join(
		bench_path, "config", "systemd", bench_info.get("bench_name") + "-redis-cache.service"
	)
	bench_redis_queue_config_path = os.path.join(
		bench_path, "config", "systemd", bench_info.get("bench_name") + "-redis-queue.service"
	)
	bench_redis_socketio_config_path = os.path.join(
		bench_path,
		"config",
		"systemd",
		bench_info.get("bench_name") + "-redis-socketio.service",
	)

	with open(bench_redis_target_config_path, "w") as f:
		f.write(bench_redis_target_config)

	with open(bench_redis_cache_config_path, "w") as f:
		f.write(bench_redis_cache_config)

	with open(bench_redis_queue_config_path, "w") as f:
		f.write(bench_redis_queue_config)

	with open(bench_redis_socketio_config_path, "w") as f:
		f.write(bench_redis_socketio_config)


def _create_symlinks(bench_path):
	bench_dir = os.path.abspath(bench_path)
	etc_systemd_system = os.path.join("/", "etc", "systemd", "system")
	config_path = os.path.join(bench_dir, "config", "systemd")
	unit_files = get_unit_files(bench_dir)
	for unit_file in unit_files:
		filename = "".join(unit_file)
		exec_cmd(
			f'sudo ln -s {config_path}/{filename} {etc_systemd_system}/{"".join(unit_file)}'
		)
	exec_cmd("sudo systemctl daemon-reload")


def _delete_symlinks(bench_path):
	bench_dir = os.path.abspath(bench_path)
	etc_systemd_system = os.path.join("/", "etc", "systemd", "system")
	unit_files = get_unit_files(bench_dir)
	for unit_file in unit_files:
		exec_cmd(f'sudo rm {etc_systemd_system}/{"".join(unit_file)}')
	exec_cmd("sudo systemctl daemon-reload")


def get_unit_files(bench_path):
	bench_name = get_bench_name(bench_path)
	unit_files = [
		[bench_name, ".target"],
		[bench_name + "-workers", ".target"],
		[bench_name + "-web", ".target"],
		[bench_name + "-redis", ".target"],
		[bench_name + "-frappe-default-worker@", ".service"],
		[bench_name + "-frappe-short-worker@", ".service"],
		[bench_name + "-frappe-long-worker@", ".service"],
		[bench_name + "-frappe-schedule", ".service"],
		[bench_name + "-frappe-web", ".service"],
		[bench_name + "-node-socketio", ".service"],
		[bench_name + "-redis-cache", ".service"],
		[bench_name + "-redis-queue", ".service"],
		[bench_name + "-redis-socketio", ".service"],
	]
	return unit_files
