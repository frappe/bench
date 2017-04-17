import click
import os, subprocess, re

from bench.app import get_repo_dir, get_apps, get_remote
from bench.utils import set_git_remote_url


@click.command('remote-set-url')
@click.argument('git-url')
def remote_set_url(git_url):
	"Set app remote url"
	set_git_remote_url(git_url)


@click.command('remote-reset-url')
@click.argument('app')
def remote_reset_url(app):
	"Reset app remote url to frappe official"
	git_url = "https://github.com/frappe/{}.git".format(app)
	set_git_remote_url(git_url)


@click.command('remote-urls')
def remote_urls():
	"Show apps remote url"
	for app in get_apps():
		repo_dir = get_repo_dir(app)

		if os.path.exists(os.path.join(repo_dir, '.git')):
			remote = get_remote(app)
			remote_url = subprocess.check_output(['git', 'config', '--get', 'remote.{}.url'.format(remote)], cwd=repo_dir).strip()
			print("{app}	{remote_url}".format(app=app, remote_url=remote_url))

