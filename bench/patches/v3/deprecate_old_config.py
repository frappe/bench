import os, json
from bench.config.common_site_config import get_config, put_config, get_common_site_config

def execute(bench_path):
	# deprecate bench config
	bench_config_path = os.path.join(bench_path, 'config.json')
	if not os.path.exists(bench_config_path):
		return

	with open(bench_config_path, "r") as f:
		bench_config = json.loads(f.read())

	common_site_config = get_common_site_config(bench_path)
	common_site_config.update(bench_config)
	put_config(common_site_config, bench_path)

	# remove bench/config.json
	os.remove(bench_config_path)

	# change keys
	config = get_config(bench_path)
	changed = False
	for from_key, to_key, default in (
			("celery_broker", "redis_queue", "redis://localhost:6379"),
			("async_redis_server", "redis_socketio", "redis://localhost:12311"),
			("cache_redis_server", "redis_cache", "redis://localhost:11311")
		):
		if from_key in config:
			config[to_key] = config[from_key]
			del config[from_key]
			changed = True

		elif to_key not in config:
			config[to_key] = default
			changed = True

	if changed:
		put_config(config, bench_path)
