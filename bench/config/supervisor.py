# imports - standard imports
import getpass
import logging
import os

# imports - module imports
import bench
from bench.app import use_rq
from bench.utils import get_bench_name, which
from bench.bench import Bench
from bench.config.common_site_config import update_config, get_gunicorn_workers

# imports - third party imports
import click


logger = logging.getLogger(bench.PROJECT_NAME)


def generate_supervisor_config(bench_path, user=None, yes=False, skip_redis=False):
	"""Generate supervisor config for respective bench path"""
	if not user:
		user = getpass.getuser()

	config = Bench(bench_path).conf
	template = bench.config.env().get_template("supervisor.conf")
	bench_dir = os.path.abspath(bench_path)

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
			"redis_socketio_config": os.path.join(bench_dir, "config", "redis_socketio.conf"),
			"redis_queue_config": os.path.join(bench_dir, "config", "redis_queue.conf"),
			"webserver_port": config.get("webserver_port", 8000),
			"gunicorn_workers": config.get(
				"gunicorn_workers", get_gunicorn_workers()["gunicorn_workers"]
			),
			"bench_name": get_bench_name(bench_path),
			"background_workers": config.get("background_workers") or 1,
			"bench_cmd": which("bench"),
			"skip_redis": skip_redis,
			"workers": config.get("workers", {}),
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


def update_supervisord_config(user=None, yes=False):
	"""From bench v5.x, we're moving to supervisor running as user"""
	import configparser
	from bench.config.production_setup import service

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
		return

	if not yes:
		click.confirm(
			f"{supervisord_conf} will be updated with the following values:\n{supervisord_conf_changes}\nDo you want to continue?",
			abort=True,
		)

	try:
		with open(supervisord_conf, "w") as f:
			config.write(f)
			logger.log(f"Updated supervisord.conf at '{supervisord_conf}'")
	except Exception as e:
		logger.log(f"Updating supervisord.conf failed due to '{e}'")

	# Reread supervisor configuration, reload supervisord and supervisorctl, restart services that were started
	service("supervisor", "reload")
