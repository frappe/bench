import os
import errno
import subprocess

def which(executable, raise_err = False):
	from distutils.spawn import find_executable
	exec_ = find_executable(executable)

	if not exec_ and raise_err:
		raise ValueError('{executable} not found.'.format(
			executable = executable
		))

	return exec_

def makedirs(dirs, exists_ok = False):
    try:
        os.makedirs(dirs)
    except OSError as e:
        if not exists_ok or e.errno != errno.EEXIST:
            raise

def popen(*params, **kwargs):
    output      = kwargs.get('output', False)
    directory   = kwargs.get('dir')
    environment = kwargs.get('env')
    shell       = kwargs.get('shell', True)
    raise_err   = kwargs.get('raise_err', True)

    environ     = os.environ.copy()
    if environment:
        environ.update(environment)

    command     = " ".join(params)
    
    proc        = subprocess.Popen(command,
        stdin   = subprocess.PIPE if output else None,
        stdout  = subprocess.PIPE if output else None,
        stderr  = subprocess.PIPE if output else None,
        env     = environ,
        cwd     = directory,
        shell   = shell
    )

    code       = proc.wait()

    if code and raise_err:
        raise subprocess.CalledProcessError(code, command)

    if output:
        output, error = proc.communicate()

        if output:
            output = output.decode('utf-8')
            if output.count('\n') == 1:
                output = output.strip('\n')

        if error:
            error  =  error.decode('utf-8')
            if  error.count('\n') == 1:
                error  =  error.strip('\n')

        return code, output, error
    else:
        return code