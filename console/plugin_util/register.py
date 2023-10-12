#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 1)
__all__ = ["bind_function_registry"]

from functools import partial
from operator import attrgetter
from typing import Callable, MutableMapping, Optional, TypeVar


K = TypeVar("K")


def bind_function_registry(
    m: MutableMapping[K, Callable], 
    /, 
    default_key_func: Callable[[Callable], K] = attrgetter("__name__"), 
) -> Callable:
    """
    """
    def register(
        func_or_key: K | Callable, 
        /, 
        key: Optional[K] = None, 
    ):
        if not callable(func_or_key):
            return partial(register, key=func_or_key)
        if key is None:
            key = default_key_func(func_or_key)
        m[key] = func_or_key
        return func_or_key
    return register

