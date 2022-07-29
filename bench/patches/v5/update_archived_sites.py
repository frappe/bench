"""
Deprecate archived_sites folder for consistency. This change is
only for Frappe v14 benches. If not a v14 bench yet, skip this
patch and try again later.

1. Rename folder `./archived_sites` to `./archived/sites`
2. Create a symlink `./archived_sites` => `./archived/sites`

Corresponding changes in frappe/frappe via https://github.com/frappe/frappe/pull/15060
"""
import os
from pathlib import Path

import click
from bench.utils.app import get_current_version
from semantic_version import Version


def execute(bench_path):
	frappe_version = Version(get_current_version("frappe"))

	if frappe_version.major < 14 or os.name != "posix":
		# Returning False means patch has been skipped
		return False

	pre_patch_dir = os.getcwd()
	old_directory = Path(bench_path, "archived_sites")
	new_directory = Path(bench_path, "archived", "sites")

	if not old_directory.exists():
		return False

	if old_directory.is_symlink():
		return True

	os.chdir(bench_path)

	if not os.path.exists(new_directory):
		os.makedirs(new_directory)

	for archived_site_path in old_directory.glob("*"):
		archived_site_path.rename(new_directory)

	click.secho(f"Archived sites are now stored under {new_directory}")

	if not os.listdir(old_directory):
		os.rmdir(old_directory)

	os.symlink(new_directory, old_directory)

	click.secho(f"Symlink {old_directory} that points to {new_directory}")

	os.chdir(pre_patch_dir)
