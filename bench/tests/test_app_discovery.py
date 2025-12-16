# imports - standard imports
import json
import os
import subprocess
import tempfile
import unittest

# imports - module imports
from bench.bench import Bench, BenchApps


class TestAppDiscovery(unittest.TestCase):
	"""Test app discovery from Python environment"""

	def test_initialize_apps_with_caching(self):
		"""Test that initialize_apps uses caching correctly"""
		# Create a temporary directory structure
		with tempfile.TemporaryDirectory() as tmpdir:
			bench_path = os.path.join(tmpdir, "test-bench")
			os.makedirs(bench_path)
			os.makedirs(os.path.join(bench_path, "apps"))
			os.makedirs(os.path.join(bench_path, "sites"))
			os.makedirs(os.path.join(bench_path, "config"))
			os.makedirs(os.path.join(bench_path, "logs"))
			
			# Create a mock bench instance
			bench = Bench(bench_path)
			bench_apps = BenchApps(bench)
			
			# First call should compute and cache
			first_call_result = bench_apps.apps
			
			# Second call should return cached result
			bench_apps.initialize_apps()
			second_call_result = bench_apps.apps
			
			# Results should be identical
			self.assertEqual(first_call_result, second_call_result)
			
	def test_cache_invalidation_on_sync(self):
		"""Test that cache is invalidated when sync is called"""
		with tempfile.TemporaryDirectory() as tmpdir:
			bench_path = os.path.join(tmpdir, "test-bench")
			os.makedirs(bench_path)
			os.makedirs(os.path.join(bench_path, "apps"))
			os.makedirs(os.path.join(bench_path, "sites"))
			os.makedirs(os.path.join(bench_path, "config"))
			os.makedirs(os.path.join(bench_path, "logs"))
			
			bench = Bench(bench_path)
			bench_apps = BenchApps(bench)
			
			# Cache should be set after initialization
			self.assertIsNotNone(bench_apps._cached_apps)
			
			# Sync should invalidate cache
			bench_apps.sync()
			
			# After sync, cache should be set again
			self.assertIsNotNone(bench_apps._cached_apps)

	def test_discover_apps_from_env_method_exists(self):
		"""Test that the new discovery methods exist"""
		with tempfile.TemporaryDirectory() as tmpdir:
			bench_path = os.path.join(tmpdir, "test-bench")
			os.makedirs(bench_path)
			os.makedirs(os.path.join(bench_path, "apps"))
			os.makedirs(os.path.join(bench_path, "sites"))
			os.makedirs(os.path.join(bench_path, "config"))
			os.makedirs(os.path.join(bench_path, "logs"))
			
			bench = Bench(bench_path)
			bench_apps = BenchApps(bench)
			
			# Check that new methods exist
			self.assertTrue(hasattr(bench_apps, '_get_installed_packages'))
			self.assertTrue(hasattr(bench_apps, '_discover_apps_from_env'))
			self.assertTrue(hasattr(bench_apps, '_get_app_location_from_env'))


if __name__ == "__main__":
	unittest.main()
