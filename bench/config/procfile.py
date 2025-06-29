import os
import platform

import click

import bench
from bench.bench import Bench
from bench.utils import which


def setup_procfile(bench_path, yes=False, skip_redis=False, skip_web=False, skip_watch=None, skip_socketio=False, skip_schedule=False, with_coverage=False):
	if skip_watch is None:
		# backwards compatibilty; may be eventually removed
		skip_watch = os.environ.get("CI")
	config = Bench(bench_path).conf
	procfile_path = os.path.join(bench_path, "Procfile")

	is_mac = platform.system() == "Darwin"
	if not yes and os.path.exists(procfile_path):
		click.confirm(
			"A Procfile already exists and this will overwrite it. Do you want to continue?",
			abort=True,
		)

	procfile = (
		bench.config.env()
		.get_template("Procfile")
		.render(
			node=which("node") or which("nodejs"),
			webserver_port=config.get("webserver_port"),
			skip_redis=skip_redis,
			skip_web=skip_web,
			skip_watch=skip_watch,
			skip_socketio=skip_socketio,
			skip_schedule=skip_schedule,
			with_coverage=with_coverage,
			workers=config.get("workers", {}),
			is_mac=is_mac,
		)
	)

	with open(procfile_path, "w") as f:
		f.write(procfile)
