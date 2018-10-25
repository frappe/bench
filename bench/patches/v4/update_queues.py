from bench.config.common_site_config import get_queues, get_config, update_config


def execute(bench_path):
    queues = get_queues()
    config = get_config(bench_path)
    for k1, v1 in queues.items():
        for k2, v2 in v1.items():
            queues[k1][k2]["workers"] = config["background_workers"]
    update_config(queues, bench_path)