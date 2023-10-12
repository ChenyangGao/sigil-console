__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)
__all__ = ['AggregationException', 'retry_sync', 'retry_async', 'retry']

from inspect import iscoroutinefunction
from itertools import chain
from typing import (
    cast, Callable, List, Optional, Tuple, Type, Union
)

from .decorator import optional_decorate


class AggregationException(Exception):

    def __init__(self, *args, exceptions=(), **kwds):
        super().__init__(*args)
        self.exceptions = exceptions
        self.kwds = kwds

    def __str__(self) -> str:
        return ', '.join(chain(
            (f'{arg}' for arg in self.args), 
            (f'{k}={v!r}' for k, v in self.kwds.items()),
            (f'exceptions={self.exceptions!r}',),
        ))

    def __repr__(self) -> str:
        return f'{type(self).__name__}({self!s})'


@optional_decorate
def retry_sync(
    f: Optional[Callable] = None, 
    /, 
    times: int = 5, 
    exceptions: Union[Type[BaseException], Tuple[Type[BaseException], ...]] = Exception, 
) -> Callable:
    if times < 1:
        raise ValueError('`times` must be >= 1')
    def wrapper(*args, **kwargs):
        excs: List[BaseException] = []
        prev_exc = None
        for _ in range(times):
            try:
                return f(*args, **kwargs)
            except exceptions as exc:
                exc.__prev__ = prev_exc
                prev_exc = exc
                excs.append(exc)
            except BaseException as exc:
                exc.__prev__ = prev_exc
                raise exc
        raise AggregationException(args=args, kwargs=kwargs, exceptions=excs)
    return wrapper


@optional_decorate
def retry_async(
    f: Optional[Callable] = None, 
    /, 
    times: int = 5, 
    exceptions: Union[Type[BaseException], Tuple[Type[BaseException], ...]] = Exception, 
) -> Callable:
    if times < 1:
        raise ValueError('`times` must be >= 1')
    async def wrapper(*args, **kwargs):
        excs: List[BaseException] = []
        prev_exc = None
        for _ in range(times):
            try:
                return await f(*args, **kwargs)
            except exceptions as exc:
                exc.__prev__ = prev_exc
                prev_exc = exc
                excs.append(exc)
            except BaseException as exc:
                exc.__prev__ = prev_exc
                raise exc
        raise AggregationException(args=args, kwargs=kwargs, exceptions=excs)
    return wrapper


@optional_decorate
def retry(
    f: Optional[Callable] = None, 
    /, 
    times: int = 5, 
    exceptions: Union[Type[BaseException], Tuple[Type[BaseException], ...]] = Exception, 
    async_: Optional[bool] = None, 
) -> Callable:
    f = cast(Callable, f)
    if async_ or (async_ is None and iscoroutinefunction(f)):
        return retry_async(
            f, times=times, exceptions=exceptions)
    else:
        return retry_sync(
            f, times=times, exceptions=exceptions)

