__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)

from functools import partial

from .undefined import undefined


__all__ = ['ppartial']


class ppartial(partial):

    def __call__(self, /, *args, **kwargs):
        a, k = self.args, self.keywords
        k.update(kwargs)
        if undefined in a:
            a1, a2 = iter(a), iter(args)
            a = (*(next(a2, v) if v is undefined else v for v in a1), 
                 *a1, *a2)
        else:
            a += args
        if undefined in a or undefined in k.values():
            return type(self)(self.func, *a, **k)
        return self.func(*a, **k)

