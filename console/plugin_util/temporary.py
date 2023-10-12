#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 4)

import os, sys

from contextlib import contextmanager
from copy import copy as _copy, deepcopy as _deepcopy
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import cast, Callable, Dict, List, Optional, Tuple, Union
from types import ModuleType

from .undefined import undefined


__all__ = ['temp_dict', 'temp_list', 'temp_set', 'temp_wdir', 'temp_namespace', 
           'temp_namespace_call', 'temp_attr', 'temp_wdir', 'temp_sys_path', 
           'temp_sys_modules', 'temp_dir', 'temp_file']


_PREFIXES: Tuple[str, ...]
try:
    _PREFIXES = tuple(__import__('site').PREFIXES)
except (ImportError, AttributeError):
    from sys import prefix, exec_prefix
    _PREFIXES = (prefix, exec_prefix)

PathType = Union[str, bytes, os.PathLike]


@contextmanager
def temp_dict(container: dict, /, copy=False, deepcopy=False):
    cp = cast(Callable, _deepcopy if deepcopy else _copy)
    if copy:
        container = cp(container)
    else:
        orig_container = cp(container)
    try:
        yield container
    finally:
        if not copy:
            container.clear()
            container.update(orig_container)


@contextmanager
def temp_list(container: list, /, copy=False, deepcopy=False):
    cp = cast(Callable, _deepcopy if deepcopy else _copy)
    if copy:
        container = cp(container)
    else:
        orig_container = cp(container)
    try:
        yield container
    finally:
        if not copy:
            container[:] = orig_container


@contextmanager
def temp_set(container: set, /, copy=False, deepcopy=False):
    cp = cast(Callable, _deepcopy if deepcopy else _copy)
    if copy:
        container = cp(container)
    else:
        orig_container = cp(container)
    try:
        yield container
    finally:
        if not copy:
            container.clear()
            container.update(orig_container)


@contextmanager
def temp_namespace(ns=None, /, *ns_extras, **ns_extra):
    if ns is None:
        sys._getframe(2).f_globals
    with temp_dict(ns) as g:
        if ns_extras:
            for ext in ns_extras:
                g.update(ext)
        if ns_extra:
            g.update(ns_extra)
        yield g


@contextmanager
def temp_namespace_call(ns=None, /, *names, **ns_extra):
    if ns is None:
        sys._getframe(2).f_globals
    with temp_namespace(ns, **ns_extra) as g:
        yield g
        excs = []
        for i, name in enumerate(names):
            try:
                g[name]()
            except BaseException as exc:
                excs.append((i, name, exc))
        if excs:
            raise Exception(excs)


@contextmanager
def temp_attr(obj, attr, value=undefined):
    old_attr = getattr(obj, attr, undefined)
    if value is undefined:
        if old_attr is not undefined:
            try:
                new_attr = _deepcopy(old_attr)
            except TypeError:
                new_attr = _copy(old_attr)
            setattr(obj, attr, new_attr)
    else:
        setattr(obj, attr, value)
    try:
        yield
    finally:
        if old_attr is undefined:
            if hasattr(obj, attr):
                delattr(obj, attr)
        elif getattr(obj, attr, undefined) is not old_attr:
            setattr(obj, attr, old_attr)


@contextmanager
def temp_wdir(wdir: Optional[PathType] = None):
    'Temporary working directory'
    original_wdir: PathType = os.getcwd()
    try:
        if wdir:
            os.chdir(wdir)
        yield
    finally:
        os.chdir(original_wdir)


@contextmanager
def temp_sys_path():
    'Temporary sys.path'
    yield from temp_list.__wrapped__(sys.path)


@contextmanager
def temp_sys_modules(
    mdir: Optional[PathType] = None, 
    clean: bool = True, 
    restore: bool = True, 
    prefixes_not_clean: Tuple[str, ...] = _PREFIXES, 
):
    'Temporary sys.modules'
    sys_modules: Dict[str, ModuleType] = sys.modules
    original_sys_modules: Dict[str, ModuleType] = sys_modules.copy()
    if clean:
        # Only retaining built-in modules and standard libraries and site-packages modules 
        # (`prefixes_not_clean` as the path prefix), 
        # but ignoring namespace packages (the documentation is as follows)
        # [Packaging namespace packages](https://packaging.python.org/guides/packaging-namespace-packages/)
        sys_modules.clear()
        sys_modules.update(
            (k, m) for k, m in original_sys_modules.items() 
            if not hasattr(m, '__file__') # It means a built-in module
                or m.__file__ is not None # It means not a namespace package
                and m.__file__.startswith(prefixes_not_clean) # It means a standard library or site-packages module
        )

    sys_path: List[str]
    with temp_sys_path() as sys_path:
        if mdir is not None:
            mdir_: str = mdir.decode() if isinstance(mdir, bytes) else str(mdir)
            sys_path.insert(0, mdir_)
        try:
            yield sys_modules
        finally:
            if restore:
                sys_modules.clear()
                sys_modules.update(original_sys_modules)


@contextmanager
def temp_dir(path: Optional[PathType] = None):
    if path is not None:
        os.makedirs(path)
        try:
            yield path
        finally:
            try:
                os.removedirs(path)
            except FileNotFoundError:
                pass
    else:
        with TemporaryDirectory() as d:
            yield d


@contextmanager
def temp_file(path: Optional[PathType] = None):
    if path is not None:
        open(path, 'x+b')
        try:
            yield path
        finally:
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
    else:
        with NamedTemporaryFile() as f:
            yield f.name

