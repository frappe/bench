# imports - standard imports
import getpass
import logging
import os

# imports - module imports
import bench
from bench.app import get_current_frappe_version, use_rq
from bench.utils import get_bench_name, find_executable
from bench.config.common_site_config import get_config, update_config, get_gunicorn_workers

# imports - third party imports
import click
from six.moves import configparser


logger = logging.getLogger(bench.PROJECT_NAME)


def generate_supervisor_config(bench_path, user=None, yes=False):
	"""Generate supervisor config for respective bench path"""
	if not user:
		user = getpass.getuser()

	template = bench.config.env.get_template('supervisor.conf')
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


def get_supervisord_conf():
	"""Returns path of supervisord config from possible paths"""
	possibilities = ("supervisord.conf", "etc/supervisord.conf", "/etc/supervisord.conf", "/etc/supervisor/supervisord.conf", "/etc/supervisord.conf")

	for possibility in possibilities:
		if os.path.exists(possibility):
			return possibility


def update_supervisord_config(user=None, yes=False):
	"""From bench v5.x, we're moving to supervisor running as user"""
	from bench.config.production_setup import service

	supervisord_conf = get_supervisord_conf()
	section = "unix_http_server"
	updated_values = {
		"chmod": "0760",
		"chown": "{user}:{user}".format(user=user)
	}
	supervisord_conf_updated = False

	if not supervisord_conf:
		return

	config = configparser.ConfigParser()
	config.read(supervisord_conf)

	if section not in config.sections():
		config.add_section(section)
		supervisord_conf_updated = True

	for key, value in updated_values.items():
		current_value = config[section].get(key, "")
		if current_value.strip() != value:
			config.set(section, key, value)
			supervisord_conf_updated = True
			logger.log("Updated supervisord config: '{0}' changed from '{1}' to '{2}'".format(key, current_value, value))

	if not supervisord_conf_updated:
		return

	try:
		with open(supervisord_conf, "w") as f:
			config.write(f)
			logger.log("Updated supervisord config at '{0}'".format(supervisord_conf))
	except Exception as e:
		logger.log("Updating supervisord config failed due to '{0}'".format(e))

	# Reread supervisor configuration, reload supervisord and supervisorctl, restart services that were started
	service('supervisor', 'reload')
