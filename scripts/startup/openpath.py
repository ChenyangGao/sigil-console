#!/usr/bin/env python
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)
__all__ = ['openpath', 'open_bookpath', 'open_id', 'open_href', 'open_outdir']

from os import remove, PathLike
from os.path import join, sep
from shutil import copytree
from typing import Union


bc = bc # type: ignore
PathType = Union[str, PathLike]

if __import__('os').path is __import__('posixpath'):
    _to_syspath = lambda s: s
else:
    _to_syspath = lambda s: s.replace('/', sep)


try:
    def openpath(
        path: PathType, 
        _func=__import__('os').startfile, 
    ) -> None:
        'Open a file or directory (For Windows)'
        _func(path)
except AttributeError:
    _PLATFROM_SYSTEM = __import__('platform').system()
    if _PLATFROM_SYSTEM == 'Linux':
        def openpath(
            path: PathType, 
            _func=__import__('subprocess').Popen, 
        ) -> None:
            'Open a file or directory (For Linux)'
            _func(['xdg-open', path])
    elif _PLATFROM_SYSTEM == 'Darwin':
        def openpath(
            path: PathType, 
            _func=__import__('subprocess').Popen, 
        ) -> None:
            'Open a file or directory (For Mac OS X)'
            _func(['open', path])
    else:
        def openpath(path: PathType, _func=None) -> None:
            'Issue an error: can not open the path.'
            raise NotImplementedError("Can't open the path %r" % path)
    del _PLATFROM_SYSTEM


def open_bookpath(bookpath: PathType) -> None:
    syspath = join(_OUTDIR, _to_syspath(bookpath))
    openpath(syspath)
open_bookpath.__doc__ = '根据传入的相对路径，打开在目录 {_OUTDIR!r} 中对应文件'


def open_id(id: str, /) -> None:
    '根据文件在 epub 的 OPF 文件中的 id，打开对应文件'
    bookpath = bc.id_to_bookpath(id)
    if bookpath is None:
        raise FileNotFoundError(
            f'Id {id!r} does not exist in manifest')
    open_bookpath(bookpath)


def open_href(href: str, /) -> None:
    '根据文件在 epub 的 OPF 文件中的 href，打开对应文件'
    id = bc.href_to_id(href)
    if id is None:
        raise FileNotFoundError(
            f'Href {href!r} does not exist in manifest')
    open_id(id)


def open_outdir() -> None:
    '打开插件运行时输出文件的临时目录'
    openpath(_OUTDIR)


def remove_path(path: PathType) -> bool:
    try:
        remove(path)
        return True
    except FileNotFoundError:
        return False


def deletefile(self, id):
    bookpath = bc.id_to_bookpath(id)
    self._w.deletefile(id)
    remove_path(join(_OUTDIR, _to_syspath(bookpath)))
deletefile.__doc__ = type(bc).deletefile.__doc__ # type: ignore
type(bc).deletefile = deletefile # type: ignore


_OUTDIR = bc._w.outdir # type: ignore
copytree(bc._w.ebook_root, _OUTDIR, dirs_exist_ok=True) # type: ignore
open_outdir()
print('Opened outdir:', _OUTDIR)

