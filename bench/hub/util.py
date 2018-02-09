import os
import os.path as osp
import errno

def makedirs(dirs, exists_ok = False):
    try:
        os.makedirs(dirs)
    except OSError as e:
        if not exists_ok or e.errno != errno.EEXIST:
            raise

def assign_if_empty(a, b):
    if not a:
        a = b
    return a