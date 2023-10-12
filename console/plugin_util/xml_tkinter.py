#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 3)
__all__ = ['TkinterXMLConfigParser']

# Reference:
#    - [python > docs > tkinter](docs.python.org/3/library/tkinter.html)
#    - [Tk tutorial](https://tk-tutorial.readthedocs.io/en/latest/)
#    - [Tk Docs](https://tkdocs.com/)
#    - [Python - GUI Programming (Tkinter)](https://www.tutorialspoint.com/python/python_gui_programming.htm)
#    - [Python Course - Python Tkinter](https://www.python-course.eu/python_tkinter.php)

import tkinter
from tkinter import ttk

from collections import ChainMap
from copy import copy
from functools import cached_property, partial
from importlib import import_module
from os import PathLike
from re import compile as re_compile, Match, Pattern
from textwrap import dedent
from types import MappingProxyType, ModuleType
from typing import (
    cast, Callable, Container, Dict, Final, Generator, Iterable, 
    List, Mapping, MutableMapping, NamedTuple, Optional, Tuple, Union, 
)
from weakref import WeakValueDictionary

try:
    from lxml.etree import fromstring # type: ignore
except ImportError:
    from xml.etree.ElementTree import fromstring


PathType = Union[bytes, str, PathLike]

TOKEN_SPECIFICATION: Final[List[Tuple[str, str]]] = [
    ('WS',       r'\s+'),
    ('FLOAT',    r'[+-]?[0-9]+\.[0-9]*|\.[0-9]+'),
    ('INT',      r'[+-]?[0-9]+'),
    ('COMMA',    r','),
    ('STRING',   r'\'(?:[^\']|(?<=\\)\')*\'|"(?:[^"]|(?<=\\)")*"'),
    ('NAME',     r'\w+'),
    ('ASSIGN',   r'='),
    ('!EVAL',    r'\(\[(?P<EVAL>.*?\]*)\]\)'),
    ('!EVAL2',   r'\(@(?P<EVAL2>.*?)@\)'),
    ('!EXEC',    r'\(\((?P<EXEC>.*?\)*)\)\)'),
    ('!EXEC2',   r'\(#(?P<EXEC2>.*?)#\)'),
    ('!LAMBDA',  r'\(\{(?P<LAMBDA>.*?\}*)\}\)'),
    ('!LAMBDA2', r'\($(?P<LAMBDA2>.*?)$\)'),
    ('MAYBEARG', r'[^,]+'),
    ('MISMATCH', r'.'),
]


class TokenInfo(NamedTuple):
    group: str
    value: str
    fullvalue: str
    match: Optional[Match]


def make_token_cre(
    token_specification: List[Tuple[str, str]], 
) -> Pattern:
    return re_compile('|'.join(
        pattern if name.startswith('!') else f'(?P<{name}>{pattern})'
        for name, pattern in token_specification
    ))


def tokenize_iter(
    args_str: str, 
    token_cre: Pattern, 
    ignore_groups: Container[str] = (), 
    raise_groups: Container[str] = (), 
) -> Generator[TokenInfo, None, None]:
    # OR you can use token_cre.finditer
    scan = token_cre.scanner(args_str).match # type: ignore
    scaniter: Iterable[Match] = iter(scan, None) 
    curr: Match
    for curr in scaniter:
        group: str = cast(str, curr.lastgroup)
        if group in ignore_groups:
            continue
        if group in raise_groups:
            raise SyntaxError('bad text')
        yield TokenInfo(
            group, 
            curr.groupdict()[group], 
            curr.group(),
            curr,
        )


def tokenize_arg(
    arg_str: str, 
    _token_iter: Callable[[str], Iterable[TokenInfo]] = partial(
        tokenize_iter, 
        token_cre=make_token_cre(TOKEN_SPECIFICATION), 
        ignore_groups=('WS',), 
        raise_groups=('MISMATCH',), 
    ),
) -> TokenInfo:
    tokit = _token_iter(arg_str)
    tok = next(tokit, None) # type: ignore
    if tok is None or tok.group in ('ASSIGN', 'COMMA') \
                   or next(tokit, None) is not None: # type: ignore
        return TokenInfo('MAYBEARG', arg_str, arg_str, None)
    return cast(TokenInfo, tok)


def tokenize_args(
    args_str: str, 
    _token_iter: Callable[[str], Iterable[TokenInfo]] = partial(
        tokenize_iter, 
        token_cre=make_token_cre(TOKEN_SPECIFICATION), 
        ignore_groups=('WS',), 
        raise_groups=('MISMATCH',), 
    ),
) -> Tuple[Tuple[TokenInfo, ...], Dict[str, TokenInfo]]:
    def last(it):
        try:
            for i in it:
                pass
            return i
        except UnboundLocalError as exc:
            raise ValueError('%r has no last value' %it) from exc

    def setval():
        nonlocal key, val, prev, curr
        if curr is None:
            return
        if prev.group == 'ASSIGN':
            raise SyntaxError('There is no value to assign')
        if key is None:
            if val is None:
                return True
            if kargs:
                raise SyntaxError(
                    'Positional argument %s follows keyword argument %r' 
                    % (val.fullvalue, last(kargs)))
            pargs.append(val)
        else:
            if val is None:
                raise SyntaxError('Keyword argument %s has no value' % key.value)
            if key.value in kargs:
                raise SyntaxError('Keyword argument repeated %s' % key.value)
            kargs[key.value] = val
            key = val = None

    key: Optional[TokenInfo] = None
    val: Optional[TokenInfo] = None
    prev: Optional[TokenInfo] = None
    curr: Optional[TokenInfo] = None

    pargs: List[TokenInfo] = []
    kargs: Dict[str, TokenInfo] = {}
    group: str

    for curr in _token_iter(args_str):
        group = curr.group
        if group == 'NAME':
            val = curr
        elif group == 'ASSIGN':
            if prev is None:
                raise SyntaxError('Missing parameter name before equal sign =')
            elif prev.group == 'COMMA':
                raise SyntaxError('Missing parameter name before equal sign =')
            elif prev.group != 'NAME':
                raise SyntaxError('Wrong parameter name %s' %prev.fullvalue)
            key, val = val, None
        elif group == 'COMMA':
            if setval():
                continue
        else:
            if not (prev is None or prev.group == 'COMMA' or prev.group == 'ASSIGN'):
                raise SyntaxError(
                    'A parameter has at least 2 values %s %s' 
                    % (prev.fullvalue, curr.fullvalue) 
                )
            val = curr
        prev = curr
    else:
        setval()

    return tuple(pargs), kargs


def parse_arg_token(
    token: TokenInfo,
    globals: Optional[dict] = None,
    locals: Optional[Mapping] = None,
):
    group: str = token.group
    value: str = token.value
    if group == 'INT':
        return int(value)
    elif group == 'FLOAT':
        return float(value)
    elif group == 'STRING':
        return value[1:-1]
    elif group == 'NAME':
        if value in ('true', 'True'):
            return True
        elif value in ('false', 'False'):
            return False
        return value
    elif group in ('EVAL', 'EVAL2'):
        return eval(value, globals, locals) if value.strip() else None
    elif group in ('EXEC', 'EXEC2'):
        exec(dedent(value), globals, locals)
        return None
    elif group in ('LAMBDA', 'LAMBDA2'):
        if value.strip():
            code = compile(value, '__main__', 'exec')
            if locals is None:
                locals = globals
            if locals is None:
                locals = {}
            return lambda *args, **kwargs: eval(
                code, globals, ChainMap(locals, 
                {'_args': args, '_kwargs': kwargs, **kwargs}))
        else:
            return lambda *args, **kwargs: None
    else:
        return value


def parse_arg(
    arg_str: str,
    globals: Optional[dict] = None,
    locals: Optional[Mapping] = None,
):
    tok = tokenize_arg(arg_str)
    return parse_arg_token(tok, globals, locals)


def parse_args(
    args_str: str,
    globals: Optional[dict] = None,
    locals: Optional[Mapping] = None,
) -> Tuple[tuple, dict]:
    pargs, kargs = tokenize_args(args_str)
    return tuple(
            parse_arg_token(arg, globals, locals) for arg in pargs
        ), {
            key: parse_arg_token(arg, globals, locals)
            for key, arg in kargs.items()
        }


class TkinterXMLConfigParser:

    def __init__(
        self, 
        path: PathType, 
        namespace: Optional[dict] = None, 
        parser=None, 
        set_name_to_namespace: bool = False, 
    ) -> None:
        self._text: bytes = open(path, 'rb').read()
        self._root = fromstring(self._text, parser)

        if namespace is None:
            namespace = {}
        self.namespace = namespace
        self.set_name_to_namespace = set_name_to_namespace
        self._namemap: MutableMapping = WeakValueDictionary()
        self._pairs: dict = {}

        namespace.update(
            __name__='__main__', 
            __file__=path.decode() if isinstance(path, bytes) else str(path), 
            __self__=self, 
            __root__=self._root, 
            namemap=self._namemap, 
            tkinter=tkinter, 
            tk=tkinter, 
            ttk=ttk, 
        )

        self._tk: tkinter.Tk = self.parse_element(self._root)

    @property
    def text(self) -> bytes:
        return self._text

    @property
    def root(self):
        return self._root

    @property
    def tk(self) -> tkinter.Tk:
        return self._tk

    @cached_property
    def pairs(self):
        return MappingProxyType(self._pairs)

    def getitem_for_tagname(self, tagname: str):
        tagname = tagname.strip()
        if not tagname:
            raise ValueError('Empty tagname')

        l_sep = tagname.strip().split('.')
        if not all(s.isidentifier() for s in l_sep):
            raise ValueError(
                'Invalid (A part of the tagname is not a identifier '
                'was detected) tagname %r' %tagname)

        modm, _, funm = tagname.rpartition('.')
        if modm == '':
            modm = 'tkinter'
        else:
            modm = 'tkinter.' + modm

        try:
            mod = import_module(modm)
        except ImportError:
            try:
                s, *rest_seps = l_sep
                obj = self.namespace[s]
                for s in rest_seps:
                    obj = getattr(obj, s)
                return obj
            except (KeyError, AttributeError):
                raise ValueError('Cannot find item for tagname %r' %tagname)

        try:
            return getattr(mod, funm.title())
        except AttributeError:
            try:
                return getattr(mod, funm)
            except AttributeError:
                try:
                    return self.namespace[funm]
                except KeyError:
                    raise ValueError(
                        'Cannot find item for tagname %r' %tagname)

    def parse_initargs(
        self, 
        el, 
        parent, 
        globals: Optional[dict] = None, 
        locals: Optional[Mapping] = None, 
    ):
        if globals is None:
            globals = self.namespace
        if locals is None:
            extras: dict = {
                'el_text': el.text, 
                'el_tail': el.tail, 
                '__parent__': parent, 
            }
            locals = ChainMap(
                globals, globals.get('namemap', self._namemap), extras)

        el_attrib: MutableMapping = el.attrib

        script_str = el_attrib.get('script-', '')
        if script_str.strip():
            exec(dedent(script_str), globals, locals)

        for k, v in el_attrib.items():
            if k.startswith('_'):
                ret = parse_arg(v, globals, locals)
                el_attrib[k] = v if ret is None else ret

        args_str = el_attrib.get('args-')
        pargs: tuple
        kargs: dict
        if args_str is None:
            pargs, kargs = (), {}
        else:
            pargs, kargs = parse_args(args_str, globals, locals)

        kargs.update(
            (k, parse_arg(v, globals, locals))
            for k, v in el_attrib.items()
            if k.isidentifier()
                and not k.startswith('_')
                and k not in ('id', 'class')
        )

        return pargs, kargs

    def parse_special_attrs(
        self, 
        el, 
        widget,
        parent, 
        globals: Optional[dict] = None, 
        locals: Optional[Mapping] = None, 
    ):
        if globals is None:
            globals = self.namespace
        if locals is None:
            extras: dict = {
                'el_text': el.text, 
                'el_tail': el.tail, 
                '__self__': widget, 
                '__parent__': parent, 
            }
            locals = ChainMap(
                globals, globals.get('namemap', self._namemap), extras)

        el_attrib: MutableMapping = el.attrib

        name = el_attrib.get('name-', '')
        if name:
            namemap = globals.get('namemap', self._namemap)
            namemap[name] = widget
            if self.set_name_to_namespace:
                self.namespace[name] = widget

        if 'data-' in el_attrib:
            setattr(widget, '$data', parse_arg(el_attrib['data-'], globals, locals))

        for attr, args_str in el_attrib.items():
            asw = attr.startswith
            if asw(('p-', 'property-')):
                p_name = attr[2:] if asw('p-') else attr[9:]
                widget[p_name] = parse_arg(args_str, globals, locals)
            elif asw(('m-', 'method-')):
                m_name = attr[2:] if asw('m-') else attr[7:]
                method = getattr(widget, m_name)
                if not callable(method):
                    raise TypeError(f'{widget!r}.{m_name} must be a callable')
                pargs_, kargs_ = parse_args(args_str, globals, locals)
                method(*pargs_, **kargs_)

    def parse_element(
        self, 
        el, 
        parent=None, 
        globals: Optional[dict] = None, 
        locals: Optional[Mapping] = None, 
    ):
        el_tag = el.tag
        if el_tag == 'script':
            return self.parse_element_script(el, parent, globals, locals)

        widget_factory: Optional[Callable] = self.getitem_for_tagname(el_tag)
        if widget_factory is None:
            return
        widget_factory = cast(Callable, widget_factory)

        if globals is None:
            globals = self.namespace
        if locals is None:
            extras: dict = {
                'el_text': el.text, 
                'el_tail': el.tail, 
                '__parent__': parent, 
            }
            locals = ChainMap(
                globals, globals.get('namemap', self._namemap), extras)

        if isinstance(widget_factory, type):
            if parent is None and not issubclass(widget_factory, tkinter.Tk):
                raise ValueError(
                    "The tag name of top level element must be"
                    " 'tk' or 'Tk', got %r" %el_tag)
            elif issubclass(widget_factory, tkinter.Toplevel):
                return self.parse_element_toplevel(
                    el, parent, globals, cls=widget_factory)

        pargs, kargs = self.parse_initargs(el, parent, globals, locals)

        if isinstance(widget_factory, type) and issubclass(widget_factory, tkinter.Menu):
            if parent is None:
                raise ValueError('%r cannot be the top level element' %el_tag)
            label = kargs.pop('label', 'Menu')
            widget = widget_factory(parent, *pargs, **kargs) # type: ignore # Found a bug of mypy?
            if isinstance(parent, tkinter.Menu):
                parent.add_cascade(label=label, menu=widget)
            else:
                parent.config(menu=widget)
        elif parent is None:
            widget = widget_factory(*pargs, **kargs)
            self.namespace.setdefault('__app__', widget)
        else:
            if 'master' in kargs:
                widget = widget_factory(*pargs, **kargs)
            else:
                widget = widget_factory(parent, *pargs, **kargs)
            try:
                widget.pack()
            except:
                pass

        self._pairs[el] = widget
        locals = ChainMap(locals, {'__self__': widget})
        self.parse_special_attrs(el, widget, parent, globals, locals)

        for child in el:
            ctag = child.tag
            if ctag == 'property':
                self.parse_element_property(child, widget, globals, locals)
            elif ctag == 'method':
                self.parse_element_method(child, widget, globals, locals)
            elif ctag.startswith(('m-', 'method-')):
                self.parse_element_method_call(child, widget, globals, locals)
            else:
                self.parse_element(child, widget, globals)

        return widget

    def parse_element_toplevel(
        self, 
        el, 
        parent, 
        globals: Optional[dict] = None, 
        locals: Optional[Mapping] = None, 
        cls=None, 
    ):
        if cls is None:
            cls = tkinter.Toplevel
        _globals, _locals = globals, locals
        if _globals is None:
            _globals = self.namespace
        def call():
            globals = copy(_globals)

            if _locals is None:
                extras: dict = {
                    'el_text': el.text, 
                    'el_tail': el.tail, 
                    '__parent__': parent, 
                }
                locals = ChainMap(
                    globals, globals.get('namemap', self._namemap), extras)
            else:
                locals = ChainMap(globals, _locals)

            pargs, kargs = self.parse_initargs(el, parent, globals, locals)

            self._pairs[el] = widget = cls(*pargs, **kargs)
            locals = ChainMap(locals, {'__self__': widget})

            el_attrib: MutableMapping = el.attrib
            data = el_attrib.get('data-')
            if data is not None:
                setattr(widget, '$data', parse_arg(data))

            self.parse_special_attrs(el, widget, parent, globals, locals)

            for child in el:
                self.parse_element(child, widget, globals)

            parent.wait_window(widget)
            return getattr(widget, '$data', None)

        name = el.attrib.get('name-', '')
        if name:
            _globals[name] = call
            return call
        else:
            return call()

    def parse_element_property(
        self, 
        el, 
        parent, 
        globals: Optional[dict] = None, 
        locals: Optional[Mapping] = None,
    ):
        if el.tag != 'property':
            raise ValueError('Invalid tag name %r for <property>' %el.tag)

        if globals is None:
            globals = self.namespace
        if locals is None:
            extras: dict = {'el_text': el.text, 'el_tail': el.tail, '__self__': parent}
            locals = ChainMap(
                globals, globals.get('namemap', self._namemap), extras)

        for k, v in el.attrib.items():
            parent[k] = parse_arg(v, globals, locals)

    def parse_element_method(
        self, 
        el, 
        parent, 
        globals: Optional[dict] = None, 
        locals: Optional[Mapping] = None, 
    ):
        el_tag, el_attrib = el.tag, el.attrib
        if el_tag != 'method':
            raise ValueError('Invalid tag name %r for <method>' %el_tag)

        if globals is None:
            globals = self.namespace
        if locals is None:
            extras: dict = {
                'el_text': el.text, 
                'el_tail': el.tail, 
                '__self__': parent, 
            }
            extras.update(
                (k, parse_arg(v, globals, locals))
                for k, v in el_attrib.items()
            )
            locals = ChainMap(
                globals, globals.get('namemap', self._namemap), extras)

        for child in el:
            m_name = child.tag
            method = getattr(parent, m_name)
            if not callable(method):
                raise TypeError(f'{parent!r}.{m_name} must be a callable')

            child_attrib = child.attrib

            script_str = child_attrib.get('script-', '')
            if script_str.strip():
                exec(dedent(script_str), globals, locals)

            args_str = child_attrib.get('args-')
            pargs: tuple
            kargs: dict
            if args_str is None:
                pargs, kargs = (), {}
            else:
                pargs, kargs = parse_args(args_str, globals, locals)

            kargs.update(
                (k, parse_arg(v, globals, locals))
                for k, v in child_attrib.items()
                if k.isidentifier()
            )

            method(*pargs, **kargs)

    def parse_element_method_call(
        self, 
        el, 
        parent, 
        globals: Optional[dict] = None, 
        locals: Optional[Mapping] = None, 
    ):
        el_tag, el_attrib = el.tag, el.attrib
        if el_tag.startswith('m-'):
            m_name = el_tag[2:]
        elif el_tag.startswith('method-'):
            m_name = el_tag[7:]
        else:
            raise ValueError('Invalid tag name %r for method call' %el_tag)

        method = getattr(parent, m_name)
        if not callable(method):
            raise TypeError(f'{parent!r}.{m_name} must be a callable')

        if globals is None:
            globals = self.namespace
        if locals is None:
            extras: dict = {
                'el_text': el.text, 
                'el_tail': el.tail, 
                '__self__': parent, 
            }
            locals = ChainMap(
                globals, globals.get('namemap', self._namemap), extras)

        pargs: tuple = tuple(self.parse_element(child, parent, globals) for child in el)
        kargs: dict

        args_str = el_attrib.get('args-')
        if args_str is None:
            kargs = {}
        else:
            pargs_, kargs = parse_args(args_str, globals, locals)
            pargs += pargs_

        kargs.update(
            (k, parse_arg(v, globals, locals))
            for k, v in el_attrib.items()
            if k.isidentifier()
        )

        method(*pargs, **kargs)

    def parse_element_script(
        self, 
        el, 
        parent, 
        globals: Optional[dict] = None, 
        locals: Optional[Mapping] = None, 
    ):
        script = el.text

        source = dedent(script)
        module_name = el.attrib.get('module')

        if globals is None:
            globals = self.namespace
        if locals is None:
            extras: dict = {
                'el_text': el.text, 
                'el_tail': el.tail, 
                '__parent__': parent, 
            }
            locals = ChainMap(
                globals, globals.get('namemap', self._namemap), extras)

        if module_name is not None:
            module = ModuleType(module_name)
            globals[module_name] = module
            globals = module.__dict__
            locals  = ChainMap(globals, locals)

        exec(source, globals, locals)

    def find(self, path, *args, **kwds):
        el = self._root.find(path, *args, **kwds)
        if el in self._pairs:
            return el, self._pairs[el]

    def iterfind(self, path, *args, **kwds):
        iterel = self._root.iterfind(path, *args, **kwds)
        pairs = self._pairs
        for el in iterel:
            if el in pairs:
                yield el, pairs[el]

    def findall(self, path, *args, **kwds):
        els = self._root.findall(path, *args, **kwds)
        pairs = self._pairs
        return {el: pairs[el] for el in els if el in pairs}

    def xpath(self, path: str, *args, **kwds) -> dict:
        try:
            xpath = self._root.xpath
        except AttributeError as exc:
            raise NotImplementedError('xpath') from exc
        els = xpath(path, *args, **kwds)
        pairs = self._pairs
        return {el: pairs[el] for el in els if el in pairs}

    def cssselect(self, expr: str, *args, **kwds) -> dict:
        try:
            cssselect = self._root.cssselect
        except AttributeError as exc:
            raise NotImplementedError('cssselect') from exc
        els = cssselect(expr, *args, **kwds)
        pairs = self._pairs
        return {el: pairs[el] for el in els if el in pairs}

    def start(self, *args, **kwds):
        self._tk.mainloop(*args, **kwds)


if __name__ == '__main__':
    import sys

    parser = TkinterXMLConfigParser(sys.argv[1])
    parser.start()

