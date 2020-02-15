# imports - standard imports
import os
import subprocess

# imports - module imports
from bench.app import get_repo_dir, get_apps, get_remote
from bench.utils import set_git_remote_url

# imports - third party imports
import click


@click.command('remote-set-url', help="Set app remote url")
@click.argument('git-url')
def remote_set_url(git_url):
	set_git_remote_url(git_url)


@click.command('remote-reset-url', help="Reset app remote url to frappe official")
@click.argument('app')
def remote_reset_url(app):
	git_url = "https://github.com/frappe/{}.git".format(app)
	set_git_remote_url(git_url)


@click.command('remote-urls', help="Show apps remote url")
def remote_urls():
	for app in get_apps():
		repo_dir = get_repo_dir(app)

		if os.path.exists(os.path.join(repo_dir, '.git')):
			remote = get_remote(app)
			remote_url = subprocess.check_output(['git', 'config', '--get', 'remote.{}.url'.format(remote)], cwd=repo_dir).strip()
			print("{app}	{remote_url}".format(app=app, remote_url=remote_url))

