#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)

from collections.abc import Mapping, MutableMapping


__all__ = ['DictAttr', 'MutableDictAttr']


class DictAttr(Mapping):
    """Implements the Mapping protocol 
    for redirecting objects's __dict__."""
    def __init__(self, *args, **kwargs):
        for arg in args:
            self.__dict__.update(arg)
        if kwargs:
            self.__dict__.update(kwargs)

    def __repr__(self):
        return '%s(%r)' % (type(self).__qualname__, self.__dict__)

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setattr__(self, attr, val):
        raise AttributeError('cannot set attribute')

    def __delattr__(self, attr):
        raise AttributeError('cannot delete attribute')


class MutableDictAttr(DictAttr, MutableMapping):
    """Implements the MutableMapping protocol 
    for redirecting objects's __dict__."""

    def __getattr__(self, attr):
        return getattr(self.__dict__, attr)

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __delitem__(self, key):
        del self.__dict__[key]

    def __setattr__(self, attr, val):
        self[attr] = val

    def __delattr__(self, key):
        del self[key]

