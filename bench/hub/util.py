import os
import os.path as osp
import errno

from distutils.spawn import find_executable

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

def which(executable, raise_err = False):
    exec_ = find_executable(executable)
    if not exec_ and raise_err:
        raise ValueError('{executable} executable not found'.format(
            executable = executable
        ))
    return exec_