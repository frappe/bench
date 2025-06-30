from bench.config.common_site_config import update_config


def execute(bench_path):
	update_config({"live_reload": True}, bench_path)
