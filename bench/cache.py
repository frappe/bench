# imports - standard imports
import os
import os.path as osp

# imports - module imports
from bench import utils

class Cache(object):
	def __init__(self, location = None, dirname = None):
		self.location = utils.assign_if_empty(location, osp.expanduser('~'))
		self.dirname  = utils.assign_if_empty(dirname,  '.frappe')

	def create(self, exists_ok = True):
		path = osp.join(self.location, self.dirname)

		utils.makedirs(path, exists_ok = True)
		
	def get(app):
		path = osp.join(self.location, self.dirname, 'app')
		utils.makedirs(path, exists_ok = True)

		# if not osp.exists(osp.join(path, app)):
			
