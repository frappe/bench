# imports - standard imports
import os

# imports - module imports
from bench.utils import get_sites


def execute(bench_path):
	"""Generates a logs folder under each site for site-wise logging introduced in v13"""
	for site in get_sites(bench_path):
		site_logs_path = os.path.join(bench_path, 'sites', site, 'logs')
		if not os.path.exists(site_logs_path):
			os.mkdir(site_logs_path)
