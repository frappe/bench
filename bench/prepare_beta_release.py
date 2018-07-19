#! env python
import os
import git
import click
from .config.common_site_config import get_config
import semantic_version

github_username = None
github_password = None

def prepare_beta_release(bench_path, app, owner='frappe', remote='upstream'):
	from .release import get_release_message

	beta_hotfix = ''
	beta_master = click.prompt('Branch name for beta release', type=str)

	if click.confirm("Do you want to setup hotfix for beta ?"):
		beta_hotfix = click.prompt('Branch name for beta hotfix ({}_hotifx)'.format(beta_master), type=str)

	validate(bench_path)
	repo_path = os.path.join(bench_path, 'apps', app)
	version = get_bummped_version(repo_path)

	update_branch(repo_path, remote)
	prepare_beta_master(repo_path, beta_master, version, remote)

	if beta_hotfix:
		prepare_beta_hotfix(repo_path, beta_hotfix, remote)
	
	tag_name = merge_beta_release_to_develop(repo_path, beta_master, remote, version)
	push_branches(repo_path, beta_master, beta_hotfix, remote)
	create_github_release(repo_path, tag_name, '', owner, remote)

def validate(bench_path):
	from .release import validate

	config = get_config(bench_path)
	validate(bench_path, config)

def get_bummped_version(repo_path):
	from .release import get_current_version
	current_version = get_current_version(repo_path, 'master')

	v = semantic_version.Version(current_version)

	if v.major:
		v.major += 1
		v.minor = 0
		v.patch = 0
		v.prerelease = ['staging']

	return str(v)

def update_branch(repo_path, remote):
	from .release import update_branch
	update_branch(repo_path, 'develop', remote)

def prepare_beta_master(repo_path, beta_master, version, remote):
	g = git.Repo(repo_path).git
	g.checkout(b=beta_master)

	set_beta_version(repo_path, version)

def set_beta_version(repo_path, version):
	from .release import set_filename_version
	set_filename_version(os.path.join(repo_path, os.path.basename(repo_path),'hooks.py'), version, 'staging_version')

	repo = git.Repo(repo_path)
	app_name = os.path.basename(repo_path)
	repo.index.add([os.path.join(app_name, 'hooks.py')])
	repo.index.commit('bumped to version {}'.format(version))
	

def prepare_beta_hotfix(repo_path, beta_hotfix, remote):
	g = git.Repo(repo_path).git
	g.checkout(b=beta_hotfix)


def merge_beta_release_to_develop(repo_path, beta_master, remote, version):
	from .release import handle_merge_error

	repo = git.Repo(repo_path)
	g = repo.git

	tag_name = 'v' + version
	repo.create_tag(tag_name, message='Release {}'.format(version))

	g.checkout('develop')

	try:
		g.merge(beta_master)
	except git.exc.GitCommandError as e:
		handle_merge_error(e, source=beta_master, target='develop')

	return tag_name

def push_branches(repo_path, beta_master, beta_hotfix, remote):
	repo = git.Repo(repo_path)
	g = repo.git

	args = [
		'develop:develop',
		'{beta_master}:{beta_master}'.format(beta_master=beta_master),
	]

	if beta_hotfix:
		args.append('{beta_hotfix}:{beta_hotfix}'.format(beta_hotfix=beta_hotfix))
	
	args.append('--tags')

	print("Pushing branches")
	print(g.push(remote, *args))

def create_github_release(repo_path, tag_name, message, owner, remote):
	from .release import create_github_release

	create_github_release(repo_path, tag_name, message, remote=remote, owner=owner, 
		repo_name=None, gh_username=github_username, gh_password=github_password)