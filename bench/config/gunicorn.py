# imports - standard imports
import getpass
import os
import pprint

# imports - third party imports
import click

# imports - module imports
import bench
from bench.bench import Bench
from bench.config.common_site_config import (
	compute_max_requests_jitter,
	get_default_max_requests,
	get_gunicorn_workers,
)
from bench.utils import get_bench_name, which

# Per-queue drain budget (seconds), mirroring the supervisor template's stopwaitsecs.
QUEUE_STOP_TIMEOUT = {
	"default": 1560,
	"long": 1560,
	"short": 360,
}
SCHEDULER_STOP_TIMEOUT = 60
SOCKETIO_STOP_TIMEOUT = 30


def build_companion_workers(bench_path, config, *, sites_dir, logs_dir):
	"""Build the ``companion_workers`` spec list for the gunicorn config.

	One companion per worker process (mirrors the supervisor ``numprocs``):
	scheduler, then ``background_workers`` instances for each queue, plus the
	socketio companion when enabled. Queue grouping follows the supervisor
	template, including multi-queue consumption.
	"""
	from bench.config.supervisor import can_enable_multi_queue_consumption

	background_workers = config.get("background_workers") or 1
	multi_queue = can_enable_multi_queue_consumption(bench_path)
	custom_workers = config.get("workers", {})

	def spec(name, target, *, cwd, stop_timeout, env=None):
		worker = {
			"name": name,
			"target": target,
			"cwd": cwd,
			"stop_timeout": stop_timeout,
			"stdout": os.path.join(logs_dir, f"{name}.log"),
			"stderr": "stdout",
		}
		if env:
			worker["env"] = env
		return worker

	# Workers/scheduler run from sites/ (frappe.init_site reads ./apps.txt);
	# socketio runs from the bench dir. cwd set per spec below.
	workers = [
		spec(
			"scheduler",
			"frappe.gunicorn_companion:run_scheduler",
			cwd=sites_dir,
			stop_timeout=SCHEDULER_STOP_TIMEOUT,
		)
	]

	# Built-in queues. With multi-queue, short/long also drain lighter queues and
	# there is no separate default worker, matching the supervisor template.
	if multi_queue:
		queue_consumption = {"short": "short,default", "long": "long,default,short"}
	else:
		queue_consumption = {"default": "default", "short": "short", "long": "long"}

	for queue_name, queue_list in queue_consumption.items():
		for index in range(background_workers):
			workers.append(
				spec(
					f"worker-{queue_name}-{index + 1}",
					"frappe.gunicorn_companion:run_worker",
					cwd=sites_dir,
					stop_timeout=QUEUE_STOP_TIMEOUT[queue_name],
					env={"FRAPPE_COMPANION_QUEUE": queue_list},
				)
			)

	# Custom queues defined under the "workers" key.
	for queue_name, details in custom_workers.items():
		count = details.get("background_workers") or background_workers
		timeout = details.get("timeout", QUEUE_STOP_TIMEOUT["default"])
		for index in range(count):
			workers.append(
				spec(
					f"worker-{queue_name}-{index + 1}",
					"frappe.gunicorn_companion:run_worker",
					cwd=sites_dir,
					stop_timeout=timeout,
					env={"FRAPPE_COMPANION_QUEUE": queue_name},
				)
			)

	if _socketio_enabled(config):
		workers.append(
			spec(
				"socketio",
				"frappe.gunicorn_companion:run_socketio",
				cwd=bench_path,
				stop_timeout=SOCKETIO_STOP_TIMEOUT,
			)
		)

	return workers


def _socketio_enabled(config):
	# python backend needs no node; node backend needs node present.
	return config.get("socketio_backend", "node") == "python" or bool(
		which("node") or which("nodejs")
	)


def generate_gunicorn_config(bench_path, user=None, yes=False):
	"""Render ``config/gunicorn.conf.py`` for use_gunicorn_companion mode."""
	if not user:
		user = getpass.getuser()

	config = Bench(bench_path).conf
	bench_dir = os.path.abspath(bench_path)
	sites_dir = os.path.join(bench_dir, "sites")
	logs_dir = os.path.join(bench_dir, "logs")

	web_worker_count = config.get(
		"gunicorn_workers", get_gunicorn_workers()["gunicorn_workers"]
	)
	max_requests = config.get(
		"gunicorn_max_requests", get_default_max_requests(web_worker_count)
	)

	companion_workers = build_companion_workers(
		bench_dir, config, sites_dir=sites_dir, logs_dir=logs_dir
	)

	template = bench.config.env().get_template("gunicorn.conf.py")
	rendered = template.render(
		**{
			"webserver_port": config.get("webserver_port", 8000),
			"gunicorn_workers": web_worker_count,
			"http_timeout": config.get("http_timeout", 120),
			"gunicorn_max_requests": max_requests,
			"gunicorn_max_requests_jitter": compute_max_requests_jitter(max_requests),
			"companion_control_socket": os.path.join(
				bench_dir, "config", "gunicorn-companion.sock"
			),
			"companion_workers_code": pprint.pformat(
				companion_workers, indent=4, width=100, sort_dicts=False
			),
			"bench_name": get_bench_name(bench_path),
		}
	)

	conf_path = os.path.join(bench_path, "config", "gunicorn.conf.py")
	if not yes and os.path.exists(conf_path):
		click.confirm(
			"gunicorn.conf.py already exists and this will overwrite it. Do you want to continue?",
			abort=True,
		)

	with open(conf_path, "w") as f:
		f.write(rendered)

	return conf_path
