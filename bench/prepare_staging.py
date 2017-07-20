#! env python
import os
import git
import click

github_username = None
github_password = None

def prepare_staging(bench_path, app, remote='upstream'):
	from .release import get_release_message
	validate(bench_path)

	repo_path = os.path.join(bench_path, 'apps', app)
	update_branches(repo_path, remote)
	message = get_release_message(repo_path, develop='develop', master='staging', remote=remote)

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
	validate(bench_path)

def update_branches(repo_path, remote):
	from .release import update_branch
	update_branch(repo_path, 'staging', remote)
	update_branch(repo_path, 'develop', remote)

	git.Repo(repo_path).git.checkout('develop')

def create_staging(repo_path, develop='develop'):
	from .release import handle_merge_error

	print('creating staging from', develop)
	repo = git.Repo(repo_path)
	g = repo.git
	g.checkout('staging')
	try:
		g.merge(develop, '--no-ff')
	except git.exc.GitCommandError as e:
		handle_merge_error(e, source=develop, target='staging')
	
	g.checkout(develop)
	try:
		g.merge('staging')
	except git.exc.GitCommandError as e:
		handle_merge_error(e, source='staging', target=develop)
	
def push_commits(repo_path, remote='upstream'):
	print('pushing staging branch of', repo_path)

	repo = git.Repo(repo_path)
	g = repo.git

	args = [
		'develop:develop',
		'staging:staging'
	]

	print(g.push(remote, *args))
