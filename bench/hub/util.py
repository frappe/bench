import os
import os.path as osp
import errno
import uuid

import subprocess

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

def popen(command, *args, **kwargs):
    output     = kwargs.get('output', True)
    raise_err  = kwargs.get('raise_err')
    directory  = kwargs.get('directory')

    proc       = subprocess.Popen(command,
        stdout = None if output else subprocess.PIPE,
        stderr = None if output else subprocess.PIPE,
        shell  = True,
        cwd    = directory
    )
    
    return_    = proc.wait()

    if raise_err:
        raise subprocess.CalledProcessError(return_, command)

    return return_

def get_uuid():
    string   = str(uuid.uuid4())
    sanitize = string.replace('-', '')

    return sanitize