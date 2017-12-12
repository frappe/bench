#!/bin/env python

"""
Bench command to exclude app while update

bench exclude-app <app-name>
"""


import click
from bench.app import add_to_excluded_appstxt
from bench.app import remove_from_exclided_appsstxt

@click.command('exclude-app')
@click.argument('app_name')
def exclude_update(app_name):
	"""Update bench"""
	add_to_excluded_appstxt(app_name)
	return


@click.command('include-app')
@click.argument('app_name')
def include_update(app_name):
    """Update bench"""
    add_to_excluded_appstxt(app_name)
    return
