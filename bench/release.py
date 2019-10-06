#! env python
import json
import os
import sys
import semantic_version
import git
import requests
import getpass
import re
from requests.auth import HTTPBasicAuth
import requests.exceptions
from time import sleep
from .config.common_site_config import get_config
import click

branches_to_update = {
	'develop': [],
	'version-11-hotfix': [],
	'version-12-hotfix': [],
}

releasable_branches = ['master']

github_username = None
github_password = None

def release(bench_path, app, bump_type, from_branch, to_branch,
		remote='upstream', owner='frappe', repo_name=None, frontport=True):

	confirm_testing()
	config = get_config(bench_path)

	if not config.get('release_bench'):
		print('bench not configured to release')
		sys.exit(1)


	if config.get('branches_to_update'):
		branches_to_update.update(config.get('branches_to_update'))

	if config.get('releasable_branches'):
		releasable_branches.extend(config.get('releasable_branches',[]))

	validate(bench_path, config)

	bump(bench_path, app, bump_type, from_branch=from_branch, to_branch=to_branch, owner=owner,
		repo_name=repo_name, remote=remote, frontport=frontport)

def validate(bench_path, config):
	global github_username, github_password

	github_username = config.get('github_username')
	github_password = config.get('github_password')

	if not github_username:
		github_username = click.prompt('Username', type=str)

	if not github_password:
		github_password = getpass.getpass()

	r = requests.get('https://api.github.com/user', auth=HTTPBasicAuth(github_username, github_password))
	r.raise_for_status()

def confirm_testing():
	print('')
	print('================ CAUTION ==================')
	print('Never miss this, even if it is a really small release!!')
	print('Manual Testing Checklisk: https://github.com/frappe/bench/wiki/Testing-Checklist')
	print('')
	print('')
	click.confirm('Is manual testing done?', abort = True)
	click.confirm('Have you added the change log?', abort = True)

def bump(bench_path, app, bump_type, from_branch, to_branch, remote, owner, repo_name=None, frontport=True):
	assert bump_type in ['minor', 'major', 'patch', 'stable', 'prerelease']

	repo_path = os.path.join(bench_path, 'apps', app)
	push_branch_for_old_major_version(bench_path, bump_type, app, repo_path, from_branch, to_branch, remote, owner)
	update_branches_and_check_for_changelog(repo_path, from_branch, to_branch, remote=remote)
	message = get_release_message(repo_path, from_branch=from_branch, to_branch=to_branch, remote=remote)

	if not message:
		print('No commits to release')
		return

	print()
	print(message)
	print()

	click.confirm('Do you want to continue?', abort=True)

	new_version = bump_repo(repo_path, bump_type, from_branch=from_branch, to_branch=to_branch)
	commit_changes(repo_path, new_version, to_branch)
	tag_name = create_release(repo_path, new_version, from_branch=from_branch, to_branch=to_branch, frontport=frontport)
	push_release(repo_path, from_branch=from_branch, to_branch=to_branch, remote=remote)
	prerelease = True if 'beta' in new_version else False
	create_github_release(repo_path, tag_name, message, remote=remote, owner=owner, repo_name=repo_name, prerelease=prerelease)
	print('Released {tag} for {repo_path}'.format(tag=tag_name, repo_path=repo_path))

def update_branches_and_check_for_changelog(repo_path, from_branch, to_branch, remote='upstream'):

	update_branch(repo_path, to_branch, remote=remote)
	update_branch(repo_path, from_branch, remote=remote)

	for branch in branches_to_update[from_branch]:
		update_branch(repo_path, branch, remote=remote)

	git.Repo(repo_path).git.checkout(from_branch)
	check_for_unmerged_changelog(repo_path)

def update_branch(repo_path, branch, remote):
	print("updating local branch of", repo_path, 'using', remote + '/' + branch)

	repo = git.Repo(repo_path)
	g = repo.git
	g.fetch(remote)
	g.checkout(branch)
	g.reset('--hard', remote+'/'+branch)

def check_for_unmerged_changelog(repo_path):
	current = os.path.join(repo_path, os.path.basename(repo_path), 'change_log', 'current')
	if os.path.exists(current) and [f for f in os.listdir(current) if f != "readme.md"]:
		raise Exception("Unmerged change log! in " + repo_path)

def get_release_message(repo_path, from_branch, to_branch, remote='upstream'):
	print('getting release message for', repo_path, 'comparing', to_branch, '...', from_branch)

	repo = git.Repo(repo_path)
	g = repo.git
	log = g.log('{remote}/{to_branch}..{remote}/{from_branch}'.format(
		remote=remote, to_branch=to_branch, from_branch=from_branch), '--format=format:%s', '--no-merges')

	if log:
		return "* " + log.replace('\n', '\n* ')

def bump_repo(repo_path, bump_type, from_branch, to_branch):
	current_version = get_current_version(repo_path, to_branch)
	new_version = get_bumped_version(current_version, bump_type)

	print('bumping version from', current_version, 'to', new_version)

	set_version(repo_path, new_version, to_branch)
	return new_version

def get_current_version(repo_path, to_branch):
	# TODO clean this up!
	version_key = '__version__'

	if to_branch.lower() in releasable_branches:
		filename = os.path.join(repo_path, os.path.basename(repo_path), '__init__.py')
	else:
		filename = os.path.join(repo_path, os.path.basename(repo_path), 'hooks.py')
		version_key = 'staging_version'

	with open(filename) as f:
		contents = f.read()
		match = re.search(r"^(\s*%s\s*=\s*['\\\"])(.+?)(['\"])(?sm)" % version_key,
				contents)
		return match.group(2)

def get_bumped_version(version, bump_type):
	v = semantic_version.Version(version)
	if bump_type == 'major':
		v.major += 1
		v.minor = 0
		v.patch = 0
		v.prerelease = None

	elif bump_type == 'minor':
		v.minor += 1
		v.patch = 0
		v.prerelease = None

	elif bump_type == 'patch':
		if v.prerelease == ():
			v.patch += 1
			v.prerelease = None

		elif len(v.prerelease) == 2:
			v.prerelease = ()

	elif bump_type == 'stable':
		# remove pre-release tag
		v.prerelease = None

	elif bump_type == 'prerelease':
		if v.prerelease == ():
			v.patch += 1
			v.prerelease = ('beta', '1')

		elif len(v.prerelease) == 2:
			v.prerelease = ('beta', str(int(v.prerelease[1]) + 1))

		else:
			raise ("Something wen't wrong while doing a prerelease")

	else:
		raise ("bump_type not amongst [major, minor, patch, prerelease]")

	return str(v)

def set_version(repo_path, version, to_branch):
	if to_branch.lower() in releasable_branches:
		set_filename_version(os.path.join(repo_path, os.path.basename(repo_path),'__init__.py'), version, '__version__')
	else:
		set_filename_version(os.path.join(repo_path, os.path.basename(repo_path),'hooks.py'), version, 'staging_version')

	# TODO fix this
	# set_setuppy_version(repo_path, version)
	# set_versionpy_version(repo_path, version)
	# set_hooks_version(repo_path, version)

# def set_setuppy_version(repo_path, version):
# 	set_filename_version(os.path.join(repo_path, 'setup.py'), version, 'version')
#
# def set_versionpy_version(repo_path, version):
# 	set_filename_version(os.path.join(repo_path, os.path.basename(repo_path),'__version__.py'), version, '__version__')
#
# def set_hooks_version(repo_path, version):
# 	set_filename_version(os.path.join(repo_path, os.path.basename(repo_path),'hooks.py'), version, 'app_version')

def set_filename_version(filename, version_number, pattern):
	changed = []

	def inject_version(match):
		before, old, after = match.groups()
		changed.append(True)
		return before + version_number + after

	with open(filename) as f:
		contents = re.sub(r"^(\s*%s\s*=\s*['\\\"])(.+?)(['\"])(?sm)" % pattern,
				inject_version, f.read())

	if not changed:
		raise Exception('Could not find %s in %s', pattern, filename)

	with open(filename, 'w') as f:
		f.write(contents)

def commit_changes(repo_path, new_version, to_branch):
	print('committing version change to', repo_path)

	repo = git.Repo(repo_path)
	app_name = os.path.basename(repo_path)

	if to_branch.lower() in releasable_branches:
		repo.index.add([os.path.join(app_name, '__init__.py')])
	else:
		repo.index.add([os.path.join(app_name, 'hooks.py')])

	repo.index.commit('bumped to version {}'.format(new_version))

def create_release(repo_path, new_version, from_branch, to_branch, frontport=True):
	print('creating release for version', new_version)
	repo = git.Repo(repo_path)
	g = repo.git
	g.checkout(to_branch)
	try:
		g.merge(from_branch, '--no-ff')
	except git.exc.GitCommandError as e:
		handle_merge_error(e, source=from_branch, target=to_branch)

	tag_name = 'v' + new_version
	repo.create_tag(tag_name, message='Release {}'.format(new_version))
	g.checkout(from_branch)

	try:
		g.merge(to_branch)
	except git.exc.GitCommandError as e:
		handle_merge_error(e, source=to_branch, target=from_branch)

	if frontport:
		for branch in branches_to_update[from_branch]:
			print ("Front porting changes to {}".format(branch))
			print('merging {0} into'.format(to_branch), branch)
			g.checkout(branch)
			try:
				g.merge(to_branch)
			except git.exc.GitCommandError as e:
				handle_merge_error(e, source=to_branch, target=branch)

	return tag_name

def handle_merge_error(e, source, target):
	print('-'*80)
	print('Error when merging {source} into {target}'.format(source=source, target=target))
	print(e)
	print('You can open a new terminal, try to manually resolve the conflict/error and continue')
	print('-'*80)
	click.confirm('Have you manually resolved the error?', abort=True)

def push_release(repo_path, from_branch, to_branch, remote='upstream'):
	print('pushing branches', to_branch, from_branch, 'of', repo_path)
	repo = git.Repo(repo_path)
	g = repo.git
	args = [
		'{to_branch}:{to_branch}'.format(to_branch=to_branch),
		'{from_branch}:{from_branch}'.format(from_branch=from_branch)
	]

	for branch in branches_to_update[from_branch]:
		print('pushing {0} branch of'.format(branch), repo_path)
		args.append('{branch}:{branch}'.format(branch=branch))

	args.append('--tags')

	print(g.push(remote, *args))

def create_github_release(repo_path, tag_name, message, remote='upstream', owner='frappe', repo_name=None,
		gh_username=None, gh_password=None, prerelease=False):

	print('creating release on github')

	global github_username, github_password
	if not (gh_username and gh_password):
		if not (github_username and github_password):
			raise Exception("No credentials")
		gh_username = github_username
		gh_password = github_password

	repo_name = repo_name or os.path.basename(repo_path)
	data = {
		'tag_name': tag_name,
		'target_commitish': 'master',
		'name': 'Release ' + tag_name,
		'body': message,
		'draft': False,
		'prerelease': prerelease
	}
	for i in range(3):
		try:
			r = requests.post('https://api.github.com/repos/{owner}/{repo_name}/releases'.format(
				owner=owner, repo_name=repo_name),
				auth=HTTPBasicAuth(gh_username, gh_password), data=json.dumps(data))
			r.raise_for_status()
			break
		except requests.exceptions.HTTPError:
			print('request failed, retrying....')
			sleep(3*i + 1)
			if i !=2:
				continue
			else:
				print(r.json())
				raise
	return r

def push_branch_for_old_major_version(bench_path, bump_type, app, repo_path, from_branch, to_branch, remote, owner):
	if bump_type != 'major':
		return

	current_version = get_current_version(repo_path)
	old_major_version_branch = "v{major}.x.x".format(major=current_version.split('.')[0])

	click.confirm('Do you want to push {branch}?'.format(branch=old_major_version_branch), abort=True)

	update_branch(repo_path, to_branch, remote=remote)

	g = git.Repo(repo_path).git
	g.checkout(b=old_major_version_branch)

	args = [
		'{old_major_version_branch}:{old_major_version_branch}'.format(old_major_version_branch=old_major_version_branch),
	]

	print("Pushing {old_major_version_branch} ".format(old_major_version_branch=old_major_version_branch))
	print(g.push(remote, *args))
