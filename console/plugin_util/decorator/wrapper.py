__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)
__all__ = ['as_thread', 'as_threads', 'timethis', 'with_lock', 
           'context', 'suppressed']

from concurrent.futures import Future
from threading import current_thread, Lock, Thread
from time import perf_counter
from typing import (
    overload, Callable, List, Optional, Type, TypeVar, Tuple, Union
)

from .decorator import optional_decorate


T = TypeVar('T')


@optional_decorate
def as_thread(
    f: Optional[Callable] = None, 
    /, 
    join: bool = False, 
    daemon: bool = True, 
    **kwds, 
) -> Callable[..., Future]:
    def wrapper(*args, **kwargs) -> Future:
        def asfuture():
            try:
                ft.set_result(f(*args, **kwargs))
            except BaseException as exc:
                ft.set_exception(exc)

        ft: Future = Future()
        t = ft.thread = Thread(target=asfuture, daemon=daemon, **kwds) # type: ignore
        t.start()
        if join:
            t.join()
        return ft

    return wrapper


@optional_decorate
def as_threads(
    f: Optional[Callable] = None, 
    /, 
    amount: int = 1, 
    join: bool = False, 
    daemon: bool = True, 
    **kwds, 
) -> Callable[..., List[Future]]:
    def wrapper(*args, **kwargs) -> List[Future]:
        def asfuture():
            ft = Future()
            ft.thread = current_thread()
            futures.append(ft)
            try:
                ft.set_result(f(*args, **kwargs))
            except BaseException as exc:
                ft.set_exception(exc)

        futures: List[Future] = []
        threads = [
            Thread(target=asfuture, daemon=daemon, **kwds)
            for _ in range(amount)
        ]
        for t in threads:
            t.start()
        if join:
            for t in threads:
                t.join()
        return futures

    return wrapper


@optional_decorate
def timethis(
    f: Optional[Callable] = None, 
    /, 
    print: Callable = print, 
) -> Callable:
    def wrapper(*args, **kwargs):
        begin_dt = perf_counter()
        try:
            return f(*args, **kwargs)
        finally:
            cost = perf_counter() - begin_dt
            name = getattr(f, '__qualname__', getattr(f, '__name__', repr(f)))
            args_str = ', '.join(
                (*map(repr, args), 
                *(f'{k}={v!r}' for k, v in kwargs.items()))
            )
            print(f'{name}({args_str}) consumed {cost} seconds')

    return wrapper


@optional_decorate
def with_lock(fn: Callable, /, lock=Lock()) -> Callable:
    def wrapper(*args, **kwds):
        with lock:
            return fn(*args, **kwds)
    return wrapper


@optional_decorate
def context(
    fn: Callable, 
    /, 
    onenter: Optional[Callable] = None,
    onexit: Optional[Callable] = None,
) -> Callable:
    def wrapper(*args, **kwds):
        if onenter:
            onenter()
        try:
            return fn(*args, **kwds)
        finally:
            if onexit: onexit()
    return wrapper


@overload
def suppressed(
    fn: Callable[..., T], 
    /, 
    default: None = ..., 
    exceptions: Union[
        Type[BaseException], 
        Tuple[Type[BaseException], ...]
    ] = ..., 
) -> Callable[..., Optional[T]]:
    ...
@overload
def suppressed(
    fn: Callable[..., T], 
    /, 
    default: T = ..., 
    exceptions: Union[
        Type[BaseException], 
        Tuple[Type[BaseException], ...]
    ] = ..., 
) -> Callable[..., T]:
    ...
@optional_decorate
def suppressed(fn, /, default=None, exceptions=Exception):
    def wrapper(*args, **kwds):
        try:
            return fn(*args, **kwds)
        except exceptions:
            return default
    return wrapper

