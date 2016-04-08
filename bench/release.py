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

repo_map = {
	'frappe': 'frappe',
	'erpnext': 'erpnext',
	'erpnext_shopify': 'erpnext_shopify',
	'paypal_integration': 'paypal_integration',
	'schools': 'schools'
}

def release(repo, bump_type, develop, master):
	if not get_config(".").get('release_bench'):
		print 'bench not configured to release'
		sys.exit(1)
	global github_username, github_password
	github_username = raw_input('username:')
	github_password = getpass.getpass()
	r = requests.get('https://api.github.com/user', auth=HTTPBasicAuth(github_username, github_password))
	r.raise_for_status()
	bump(repo, bump_type, develop=develop, master=master)

def bump(repo, bump_type, develop='develop', master='master', remote='upstream'):
	assert bump_type in ['minor', 'major', 'patch']
	update_branches_and_check_for_changelog(repo, bump_type, develop=develop, master=master, remote=remote)
	message = get_release_message(repo, develop_branch=develop, master_branch=master)
	if not message:
		print 'No commits to release'
		return

	print
	print message
	print

	click.confirm('Do you want to continue?', abort=True)

	new_version = bump_repo(repo, bump_type, develop=develop, master=master, remote=remote)
	commit_changes(repo, new_version)
	tag_name = create_release(repo, new_version, develop_branch=develop, master_branch=master)
	push_release(repo, develop_branch=develop, master_branch=master)
	create_github_release('frappe', repo, tag_name, message)
	print 'Released {tag} for {repo}'.format(tag=tag_name, repo=repo)

def update_branches_and_check_for_changelog(repo, bump_type, develop='develop', master='master', remote='upstream'):
	update_branch(repo, master, remote=remote)
	update_branch(repo, develop, remote=remote)
	git.Repo(repo).git.checkout(develop)
	check_for_unmerged_changelog(repo)

def update_branch(repo_path, branch, remote='origin'):
	print "updating local branch of", repo_path, 'using', remote + '/' + branch

	repo = git.Repo(repo_path)
	g = repo.git
	g.fetch(remote)
	g.checkout(branch)
	g.reset('--hard', remote+'/'+branch)

def check_for_unmerged_changelog(repo):
	current = os.path.join(repo, os.path.basename(repo), 'change_log', 'current')
	if os.path.exists(current) and [f for f in os.listdir(current) if f != "readme.md"]:
		raise Exception("Unmerged change log! in " + repo)

def get_release_message(repo_path, develop_branch='develop', master_branch='master'):
	print 'getting release message for', repo_path, 'comparing', master_branch, '...', develop_branch
	repo = git.Repo(repo_path)
	g = repo.git
	log = g.log('upstream/{master_branch}..upstream/{develop_branch}'.format(master_branch=master_branch, develop_branch=develop_branch), '--format=format:%s', '--no-merges')
	if log:
		return "* " + log.replace('\n', '\n* ')


def bump_repo(repo, bump_type, develop='develop', master='master', remote='upstream'):
	current_version = get_current_version(repo)
	new_version = get_bumped_version(current_version, bump_type)

	print 'bumping version from', current_version, 'to', new_version

	set_version(repo, new_version)
	return new_version

def get_current_version(repo):
	filename = os.path.join(repo, 'setup.py')
	with open(filename) as f:
		contents = f.read()
		match = re.search(r"^(\s*%s\s*=\s*['\\\"])(.+?)(['\"])(?sm)" % 'version',
				contents)
		return match.group(2)

def get_bumped_version(version, bump_type):
	v = semantic_version.Version(version)
	if bump_type == 'minor':
		v.minor += 1
		v.patch = 0
	elif bump_type == 'major':
		v.major += 1
		v.minor = 0
		v.patch = 0
	elif bump_type == 'patch':
		v.patch += 1
	return unicode(v)

def set_version(repo, version):
	set_setuppy_version(repo, version)
	set_versionpy_version(repo, version)
	set_hooks_version(repo, version)

def set_setuppy_version(repo, version):
	set_filename_version(os.path.join(repo, 'setup.py'), version, 'version')

def set_versionpy_version(repo, version):
	set_filename_version(os.path.join(repo, os.path.basename(repo),'__version__.py'), version, '__version__')

def set_hooks_version(repo, version):
	set_filename_version(os.path.join(repo, os.path.basename(repo),'hooks.py'), version, 'app_version')

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

def commit_changes(repo_path, version):
	print 'committing version change to', repo_path

	repo = git.Repo(repo_path)
	repo_name = os.path.basename(repo_path)
	repo.index.add(['setup.py'])
	repo.index.add([os.path.join(repo_name, '__version__.py')])
	repo.index.add([os.path.join(repo_name, 'hooks.py')])
	repo.index.commit('bumped to version {}'.format(version))

def create_release(repo_path, version, remote='origin', develop_branch='develop', master_branch='master'):
	print 'creating release for version', version
	repo = git.Repo(repo_path)
	g = repo.git
	g.checkout(master_branch)
	g.merge(develop_branch, '--no-ff')
	tag_name = 'v' + version
	repo.create_tag(tag_name, message='Release {}'.format(version))
	g.checkout(develop_branch)
	g.merge(master_branch)

	if develop_branch != 'develop':
		print 'merging master into develop'
		g.checkout('develop')
		g.merge(master_branch)

	return tag_name

def push_release(repo_path, develop_branch='develop', master_branch='master'):
	print 'pushing branches', master_branch, develop_branch, 'of', repo_path
	repo = git.Repo(repo_path)
	g = repo.git
	print g.push('upstream', '{master}:{master}'.format(master=master_branch), '{develop}:{develop}'.format(develop=develop_branch), '--tags')

def create_github_release(owner, repo, tag_name, log, gh_username=None, gh_password=None):
	print 'creating release on github'

	global github_username, github_password
	if not (gh_username and gh_password):
		if not (github_username and github_password):
			raise Exception, "No credentials"
		gh_username = github_username
		gh_password = github_password
	repo = repo_map[os.path.basename(repo)]
	data = {
		'tag_name': tag_name,
		'target_commitish': 'master',
		'name': 'Release ' + tag_name,
		'body': log,
		'draft': False,
		'prerelease': False
	}
	for i in xrange(3):
		try:
			r = requests.post('https://api.github.com/repos/{owner}/{repo}/releases'.format(owner=owner, repo=repo), auth=HTTPBasicAuth(gh_username, gh_password), data=json.dumps(data))
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

