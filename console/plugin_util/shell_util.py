#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)
__all__ = [
    'winsh_quote', 'winsh_join', 'exists_execfile', 'list_debian_apps', 
    'get_debian_default_app', 'set_debian_default_app', 
]


from subprocess import run as sprun, DEVNULL, PIPE
from typing import List, Optional, Sequence


def winsh_quote(part, _cre=__import__('re').compile(r'\s')):
    'Return a shell-escaped string.'
    part = part.strip().replace(r'"', r'\"')
    if _cre.search(part) is not None:
        part = r'"%s"' % part
    return part


def winsh_join(split_command: Sequence[str]) -> str:
    'Return a shell-escaped string from *split_command*.'
    return ' '.join(map(winsh_quote, split_command))


def exists_execfile(file: str) -> bool:
    'Check whether the executable file exists in a directory in $PATH.'
    return sprun(
        ['which', file], stdout=DEVNULL, stderr=DEVNULL
    ).returncode == 0


def list_debian_apps(field: str) -> Optional[List[str]]:
    'Use `update-alternatives` command to list apps of the field.'
    ret = sprun(
        ['update-alternatives', '--list', field], stdout=PIPE)
    if ret.returncode != 0:
        return None
    return ret.stdout.rstrip(b'\n').decode().split('\n')


def get_debian_default_app(field: str) -> Optional[str]:
    'Use `update-alternatives` command to get default app of the field.'
    f: bytes = field.encode()
    ret = sprun(
        'update-alternatives --get-selections', 
        shell=True, stdout=PIPE)
    if ret.returncode != 0:
        return None
    rows = (row.split(maxsplit=3) 
        for row in ret.stdout.rstrip(b'\n').split(b'\n'))
    return next(
        (r[2].decode() for r in rows if r[0] == f), None)


def set_debian_default_app(field: str, value: Optional[str] = None) -> None:
    'Use `update-alternatives` command to set default app of the field.'
    if value is None:
        cmd = ['sudo', 'update-alternatives', '--config', field]
    else:
        cmd = ['sudo', 'update-alternatives', '--set', field, value]
    sprun(cmd, check=True)

