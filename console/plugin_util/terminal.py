#!/usr/bin/env python3
# coding: utf-8

# Reference:
#   - https://developer.apple.com/library/archive/documentation/AppleScript/Conceptual/AppleScriptLangGuide/introduction/ASLR_intro.html
#   - https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/
#   - https://en.wikibooks.org/wiki/AppleScript_Programming
#   - https://linux.die.net/man/8/update-alternatives

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 6)

import os
import socket

from contextlib import contextmanager
from json import dump as json_dump, load as json_load
from multiprocessing.connection import Client, Listener
from os import getcwd, getpid, remove, path as _path
from shlex import join as shlex_join, split as shlex_split
from subprocess import run as sprun, CompletedProcess
from tempfile import NamedTemporaryFile
from typing import (
    cast, Dict, Final, List, Optional, Sequence, Tuple, Union
)
from uuid import uuid4

from .cm import ensure_cm
from .shell_util import exists_execfile
from .run import wait_for_pid_finish
from .decorator import as_thread, suppressed, expand_by_args
from .shell_util import winsh_join, winsh_quote
from .timeout import ThreadingTimeout


__all__ = [
    'start_terminal', 'start_windows_terminal', 'start_linux_terminal', 
    'start_macosx_terminal', 'open_macosx_terminal', 
]


_CURDIR: Final[str] = getcwd()
_ENV_WAIT_SERFILE = _path.join(_CURDIR, '.env_wait_pid.json')
_PLATFORM = __import__('platform').system()


def _remove_file(path: Union[bytes, str]) -> bool:
    try:
        remove(path)
        return True
    except OSError:
        return False


@expand_by_args
def _wait_child_process(*args, **kwds):
    raise NotImplementedError


@_wait_child_process.register('tcpsock')
@contextmanager
def _waitcp_tcpsock(
    address=None, 
    timeout: Union[int, float] = 10, 
    port_start: int = 10000, 
):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)

    if address is None:
        for port in range(port_start, 65536):
            address = ('', port)
            try:
                server.bind(address)
                break
            except OSError:
                pass
        else:
            raise OSError('cannot bind port %d-65535' % port_start)
    else:
        server.bind(address)

    server.settimeout(timeout)

    @as_thread
    def wait():
        pid: int = 0
        with server:
            server.listen(1)
            client, _ = server.accept()
            with client:
                pid = int(client.recv(1024)) 
        if pid:
            wait_for_pid_finish(pid)

    future = wait()
    yield address
    future.thread.join()


@_wait_child_process.register('unixsock')
@contextmanager
def _waitcp_unixsock(
    address=None, 
    timeout: Union[int, float] = 10, 
):
    if address is None:
        address = _path.abspath('.%s.sock' % uuid4())
    else:
        _remove_file(address)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(address)
    server.settimeout(timeout)

    @as_thread
    def wait():
        pid: int = 0
        with server:
            server.listen(1)
            client, _ = server.accept()
            with client:
                pid = int(client.recv(1024))
        if pid:
            wait_for_pid_finish(pid)

    future = wait()
    try:
        yield address
        future.thread.join()
    finally:
        _remove_file(address)


@_wait_child_process.register('namedpipe')
@contextmanager
def _waitcp_namedpipe(
    address=None, 
    timeout: Union[int, float] = 10, 
):
    if address is None:
        address = _path.abspath('.%s.pipe' % uuid4())
    else:
        _remove_file(address)

    # TODO: support Windows namedpipe
    os.mkfifo(address)

    @as_thread
    def wait():
        pid: int = 0
        with ThreadingTimeout(timeout):
            with open(address, 'rb') as f:
                pid = int(f.read())
        if pid:
            wait_for_pid_finish(pid)

    future = wait()
    try:
        yield address
        future.thread.join()
    finally:
        _remove_file(address)


# NOTE: Reference
# https://docs.python.org/3/library/multiprocessing.html#module-multiprocessing.connection
@_wait_child_process.register('listener')
@contextmanager
def _waitcp_listener(
    address=None, 
    timeout: Union[int, float] = 10, 
    port_start: int = 10000, 
):
    if address is None:
        try:
            address = _path.abspath('.%s.pipe' % uuid4())
            server = Listener(address, authkey=b'injectedConsole')
        except OSError:
            for port in range(port_start, 65536):
                address = ('', port)
                try:
                    server = Listener(address, authkey=b'injectedConsole')
                    break
                except OSError:
                    pass
            else:
                raise OSError('cannot bind port %d-65535' % port_start)
    else:
        _remove_file(address)

    @as_thread
    def wait():
        pid: int = 0
        with ThreadingTimeout(timeout):
            client = server.accept()
            pid = client.recv()

        if pid:
            wait_for_pid_finish(pid)

    future = wait()
    try:
        yield address
        future.thread.join()
    finally:
        _remove_file(address)


@contextmanager
def _wait_for_client(
    server_type: str = 'listener', 
    timeout: Union[int, float] = 10, 
):
    try:
        with _wait_child_process(server_type, timeout=timeout) as address:
            json_dump(
                {'type': server_type, 'address': address}, 
                open(_ENV_WAIT_SERFILE, 'w')
            )
            yield
    finally:
        _remove_file(_ENV_WAIT_SERFILE)


@suppressed
def _send_pid_to_server(env=None):
    if env is None:
        env = json_load(open(_ENV_WAIT_SERFILE, 'r'))

    server_type, address = env['type'], env['address']
    if server_type == 'tcpsock':
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(address)
        with client:
            client.send(str(getpid()).encode('latin-1'))
    elif server_type == 'unixsock':
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(address)
        with client:
            client.send(str(getpid()).encode('latin-1'))
    elif server_type == 'namedpipe':
        client = open(address, 'wb')
        with client:
            client.write(str(getpid()).encode('latin-1'))
    elif server_type == 'listener':
        client = Client(address, authkey=b'injectedConsole')
        with client:
            client.send(getpid())
    else:
        raise NotImplementedError(server_type)


def start_terminal(cmd, **kwargs) -> CompletedProcess:
    'Start a terminal emulator in current OS platform.'
    if _PLATFORM == 'Windows':
        return start_windows_terminal(cmd, **kwargs)
    elif _PLATFORM == 'Darwin':
        return start_macosx_terminal(cmd, **kwargs)
    elif _PLATFORM == 'Linux':
        return start_linux_terminal(cmd, **kwargs)
    else:
        raise NotImplementedError(
            'start terminal of other system %r is unavailable' % _PLATFORM)


def start_windows_terminal(
    cmd: Union[str, Sequence[str]], 
    app: str = 'powershell',
    app_args: Union[None, str, Sequence[str]] = None, 
    wait: bool = True,
    with_tempfile: bool = False,
    tempfile_suffix: str = '.cmd',
) -> CompletedProcess:
    'Start a terminal emulator in Windows.'
    split_command: List[str] = ['start']
    if wait:
        split_command.append('/wait')
    if app:
        split_command.append(app)
        if app_args is None:
            if app in ('cmd', 'cmd.exe'):
                split_command.append('/c')
        elif isinstance(app_args, str):
            split_command.extend(shlex_split(app_args, posix=False))
        else:
            split_command.extend(app_args)
    if with_tempfile:
        # In Windows, file is occupied when is opening, until it is closed.
        # Like lock, anyone cannot open the file while it is occupied.
        # So we should close it first, then give it to any other, and finally delete it.
        f = NamedTemporaryFile(suffix=tempfile_suffix, mode='w', delete=False)
        try:
            with f:
                if not isinstance(cmd, str):
                    cmd = cast(str, winsh_join(cmd))
                f.write(cmd)
            if app in ('powershell', 'powershell.exe'):
                # Reference::
                # [The call operator &](https://ss64.com/ps/call.html)
                split_command.append('&' + winsh_quote(f.name))
            else:
                split_command.append(winsh_quote(f.name))
            return sprun(split_command, check=True, shell=True)
        finally:
            # TODO: We may need to wait until the file is no longer 
            #       occupied before deleting it.
            _remove_file(f.name)
    if isinstance(cmd, str):
        if app in ('powershell', 'powershell.exe') and cmd.strip():
            split_command.append('&')
        return sprun(
            winsh_join(split_command) + ' ' + cmd, 
            check=True, shell=True)
    else:
        if cmd:
            if app in ('powershell', 'powershell.exe'):
                split_command.append('& ' + winsh_quote(cmd[0]))
                split_command.extend(cmd[1:])
            else:
                split_command.extend(cmd)
        return sprun(split_command, check=True, shell=True)


def start_linux_terminal(
    cmd: Union[str, Sequence[str]], 
    app: Optional[str] = None, 
    app_args: Union[None, str, Sequence[str]] = None, 
    wait: bool = True, 
    with_tempfile: bool = False, 
    tempfile_suffix: str = '.sh', 
    shebang: str = '#!/bin/sh', 
) -> CompletedProcess:
    'Start a terminal emulator in Linux.'
    terminal_apps: Tuple[str, ...] = (
        'gnome-terminal',      # GNOME
        'konsole',             # KDE
        'xfce4-terminal',      # XFCE
        'lxterminal',          # LXDE
        # Other popular terminal emulators
        'terminator', 'rxvt', 'xterm', 
    )

    terminal_app_execute_args: Dict[str, List[str]] = {
        # https://linuxcommandlibrary.com/man/gnome-terminal
        'gnome-terminal': ['--'], 
        # https://linuxcommandlibrary.com/man/konsole
        'konsole': ['-e'], 
        # https://linuxcommandlibrary.com/man/xfce4-terminal
        'xfce4-terminal': ['-x'], 
        # https://linuxcommandlibrary.com/man/lxterminal
        'lxterminal': ['-e'], 
        # https://linux.die.net/man/1/terminator
        'terminator': ['-x'], 
        # https://linux.die.net/man/1/rxvt
        'rxvt': ['-e'], 
        # https://linux.die.net/man/1/xterm
        'xterm': ['-e']
    }

    split_command: List[str] = []
    if app is None:
        # Debian Series
        # https://helpmanual.io/man1/x-terminal-emulator/
        if exists_execfile('x-terminal-emulator'):
            from .shell_util import get_debian_default_app
            app = get_debian_default_app('x-terminal-emulator')
        else:
            for app in terminal_apps:
                if exists_execfile(app):
                    break
            else:
                raise NotImplementedError('Failed to detect the terminal app, '
                                          'please specify one')
    if app:
        split_command.append(app)
        if app_args is None:
            app_name = app.rsplit('/', 1)[-1]
            split_command.extend(terminal_app_execute_args.get(app_name, []))
        elif isinstance(app_args, str):
            split_command.extend(shlex_split(app_args))
        else:
            split_command.extend(app_args)
    with ensure_cm(_wait_for_client() if wait else None):
        if with_tempfile:
            with NamedTemporaryFile(suffix=tempfile_suffix, mode='w') as f:
                sprun(['chmod', '+x', f.name], check=True)
                if not isinstance(cmd, str):
                    cmd = cast(str, shlex_join(cmd))
                f.write('%s\n%s\n' % (shebang, cmd))
                f.flush()
                split_command.append(f.name)
                return sprun(split_command, check=True)
        if isinstance(cmd, str):
            return sprun(shlex_join(split_command) + ' ' + cmd, 
                         check=True, shell=True)
        else:
            split_command.extend(cmd)
            return sprun(split_command, check=True)


def _run_osascript(script: str, /, *args: str, **kwds):
    return sprun(['osascript', '-e', script, *args], **kwds)


def start_macosx_terminal(
    cmd: Union[str, Sequence[str]], 
    app: str = 'Terminal.app', 
    app_args: Union[None, str, Sequence[str]] = None, 
    wait: bool = True, 
    wait_command: str = '''\
    repeat while w exists
        delay 0.1
    end repeat''', 
    with_tempfile: bool = False, 
    tempfile_suffix: str = '.command', 
    shebang: str = '#!/bin/sh', 
) -> CompletedProcess:
    'Start a terminal emulator in MacOSX.'
    if not isinstance(cmd, str):
        cmd = cast(str, shlex_join(cmd))
    if app_args is None:
        if app in ('Terminal.app', 'Terminal', 'terminal'):
            app_args = 'do script'
        elif app in ('iTerm.app', 'iTerm', 'iterm'):
            # NOTE: See: https://iterm2.com/documentation-scripting.html
            app_args = 'create window with default profile command'
    elif not isinstance(app_args, str):
        app_args = shlex_join(app_args)
    app_args = cast(str, app_args)
    if wait:
        tpl_command = '''\
tell application "{app}"
    activate
    set w to ({app_args} "{command}")
    %s
end tell''' % wait_command
    else:
        tpl_command = '''\
tell application "{app}"
    activate
    ({app_args} "{command}")
end tell'''
    if with_tempfile:
        with NamedTemporaryFile(suffix=tempfile_suffix, mode='w') as f:
            sprun(['chmod', '+x', f.name], check=True)
            f.write('%s\n%s\n' % (shebang, cmd))
            f.flush()
            return _run_osascript(tpl_command.format(
                app=app.replace('"', r'\"'), 
                app_args=app_args, 
                command=f.name.replace('"', r'\"'), 
            ), check=True)
    else:
        return _run_osascript(tpl_command.format(
            app=app.replace('"', r'\"'), 
            app_args=app_args, 
            command=cmd.replace('"', r'\"'), 
        ), check=True)


def open_macosx_terminal(
    cmd: Union[str, Sequence[str]], 
    app: str = 'Terminal.app', 
    app_args: Union[None, str, Sequence[str]] = None, 
    wait: bool = True, 
    with_tempfile: bool = True, 
    tempfile_suffix: str = '.command', 
    shebang: str = '#!/bin/sh', 
) -> CompletedProcess:
    'Start a terminal emulator in MacOSX.'
    split_command: List[str] = ['open']
    if app:
        split_command.append('-a')
        split_command.append(app)
        if app_args is None:
            split_command.append('-n')
        elif isinstance(app_args, str):
            split_command.extend(shlex_split(app_args))
        else:
            split_command.extend(app_args)
    if wait:
        if '-W' not in split_command or '--wait-apps' not in split_command:
            split_command.append('-W')
    if '--args' not in split_command:
        split_command.append('--args')
    if with_tempfile:
        with NamedTemporaryFile(suffix=tempfile_suffix, mode='w') as f:
            sprun(['chmod', '+x', f.name], check=True)
            if not isinstance(cmd, str):
                cmd = cast(str, shlex_join(cmd))
            f.write('%s\n%s\n' % (shebang, cmd))
            f.flush()
            split_command.append(f.name)
            return sprun(split_command, check=True)
    else:
        if isinstance(cmd, str):
            return sprun(shlex_join(split_command) + ' ' + cmd, 
                         check=True, shell=True)
        else:
            split_command.extend(cmd)
            return sprun(split_command, check=True)


if __name__ == '__main__':
    from sys import executable, argv
    argv = argv[1:]
    if argv:
        start_terminal(argv)
    else:
        start_terminal(executable)

