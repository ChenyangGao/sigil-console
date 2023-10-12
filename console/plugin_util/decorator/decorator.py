__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 3)
__all__ = [
    'decorated', 'partial_decorated', 'pipe', 'compose', 'optional_kwargs', 
    'optional', 'optional_decorate', 'optional_partial', 'currying', 
    'partialize', 
]

from functools import partial, reduce, update_wrapper
from inspect import signature
from typing import Any, Callable, Optional, TypeVar, Union

from ..partial import ppartial
from ..undefined import undefined


T = TypeVar('T')


def decorated(
    f: Callable[..., T], 
    g: Optional[Callable] = None, 
    /, 
) -> Callable[[Callable], Union[Callable, T]]:
    if g is None:
        return partial(decorated, f)
    return update_wrapper(lambda *a, **k: f(g, *a, **k), g)


def partial_decorated(
    f: Callable[..., T], 
    g: Optional[Callable] = None, 
    /, 
) -> Callable[[Callable], Union[Callable, T]]:
    if g is None:
        return partial(partial_decorated, f)
    return partial(f, g)


def pipe(
    *decorators: Callable[[Callable], Callable]
) -> Callable:
    return decorated(
        lambda f, /, *args, **kwds: 
        reduce(
            lambda f, g: g(f), 
            decorators, 
            f(*args, **kwds),
        ),
    )


def compose(
    *decorators: Callable[[Callable], Callable]
) -> Callable:
    return pipe(*reversed(decorators))


@decorated
def optional_kwargs(
    f: Callable[..., Callable], 
    g: Optional[Callable] = None, 
    /, 
    **kwds, 
) -> Callable:
    return  f(**kwds) if g is None else f(**kwds)(g)


@decorated
def optional(
    f: Callable[..., Callable], 
    g: Optional[Callable] = None, 
    /, 
    *args, 
    **kwds, 
) -> Callable:
    if g is None:
        return f(*args, **kwds)
    elif callable(g):
        return f(*args, **kwds)(g)
    return f(g, *args, **kwds)


def optional_decorate(
    f: Callable, 
    g: Optional[Callable] = None, 
    /, 
    *args,
    **kwds,
) -> Callable:
    if g is None:
        return ppartial(f, undefined, *args, **kwds)
    return update_wrapper(f(g, *args, **kwds), g)


def optional_partial(
    f: Callable, 
    g: Optional[Callable] = None, 
    /, 
    **kwds, 
) -> Callable:
    if g is None:
        return partial(optional_partial, f, **kwds)
    return partial(f, g, **kwds)


def currying(
    f: Callable[..., T], /
) -> Callable[..., Union[Callable, T]]:
    bind = signature(f).bind
    def wrapper(*args, **kwargs):
        try:
            bind(*args, **kwargs)
        except TypeError as exc:
            if (exc.args 
                and isinstance(exc.args[0], str)
                and exc.args[0].startswith('missing a required argument:')
            ):
                return partial(wrapper, *args, **kwargs)
            raise
        else:
            return f(*args, **kwargs)
    return update_wrapper(wrapper, f)


def partialize(
    f: Optional[Callable[..., T]] = None, 
    /, 
    sentinel: Any = undefined, 
) -> Callable[..., Union[Callable, T]]:
    if f is None:
        return partial(partialize, sentinel=sentinel)
    bind = signature(f).bind
    def wrap(_paix, _pargs, _kargs, /):
        def wrapper(*args, **kwargs):
            pargs = _pargs.copy()
            j = len(pargs)
            for i, e in zip(_paix, args[j:]):
                pargs[i] = e
                j += 1
            pargs.extend(args[j:])
            try:
                bound = bind(*pargs, **kwargs)
            except TypeError as exc:
                if (exc.args 
                    and isinstance(exc.args[0], str)
                    and exc.args[0].startswith('missing a required argument:')
                ):
                    return partial(wrapper, *args, **kwargs)
                raise
            else:
                bound.apply_defaults()
            if sentinel in bound.args or sentinel in bound.kwargs.values():
                return wrap(
                    [i for i, e in enumerate(args) if e is sentinel], 
                    list(args), kwargs)
            return f(*args, **kwargs)
        return partial(update_wrapper(wrapper, f), *_pargs, **_kargs)
    return wrap([], [], {})

