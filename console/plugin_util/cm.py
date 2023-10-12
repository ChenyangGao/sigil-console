__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncContextManager, ContextManager

from .undefined import undefined 


__all__ = ['cm', 'acm', 'ensure_cm', 'ensure_acm']


@contextmanager
def cm(yield_=None, /):
    'A context manager'
    yield yield_


@asynccontextmanager
async def acm(yield_=None, /):
    'A asynchronous context manager'
    yield yield_


def ensure_cm(
    obj, /, default=undefined
) -> ContextManager:
    for C in type(obj).__mro__:
        if '__enter__' in C.__dict__:
            return obj
    if default is undefined:
        default = obj
    return cm(default)


def ensure_acm(
    obj, /, default=undefined
) -> AsyncContextManager:
    for C in type(obj).__mro__:
        if '__aenter__' in C.__dict__:
            return obj
    if default is undefined:
        default = obj
    return acm(default)

