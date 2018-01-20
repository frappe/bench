#!/bin/env python

"""
Bench command to exclude app while update

bench exclude-app <app-name>
"""


import click
from bench.app import add_to_excluded_apps_txt
from bench.app import remove_from_excluded_apps_txt

@click.command('exclude-app')
@click.argument('app_name')
def exclude_app_for_update(app_name):
	"""
	Update bench exclude app for update

	:param app_name(str): App name
	"""
	add_to_excluded_apps_txt(app_name)
	return


@click.command('include-app')
@click.argument('app_name')
def include_app_for_update(app_name):
	"""
	Update bench include app for update.

	:param app_name(str): App name
	"""
	remove_from_excluded_apps_txt(app_name)
	return
