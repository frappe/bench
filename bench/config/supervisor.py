# imports - standard imports
import getpass
import logging
import os

# imports - third party imports
import click

# imports - module imports
import bench
from bench.app import use_rq
from bench.bench import Bench
from bench.config.common_site_config import (
	compute_max_requests_jitter,
	get_config,
	get_default_max_requests,
	get_gunicorn_workers,
	update_config,
)
from bench.utils import get_bench_name, which

logger = logging.getLogger(bench.PROJECT_NAME)


def generate_supervisor_config(bench_path, user=None, yes=False, skip_redis=False):
	"""Generate supervisor config for respective bench path"""
	if not user:
		user = getpass.getuser()

	config = Bench(bench_path).conf
	template = bench.config.env().get_template("supervisor.conf")
	bench_dir = os.path.abspath(bench_path)

	web_worker_count = config.get(
		"gunicorn_workers", get_gunicorn_workers()["gunicorn_workers"]
	)
	max_requests = config.get(
		"gunicorn_max_requests", get_default_max_requests(web_worker_count)
	)

	config = template.render(
		**{
			"bench_dir": bench_dir,
			"sites_dir": os.path.join(bench_dir, "sites"),
			"user": user,
			"use_rq": use_rq(bench_path),
			"http_timeout": config.get("http_timeout", 120),
			"redis_server": which("redis-server"),
			"node": which("node") or which("nodejs"),
			"redis_cache_config": os.path.join(bench_dir, "config", "redis_cache.conf"),
			"redis_queue_config": os.path.join(bench_dir, "config", "redis_queue.conf"),
			"webserver_port": config.get("webserver_port", 8000),
			"gunicorn_workers": web_worker_count,
			"gunicorn_max_requests": max_requests,
			"gunicorn_max_requests_jitter": compute_max_requests_jitter(max_requests),
			"bench_name": get_bench_name(bench_path),
			"background_workers": config.get("background_workers") or 1,
			"bench_cmd": which("bench"),
			"skip_redis": skip_redis,
			"workers": config.get("workers", {}),
			"multi_queue_consumption": can_enable_multi_queue_consumption(bench_path),
		}
	)

	conf_path = os.path.join(bench_path, "config", "supervisor.conf")
	if not yes and os.path.exists(conf_path):
		click.confirm(
			"supervisor.conf already exists and this will overwrite it. Do you want to continue?",
			abort=True,
		)

	with open(conf_path, "w") as f:
		f.write(config)

	update_config({"restart_supervisor_on_update": True}, bench_path=bench_path)
	update_config({"restart_systemd_on_update": False}, bench_path=bench_path)
	sync_socketio_port(bench_path)


def get_supervisord_conf():
	"""Returns path of supervisord config from possible paths"""
	possibilities = (
		"supervisord.conf",
		"etc/supervisord.conf",
		"/etc/supervisord.conf",
		"/etc/supervisor/supervisord.conf",
		"/etc/supervisord.conf",
	)

	for possibility in possibilities:
		if os.path.exists(possibility):
			return possibility


def sync_socketio_port(bench_path):
	# Backward compatbility: always keep redis_cache and redis_socketio port same
	common_config = get_config(bench_path=bench_path)

	socketio_port = common_config.get("redis_socketio")
	cache_port = common_config.get("redis_cache")
	if socketio_port and socketio_port != cache_port:
		update_config({"redis_socketio": cache_port})


def can_enable_multi_queue_consumption(bench_path: str) -> bool:
	try:
		from semantic_version import Version

		from bench.utils.app import get_current_version

		supported_version = Version(major=14, minor=18, patch=0)

		frappe_version = Version(get_current_version("frappe", bench_path=bench_path))

		return frappe_version > supported_version
	except Exception:
		return False


def check_supervisord_config(user=None):
	"""From bench v5.x, we're moving to supervisor running as user"""
	# i don't think bench should be responsible for this but we're way past this now...
	# removed updating supervisord conf & reload in Aug 2022 - gavin@frappe.io
	import configparser

	if not user:
		user = getpass.getuser()

	supervisord_conf = get_supervisord_conf()
	section = "unix_http_server"
	updated_values = {"chmod": "0760", "chown": f"{user}:{user}"}
	supervisord_conf_changes = ""

	if not supervisord_conf:
		logger.log("supervisord.conf not found")
		return

	config = configparser.ConfigParser()
	config.read(supervisord_conf)

	if section not in config.sections():
		config.add_section(section)
		action = f"Section {section} Added"
		logger.log(action)
		supervisord_conf_changes += "\n" + action

	for key, value in updated_values.items():
		try:
			current_value = config.get(section, key)
		except configparser.NoOptionError:
			current_value = ""

		if current_value.strip() != value:
			config.set(section, key, value)
			action = (
				f"Updated supervisord.conf: '{key}' changed from '{current_value}' to '{value}'"
			)
			logger.log(action)
			supervisord_conf_changes += "\n" + action

	if not supervisord_conf_changes:
		logger.error("supervisord.conf not updated")
		contents = "\n".join(f"{x}={y}" for x, y in updated_values.items())
		print(
			f"Update your {supervisord_conf} with the following values:\n[{section}]\n{contents}"
		)
