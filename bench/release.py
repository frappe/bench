#! env python
import json
import os
import sys
import semantic_version
import git
import json
import requests
import getpass
import argparse
import re
from requests.auth import HTTPBasicAuth
import requests.exceptions
from time import sleep
from .config.common_site_config import get_config
import click

github_username = None
github_password = None

def release(bench_path, app, bump_type, develop='develop', master='master',
		remote='upstream', owner='frappe', repo_name=None):

	validate(bench_path)

	bump(bench_path, app, bump_type, develop=develop, master=master, owner=owner,
		repo_name=repo_name, remote=remote)

def validate(bench_path):
	config = get_config(bench_path)
	if not config.get('release_bench'):
		print 'bench not configured to release'
		sys.exit(1)

	global github_username, github_password

	github_username = config.get('github_username')
	github_password = config.get('github_password')

	if not github_username:
		github_username = raw_input('Username: ')

	if not github_password:
		github_password = getpass.getpass()

	r = requests.get('https://api.github.com/user', auth=HTTPBasicAuth(github_username, github_password))
	r.raise_for_status()

def bump(bench_path, app, bump_type, develop, master, remote, owner, repo_name=None):
	assert bump_type in ['minor', 'major', 'patch', 'stable', 'prerelease']

	repo_path = os.path.join(bench_path, 'apps', app)
	update_branches_and_check_for_changelog(repo_path, develop, master, remote=remote)
	message = get_release_message(repo_path, develop=develop, master=master, remote=remote)

	if not message:
		print 'No commits to release'
		return

	print
	print message
	print

	click.confirm('Do you want to continue?', abort=True)

	new_version = bump_repo(repo_path, bump_type, develop=develop, master=master)
	commit_changes(repo_path, new_version)
	tag_name = create_release(repo_path, new_version, develop=develop, master=master)
	push_release(repo_path, develop=develop, master=master, remote=remote)
	create_github_release(repo_path, tag_name, message, remote=remote, owner=owner, repo_name=repo_name)
	print 'Released {tag} for {repo_path}'.format(tag=tag_name, repo_path=repo_path)

def update_branches_and_check_for_changelog(repo_path, develop='develop', master='master', remote='upstream'):

	update_branch(repo_path, master, remote=remote)
	update_branch(repo_path, develop, remote=remote)
	if develop != 'develop':
		update_branch(repo_path, 'develop', remote=remote)

	git.Repo(repo_path).git.checkout(develop)
	check_for_unmerged_changelog(repo_path)

def update_branch(repo_path, branch, remote):
	print "updating local branch of", repo_path, 'using', remote + '/' + branch

	repo = git.Repo(repo_path)
	g = repo.git
	g.fetch(remote)
	g.checkout(branch)
	g.reset('--hard', remote+'/'+branch)

def check_for_unmerged_changelog(repo_path):
	current = os.path.join(repo_path, os.path.basename(repo_path), 'change_log', 'current')
	if os.path.exists(current) and [f for f in os.listdir(current) if f != "readme.md"]:
		raise Exception("Unmerged change log! in " + repo_path)

def get_release_message(repo_path, develop='develop', master='master', remote='upstream'):
	print 'getting release message for', repo_path, 'comparing', master, '...', develop

	repo = git.Repo(repo_path)
	g = repo.git
	log = g.log('{remote}/{master}..{remote}/{develop}'.format(
		remote=remote, master=master, develop=develop), '--format=format:%s', '--no-merges')

	if log:
		return "* " + log.replace('\n', '\n* ')

def bump_repo(repo_path, bump_type, develop='develop', master='master'):
	current_version = get_current_version(repo_path)
	new_version = get_bumped_version(current_version, bump_type)

	print 'bumping version from', current_version, 'to', new_version

	set_version(repo_path, new_version)
	return new_version

def get_current_version(repo_path):
	# TODO clean this up!
	filename = os.path.join(repo_path, os.path.basename(repo_path), '__init__.py')
	with open(filename) as f:
		contents = f.read()
		match = re.search(r"^(\s*%s\s*=\s*['\\\"])(.+?)(['\"])(?sm)" % '__version__',
				contents)
		return match.group(2)

def get_bumped_version(version, bump_type):
	v = semantic_version.Version(version)
	if bump_type == 'minor':
		v.minor += 1
		v.patch = 0
		v.prerelease = None

	elif bump_type == 'major':
		v.major += 1
		v.minor = 0
		v.patch = 0
		v.prerelease = None

	elif bump_type == 'patch':
		v.patch += 1
		v.prerelease = None

	elif bump_type == 'stable':
		# remove pre-release tag
		v.prerelease = None

	elif bump_type == 'prerelease':
		if v.prerelease == None:
			v.prerelease = ('beta',)

		elif len(v.prerelease)==1:
			v.prerelease[1] = '1'

		else:
			v.prerelease[1] = str(int(v.prerelease[1]) + 1)

	return unicode(v)

def set_version(repo_path, version):
	set_filename_version(os.path.join(repo_path, os.path.basename(repo_path),'__init__.py'), version, '__version__')

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

def commit_changes(repo_path, new_version):
	print 'committing version change to', repo_path

	repo = git.Repo(repo_path)
	app_name = os.path.basename(repo_path)
	repo.index.add([os.path.join(app_name, '__init__.py')])
	repo.index.commit('bumped to version {}'.format(new_version))

def create_release(repo_path, new_version, develop='develop', master='master'):
	print 'creating release for version', new_version
	repo = git.Repo(repo_path)
	g = repo.git
	g.checkout(master)
	try:
		g.merge(develop, '--no-ff')
	except git.exc.GitCommandError, e:
		handle_merge_error(e, source=develop, target=master)

	tag_name = 'v' + new_version
	repo.create_tag(tag_name, message='Release {}'.format(new_version))
	g.checkout(develop)

	try:
		g.merge(master)
	except git.exc.GitCommandError, e:
		handle_merge_error(e, source=master, target=develop)

	if develop != 'develop':
		print 'merging master into develop'
		g.checkout('develop')
		try:
			g.merge(master)
		except git.exc.GitCommandError, e:
			handle_merge_error(e, source=master, target='develop')

	return tag_name

def handle_merge_error(e, source, target):
	print '-'*80
	print 'Error when merging {source} into {target}'.format(source=source, target=target)
	print e
	print 'You can open a new terminal, try to manually resolve the conflict/error and continue'
	print '-'*80
	click.confirm('Have you manually resolved the error?', abort=True)

def push_release(repo_path, develop='develop', master='master', remote='upstream'):
	print 'pushing branches', master, develop, 'of', repo_path
	repo = git.Repo(repo_path)
	g = repo.git
	args = [
		'{master}:{master}'.format(master=master),
		'{develop}:{develop}'.format(develop=develop)
	]

	if develop != 'develop':
		print 'pushing develop branch of', repo_path
		args.append('develop:develop')

	args.append('--tags')

	print g.push(remote, *args)

def create_github_release(repo_path, tag_name, message, remote='upstream', owner='frappe', repo_name=None,
		gh_username=None, gh_password=None):

	print 'creating release on github'

	global github_username, github_password
	if not (gh_username and gh_password):
		if not (github_username and github_password):
			raise Exception, "No credentials"
		gh_username = github_username
		gh_password = github_password

	repo_name = repo_name or os.path.basename(repo_path)
	data = {
		'tag_name': tag_name,
		'target_commitish': 'master',
		'name': 'Release ' + tag_name,
		'body': message,
		'draft': False,
		'prerelease': False
	}
	for i in xrange(3):
		try:
			r = requests.post('https://api.github.com/repos/{owner}/{repo_name}/releases'.format(
				owner=owner, repo_name=repo_name),
				auth=HTTPBasicAuth(gh_username, gh_password), data=json.dumps(data))
			r.raise_for_status()
			break
		except requests.exceptions.HTTPError:
			print 'request failed, retrying....'
			sleep(3*i + 1)
			if i !=2:
				continue
			else:
				print r.json()
				raise
	return r

