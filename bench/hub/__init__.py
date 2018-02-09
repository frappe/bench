from __future__ import absolute_import

import os
import os.path as osp

from bench.hub.config import set_config

def init(bench = None, group = None):
    set_config('foo', 'bar')


    