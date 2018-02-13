from __future__ import absolute_import

import logging

import elasticsearch as es

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class ESearch(object):
    """
    Helper for ElasticSearch
    """
    def __init__(self,
        host = 'localhost', # TODO: multiple hosts :)
        port = 9200
    ):
        self.client = es.Elasticsearch()
    
    def insert(self, index, create = True, refresh = True):
        """
        :param: refresh - Make data available immediately for search.
        """
        es = self.client
        if not es.indices.exists(index) and create:
            log.debug('Creating Index {index}'.format(index = index))
            res = es.indices.create(index = index)
            log.debug('Response: {response}'.format(response = res))
        else:
            raise ValueError('Index {index} does not exist.'.format(index = index))
        
        

        