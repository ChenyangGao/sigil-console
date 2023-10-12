#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 6)
__all__ = ["run_in_process", "restart_program", "run_file", "run_path", 
           "ctx_run", "run", "ctx_load", "load", "prun", "prun_module", 
           "pid_exists", "wait_for_pid_finish"]

import errno
import inspect
import multiprocessing
import re
import subprocess
import sys

from contextlib import contextmanager
from functools import partial
from os import execl, getcwd, getpid, kill, path as _path
from runpy import run_path
from subprocess import (
    getoutput, CalledProcessError, CompletedProcess, Popen, TimeoutExpired, PIPE
)
from sys import argv, executable
from time import sleep
from typing import (
    Any, Callable, Final, Generator, Optional, Sequence, Union
)
from types import CodeType, ModuleType
from urllib.parse import unquote
from urllib.request import urlopen, Request

from .cm import ensure_cm
from .temporary import temp_wdir, temp_sys_modules, _PREFIXES
from .undefined import undefined 


_PLATFORM_IS_WINDOWS: Final[bool] = __import__("platform").system() == "Windows"


def _startswith_protocol(
    path: Union[bytes, str], 
    _cre=re.compile('^[_a-zA-Z][_a-zA-Z0-9]+://'),
    _creb=re.compile(b'^[_a-zA-Z][_a-zA-Z0-9]+://'),
) -> bool:
    if isinstance(path, bytes):
        return _creb.match(path) is not None
    else:
        return _cre.match(path) is not None


def _update_signature(
    standard_unit: Callable, 
    machining_unit: Optional[Callable] = None, 
    return_annotation=undefined,
):
    if machining_unit is None:
        return partial(
            _update_signature, 
            standard_unit, 
            return_annotation=return_annotation, 
        )
    sig: inspect.Signature = inspect.signature(standard_unit)
    if return_annotation is not undefined:
        sig = sig.replace(return_annotation=return_annotation)
    machining_unit.__signature__ = sig # type: ignore

    machining_unit.__doc__ = standard_unit.__doc__
    machining_unit.__annotations__ = {
        **standard_unit.__annotations__, 
        'run': return_annotation, 
    }
    return machining_unit


def _read_source(path) -> tuple[str, str]:
    file: str
    if isinstance(path, Request):
        req = urlopen(path)
        file = req.full_url
    elif isinstance(path, str):
        file = path
        if path.startswith(('http://', 'https://')):
            req = urlopen(path)
        else:
            req = open(path, 'rb')
    else:
        raise TypeError(type(path))

    with req as f:
        return file, f.read().decode('utf-8')


def _pipe_result(
    pipe, 
    fn: Callable, 
    args: tuple = (), 
    kwargs: dict = {}, 
) -> tuple[bool, Any]:
    try:
        r = fn(*args, **kwargs)
        pipe.send((True, r))
        return (True, r)
    except BaseException as exc:
        pipe.send((False, exc))
        return (False, exc)


def run_in_process(fn: Callable, /, *args, **kwargs):
    'Run function in child process.'
    recv, send = multiprocessing.Pipe(duplex=False)
    try:
        p = multiprocessing.Process(
            target=_pipe_result, 
            args=(send, fn, args, kwargs), 
            daemon=True, 
        )
        p.start()
        p.join()
        is_success, ret = recv.recv()
        if is_success:
            return ret
        raise ret
    finally:
        recv.close()
        send.close()


def restart_program(argv=argv):
    'restart the program'
    execl(executable, executable, *argv)


def run_file(
    path, 
    namespace: Optional[dict] = None, 
    read_source: Callable[..., tuple[str, str]] = _read_source,
) -> dict:
    '''Run a [file], from a [file] | [url] | [source object].

    :param path: The path or source object of the python script.
    :param namespace: Execute the given source in the context of namespace.
                      If it is None (the default), will create a new dict().
    :param read_source: Take path or request source, return tuple of file path and text.

    :return: Dictionary of script execution results.
    '''
    file_path, source = read_source(path)

    if namespace is None:
        namespace = {
            '__name__': '__main__', 
            '__package__': '', 
            '__file__': file_path, 
        }

    code = compile(source, file_path, 'exec')
    exec(code, namespace)
    return namespace


@contextmanager
def ctx_run(
    path: str, 
    namespace: Optional[dict] = None, 
    wdir: Optional[str] = None, 
    mainfile: Union[str, tuple[str, ...]] = ('__main__.py', 'main.py', '__init__.py'),
    clean_sys_modules: bool = True,
    prefixes_not_clean: tuple[str, ...] = _PREFIXES,
    restore_sys_modules: bool = True,
) -> Generator[dict[str, Any], None, None]:
    '''Run a [file] / [mainfile in directory], from a [file] | [url] | [directory].

    :param path: The path of file or directory of the python script.
    :param namespace: Execute the given source in the context of namespace.
                      If it is None (the default), will create a new dict().
    :param wdir: Temporay working directory, if it is None (the default), 
                 then use the current working directory.
    :param mainfile: If the `path` is a directory, according to this parameter, 
                     an existing main file will be used.
    :param clean_sys_modules: Determine whether to restore `sys.modules` at the beginning.
        If `clean_sys_modules` is True, it will retain built-in modules and standard libraries and 
        site-packages modules / packages, but clear namespace packages and any other modules / packages.
    :param prefixes_not_clean: Modules and packages prefixed with `prefixes_not_clean` will not be cleaned up.
    :param restore_sys_modules: Determine whether to restore `sys.modules` at the end.

    :return: Dictionary of script execution results.

    Reference:
        - [How to Run Your Python Scripts](https://realpython.com/run-python-scripts/)

    Tips: You can also use other functions as following
        - [runpy.run_path](https://docs.python.org/3/library/runpy.html#runpy.run_path)
        - [importlib.import_module](https://docs.python.org/3/library/importlib.html#importlib.import_module)
        - [spyder runfile](https://github.com/spyder-ide/spyder-kernels/blob/master/spyder_kernels/customize/spydercustomize.py#L486)
    '''
    # If you want to run as main module, set namespace['__name__'] = '__main__'
    # TODO: run a .zip or .egg file
    if wdir is None:
        wdir = getcwd()
    else:
        wdir = _path.abspath(wdir)

    if _startswith_protocol(path):
        file_ = path = unquote(path)
        mdir = None
        module_name = _path.splitext(_path.basename(path))[0]
        package_name = ''
        source = urlopen(path).read().decode('utf-8')
    else:
        file_ = path = _path.abspath(path)
        if _path.isdir(path):
            mdir = path
            module_name = package_name = _path.basename(path)
            if isinstance(mainfile, str):
                file_ = _path.join(path, mainfile)
            else:
                notfound_files = []
                for mainfile_ in mainfile:
                    file_ = _path.join(path, mainfile_)
                    if _path.exists(file_):
                        break
                    notfound_files.append(file_)
                else:
                    raise FileNotFoundError(notfound_files)
        else:
            mdir = _path.dirname(path)
            module_name = _path.splitext(_path.basename(path))[0]
            package_name = ''

        source = open(file_, encoding='utf-8').read()

    if namespace is None:
        namespace = {'__name__': module_name}
    elif not namespace.get('__name__'):
        namespace['__name__'] = module_name

    namespace['__file__'] = file_
    namespace['__package__'] = package_name

    with temp_sys_modules(
            mdir, 
            clean=clean_sys_modules, 
            restore=restore_sys_modules,
            prefixes_not_clean=prefixes_not_clean,
        ), \
        ensure_cm(None if wdir == getcwd() else temp_wdir(wdir)) \
    :
        code: CodeType = compile(source, path, 'exec')

        exec(code, namespace)

        yield dict(
            namespace=namespace,
            path=path, 
            code=code, 
            sys_path=sys.path.copy(),
            sys_modules=sys.modules.copy(),
        )


@_update_signature(ctx_run, return_annotation=dict[str, Any])
def run(*args, **kwargs):
    with ctx_run(*args, **kwargs) as d:
        return d


@contextmanager
def ctx_load(
    path: str, 
    wdir: Optional[str] = None,
    mainfile: Union[str, tuple[str, ...]] = '__init__.py',
    as_sys_module: bool = False,
    prefixes_not_clean: tuple[str, ...] = _PREFIXES,
) -> Generator[ModuleType, None, None]:
    '''Load a [module] | [package], from a [file] | [directory] | [url].

    :param path: The path of file or directory of the python script.
    :param wdir: Temporay working directory, if it is None (the default), 
                 then use the current working directory.
    :param mainfile: If the `path` is a directory, according to this parameter, 
                     an existing main file will be used.
    :param as_sys_module: If True, module will be set to sys.modules.
    :param prefixes_not_clean: Modules and packages prefixed with `prefixes_not_clean` will not be cleaned up.

    :return: A new module.
    '''
    # TODO: load a .zip or .egg file
    mod: ModuleType = ModuleType('')
    info: dict[str, Any]
    with ctx_run(
        path, mod.__dict__, 
        wdir=wdir, 
        mainfile=mainfile, 
        clean_sys_modules=not as_sys_module,
        restore_sys_modules=not as_sys_module,
        prefixes_not_clean=prefixes_not_clean,
    ) as info:
        if as_sys_module:
            sys.modules[info['path']] = mod
        yield mod


@_update_signature(ctx_load, return_annotation=ModuleType)
def load(*args, **kwargs):
    with ctx_load(*args, **kwargs) as mod:
        return mod


def prun(
    *popenargs, 
    input: Optional[bytes] = None, 
    capture_output: bool = False, 
    timeout: Union[None, int, float] = None, 
    check: bool = False, 
    continue_with_exceptions: Union[type[BaseException], tuple[type[BaseException], ...]] = (),
    **kwargs,
) -> CompletedProcess:
    if input is not None:
        if kwargs.get("stdin") is not None:
            raise ValueError("stdin and input arguments may not both be used.")
        kwargs["stdin"] = PIPE

    if capture_output:
        if kwargs.get("stdout") is not None or kwargs.get("stderr") is not None:
            raise ValueError("stdout and stderr arguments may not be used "
                             "with capture_output.")
        kwargs["stdout"] = PIPE
        kwargs["stderr"] = PIPE

    with Popen(*popenargs, **kwargs) as process:
        while True:
            try:
                stdout, stderr = process.communicate(input, timeout=timeout)
                break
            except continue_with_exceptions:
                continue
            except TimeoutExpired as exc:
                process.kill()
                if subprocess._mswindows: # type: ignore
                    # Windows accumulates the output in a single blocking
                    # read() call run on child threads, with the timeout
                    # being done in a join() on those threads.  communicate()
                    # _after_ kill() is required to collect that and add it
                    # to the exception.
                    exc.stdout, exc.stderr = process.communicate()
                else:
                    # POSIX _communicate already populated the output so
                    # far into the TimeoutExpired exception.
                    process.wait()
                raise
            except:  # Including KeyboardInterrupt, communicate handled that.
                process.kill()
                # We don"t call process.wait() as .__exit__ does that for us.
                raise
        retcode: int = process.poll() or 0
        if check and retcode:
            raise CalledProcessError(
                retcode, process.args, output=stdout, stderr=stderr)

    return CompletedProcess(process.args, retcode, stdout, stderr)

prun.__doc__ = subprocess.run.__doc__


def prun_module(
    module: Optional[str] = None, 
    args: Sequence[str] = (), 
    executable: str = executable, 
    continue_with_exceptions: Union[type[BaseException], tuple[type[BaseException], ...]] = KeyboardInterrupt, 
    shell: bool = _PLATFORM_IS_WINDOWS, 
    **prun_kwargs, 
) -> CompletedProcess:
    pargs = [executable]
    "Run a module as a script by `prun` function."
    if module:
        args = [executable, "-m", module, *args]
    else:
        args = [executable, *args]
    return prun(
        args, 
        continue_with_exceptions=continue_with_exceptions, 
        shell=shell, 
        **prun_kwargs, 
    )


def pid_exists(pid: int) -> bool:
    """Check whether pid exists in the current process table.

    NOTE: A more reliable approach is to use `psutil <https://pypi.org/project/psutil/>`
        def pid_exists(pid: int) -> bool:
            try:
                psutil.Process(pid)
                return True
            except psutil.NoSuchProcess:
                return False
    """
    if pid < 0:
        return False
    if _PLATFORM_IS_WINDOWS:
        try:
            kill(pid, 0)
            return True
        except OSError:
            return False
    else:
        if pid == 0:
            # According to "man 2 kill" PID 0 refers to every process
            # in the process group of the calling process.
            # On certain systems 0 is a valid PID but we have no way
            # to know that in a portable fashion.
            raise ValueError("invalid PID 0")
        try:
            kill(pid, 0)
            return True
        except OSError as err:
            if err.errno == errno.ESRCH:
                # ESRCH == No such process
                return False
            elif err.errno == errno.EPERM:
                # EPERM clearly means there's a process to deny access to
                return True
            else:
                # According to "man 2 kill" possible error values are
                # (EINVAL, EPERM, ESRCH)
                raise


def wait_for_pid_finish(
    pid: int, 
    sleep_interval: Union[int, float] = 0.1, 
):
    "Wait for a process to finish."
    while pid_exists(pid):
        sleep(sleep_interval)

