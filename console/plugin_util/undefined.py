__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)

__all__ = ['UndefinedType', 'undefined']


class UndefinedType:
    'A singleton constant, indicates that no arguments were passed in.'
    __slots__ = () # instance has no property `__dict__`
    __instance__ = None

    def __new__(cls, /):
        if cls.__instance__ is None:
            cls.__instance__ = object.__new__(cls)
        return cls.__instance__

    __repr__ = staticmethod(lambda: 'undefined') # type: ignore # staticmethod for speed up
    __bool__ = staticmethod(lambda: False)


undefined = UndefinedType()

