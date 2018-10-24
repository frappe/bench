from bench.config.common_site_config import get_queues, update_config

def execute(bench_path):
    update_config(get_queues(), bench_path)