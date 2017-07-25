#! env python
import os
import git
import click
from .config.common_site_config import get_config

github_username = None
github_password = None

def prepare_staging(bench_path, app, remote='upstream'):
	from .release import get_release_message
	validate(bench_path)

	repo_path = os.path.join(bench_path, 'apps', app)
	update_branches(repo_path, remote)
	message = get_release_message(repo_path, from_branch='develop', to_branch='staging', remote=remote)

	if not message:
		print('No commits to release')
		return

	print()
	print(message)
	print()

	click.confirm('Do you want to continue?', abort=True)

	create_staging(repo_path)
	push_commits(repo_path)

def validate(bench_path):
	from .release import validate

	config = get_config(bench_path)
	validate(bench_path, config)

def update_branches(repo_path, remote):
	from .release import update_branch
	update_branch(repo_path, 'staging', remote)
	update_branch(repo_path, 'develop', remote)

	git.Repo(repo_path).git.checkout('develop')

def create_staging(repo_path, from_branch='develop'):
	from .release import handle_merge_error

	print('creating staging from', from_branch)
	repo = git.Repo(repo_path)
	g = repo.git
	g.checkout('staging')
	try:
		g.merge(from_branch, '--no-ff')
	except git.exc.GitCommandError as e:
		handle_merge_error(e, source=from_branch, target='staging')
	
	g.checkout(from_branch)
	try:
		g.merge('staging')
	except git.exc.GitCommandError as e:
		handle_merge_error(e, source='staging', target=from_branch)
	
def push_commits(repo_path, remote='upstream'):
	print('pushing staging branch of', repo_path)

	repo = git.Repo(repo_path)
	g = repo.git

	args = [
		'develop:develop',
		'staging:staging'
	]

	print(g.push(remote, *args))
