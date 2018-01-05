# imports - standard imports
import os
import os.path as osp

# imports - third-party imports
import git

# imports - module imports
from bench import utils

class Cache(object):
	def __init__(self, location = None, dirname = None):
		self.location = utils.assign_if_empty(location, osp.expanduser('~'))
		self.dirname  = utils.assign_if_empty(dirname,  '.frappe')

	def create(self, exists_ok = True):
		path = osp.join(self.location, self.dirname)
		utils.makedirs(path, exists_ok = exists_ok)
		
	def get(self, app, target = None):
		path = osp.join(self.location, self.dirname)
		dest = utils.assign_if_empty(target, os.getcwd())

		# check url
		if not utils.check_url(app, raise_err = False):
			pass

		git.Repo.clone_from(app , path)
		git.Repo.clone_from(path, dest)