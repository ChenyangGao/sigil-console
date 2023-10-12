#!/usr/bin/env python
# coding: utf-8

from __future__ import annotations

"""
This module provides some functions for modifying files in the 
`Sigil Ebook Editor <https://sigil-ebook.com/>` plug-ins.
"""

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 1, 4)
__all__ = [
    "html_fromstring", "html_tostring", "xml_fromstring", "xml_tostring", 
    "IterMatchInfo", "re_iter", "re_sub", "WriteBack", "DoNotWriteBack", "edit", 
    "ctx_edit", "ctx_edit_sgml", "ctx_edit_html", "read_iter", "read_html_iter", 
    "edit_iter", "edit_batch", "edit_html_iter", "edit_html_batch", 
    "EditCache", "TextEditCache", 
]

import sys

from contextlib import contextmanager
from enum import Enum
from functools import partial
from re import compile as re_compile, Match, Pattern
from typing import (
    cast, Any, AnyStr, Callable, ContextManager, Dict, Final, 
    Generator, Iterable, Iterator, List, Mapping, MutableMapping, 
    NamedTuple, Optional, Tuple, TypeVar, Union, 
)
from types import MappingProxyType

try:
    from bookcontainer import BookContainer # type: ignore
except ImportError:
    pass

try:
    from plugin_util.pip_tool import ensure_install

    ensure_install("lxml")
    ensure_install("cssselect")

    from cssselect.xpath import GenericTranslator # type: ignore
    from lxml.cssselect import CSSSelector # type: ignore
    from lxml.etree import _Element as Element, XPath # type: ignore
except ImportError:
    from xml.etree.ElementTree import Element
    from plugin_util.htmlparser import ( # type: ignore
        html_fromstring, html_tostring, xml_fromstring, xml_tostring
    )
    _LXML_IMPORTED = False
else:
    from plugin_util.lxmlparser import ( # type: ignore
        html_fromstring, html_tostring, xml_fromstring, xml_tostring
    )
    _LXML_IMPORTED = True


T = TypeVar("T")
PatternType = Union[AnyStr, Pattern]


def _ensure_bc(
    bc: Optional[BookContainer] = None, 
    frame_back: int = 2, # positive integer
) -> BookContainer:
    """Helper function to guarantee that the return value is 
    `bookcontainer.BookContainer` type"""
    if isinstance(bc, BookContainer):
        return bc
    elif bc is None:
        try:
            bc = sys._getframe(frame_back).f_globals["bc"]
            if not isinstance(bc, BookContainer):
                raise TypeError
        except (KeyError, TypeError):
            import plugin_help as plugin
            bc = BookContainer(plugin.WRAPPER)
        return bc
    raise TypeError("Expected type %r, got %r" % (BookContainer, type(bc)))


class IterMatchInfo(NamedTuple):
    """Context information wrapper for regular expression matches.

    - **bc**: The ePub editor object `BookContainer`. 
        `BookContainer` object is an object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    - **manifest_id**: The file's manifest id (listed in the OPF file).
    - **local_no**: Number in the current file (from 1).
    - **global_no**: Number in all files (from 1).
    - **file_no**: Number of processed files (from 1).
    - **href**: The file's OPF href.
    - **mimetype**: The file's media type.
    - **match**: The regular expression match object.
    - **string**: The content of the current file.
    """
    bc: BookContainer
    manifest_id: str
    local_no: int  # unsigned integer
    global_no: int # unsigned integer
    file_no: int   # unsigned integer
    href: str
    mimetype: str
    match: Match
    string: Union[bytes, str]


def re_iter(
    pattern: PatternType, 
    manifest_id_s: Union[None, str, Iterable[str]] = None, 
    bc: Optional[BookContainer] = None, 
    errors: str = "ignore", 
    more_info: bool = False, 
) -> Union[Generator[Match, None, None], Generator[IterMatchInfo, None, None]]:
    """Iterate over each of the files corresponding to the given manifest_id_s 
    with regular expressions, and yield matches one by one.

    :param pattern: A regular expression pattern string or compiled object.
    :param manifest_id_s: Manifest id collection, are listed in OPF file,
        The XPath as following (the `namespace` depends on the specific situation):

            /namespace:package/namespace:manifest/namespace:item/@id

        If manifest_id_s is None (the default), it will get by `bc.text_iter()`.
    :param bc: `BookContainer` object. 
        If it is None (the default), will be found in caller's globals().
        `BookContainer` object is an object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    :param errors: Strategies for errors, it can take a value in ("ignore", "raise", "skip").

        - **ignore**: Ignore the error and continue processing, but the number will increase.
        - **skip**: Ignore the error and continue processing, the number will not increase.
        - **raise**: Raise the error and stop processing.

    :param more_info: 
        If false, the yielding results are the match object of the regular expression,
        else the yielding results are the namedtuple `IterMatchInfo` objects, 
        including the following fields:

            - **bc**: The ePub editor object.
            - **manifest_id**: The file's manifest id (listed in the OPF file)
            - **local_no**: Number in the current file (from 1)
            - **global_no**: Number in all files (from 1)
            - **file_no**: Number of processed files (from 1)
            - **href**: The file's OPF href 
            - **mimetype**: The file's media type
            - **match**: The regular expression match object
            - **string**: The content of the current file

    :return: Generator, if `more_info` is True, then yield `IterMatchInfo` object, 
             else yield `Element` object.

    :Examples:

        .. code-block:: python

            # Print all text node match objects one by one
            for text in re_iter(r"(?<=>)[^<]+"):
                print(text)
    """
    bc = cast(BookContainer, _ensure_bc(bc))

    fn: Callable = re_compile(pattern).finditer

    if manifest_id_s is None:
        manifest_id_s = (info[0] for info in bc.text_iter())
    elif isinstance(manifest_id_s, str):
        manifest_id_s = (manifest_id_s,)

    if more_info:
        local_no: int  = 1
        global_no: int = 1
        file_no: int   = 1

        for fid in manifest_id_s:
            href = bc.id_to_href(fid)
            mime = bc.id_to_mime(fid)
            try:
                string = bc.readfile(fid)
                local_no = 1
                for match in fn(string):
                    yield IterMatchInfo(
                        bc, fid, local_no, global_no, file_no, 
                        href, mime, match, string)
                    local_no  += 1
                    global_no += 1
            except:
                if errors == "skip":
                    continue
                elif errors == "raise":
                    raise
            file_no += 1
    else:
        for fid in manifest_id_s:
            try:
                string = bc.readfile(fid)
                yield from fn(string)
            except:
                if errors == "raise":
                    raise


def re_sub(
    pattern: PatternType, 
    repl: Union[AnyStr, Callable[[Match], AnyStr], Callable[[IterMatchInfo], AnyStr]], 
    manifest_id_s: Union[None, str, Iterable[str]] = None, 
    bc: Optional[BookContainer] = None, 
    errors: str = "ignore", 
    more_info: bool = False, 
) -> None:
    """Iterate over each of the files corresponding to the given manifest_id_s 
    with regular expressions, and replace all matches.

    :param pattern: A regular expression pattern string or compiled object.
    :param repl: 
        `repl` can be either a string or a callable.
        If it is a string, backslash escapes in it are processed.
        If it is a callable, it's passed the specified object (see param `more_info`) 
        and must return a replacement string to be used.
    :param manifest_id_s: Manifest id collection, are listed in OPF file,
        The XPath as following (the `namespace` depends on the specific situation):

            /namespace:package/namespace:manifest/namespace:item/@id

        If manifest_id_s is None (the default), it will get by `bc.text_iter()`.
    :param bc: `BookContainer` object. 
        If it is None (the default), will be found in caller's globals().
        `BookContainer` object is an object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    :param errors: Strategies for errors, it can take a value in ("ignore", "raise", "skip").

        - **ignore**: Ignore the error and continue processing, but the number will increase.
        - **skip**: Ignore the error and continue processing, the number will not increase.
        - **raise**: Raise the error and stop processing.

    :param more_info: This parameter only takes effect when `repl` is a callable.
        If false, the argument was passed to the `repl` function is the match object of the regular expression,
        else the argument was passed to the `repl` function is the namedtuple `IterMatchInfo` object, 
        including the following fields:

            - **bc**: The ePub editor object.
            - **manifest_id**: The file's manifest id (listed in the OPF file)
            - **local_no**: Number in the current file (from 1)
            - **global_no**: Number in all files (from 1)
            - **file_no**: Number of processed files (from 1)
            - **href**: The file's OPF href 
            - **mimetype**: The file's media type
            - **match**: The regular expression match object
            - **string**: The content of the current file

    :Examples:

        .. code-block:: python

            # clear all text nodes" text
            re_sub(r"(?<=>)[^<]+", "")
    """
    bc = cast(BookContainer, _ensure_bc(bc))

    fn: Callable = re_compile(pattern).sub

    if manifest_id_s is None:
        manifest_id_s = (info[0] for info in bc.text_iter())
    elif isinstance(manifest_id_s, str):
        manifest_id_s = (manifest_id_s,)

    if callable(repl):
        repl = cast(Callable[..., AnyStr], repl)

        local_no: int = 1
        global_no: int = 1
        file_no: int = 1

        if more_info:
            def _repl(match):
                nonlocal local_no, global_no
                try:
                    ret = repl(IterMatchInfo(
                        bc, fid, local_no, global_no, file_no, 
                        href, mime, match, string))
                except:
                    if errors == "skip":
                        global_no = old_global_no
                        raise
                    elif errors == "raise":
                        raise
                else:
                    local_no += 1
                    global_no += 1
                    return ret
        else:
            _repl = repl

        for fid in manifest_id_s:
            old_global_no = global_no
            local_no = 1
            href = bc.id_to_href(fid)
            mime = bc.id_to_mime(fid)
            try:
                string = bc.readfile(fid)
                string_new = fn(_repl, string)
                if string != string_new:
                    bc.writefile(fid, string_new)
            except:
                if errors == "skip":
                    continue
                elif errors == "raise":
                    raise
            file_no += 1
    else:
        for fid in manifest_id_s:
            try:
                string = bc.readfile(fid)
                string_new = fn(repl, string)
                if string != string_new:
                    bc.writefile(fid, string_new)
            except:
                if errors == "raise":
                    raise


class WriteBack(Exception):
    """If changes require writing back to the file, 
    you can raise this exception"""

    def __init__(self, data):
        self.data = data


class DoNotWriteBack(Exception):
    """If changes do not require writing back to the file, 
    you can raise this exception"""


def edit(
    manifest_id: str, 
    operate: Callable[..., Union[bytes, str]], 
    bc: Optional[BookContainer] = None, 
) -> bool:
    """Read the file data, operate on, and then write the changed data back

    :param manifest_id: Manifest id, is listed in OPF file, 
        The XPath as following (the `namespace` depends on the specific situation):

            /namespace:package/namespace:manifest/namespace:item/@id

    :param operate: Take data in, operate on, and then return the changed data.
    :param bc: `BookContainer` object. 
        If it is None (the default), will be found in caller's globals().
        `BookContainer` object is an object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.

    :return: Is it successful?
    """
    bc = cast(BookContainer, _ensure_bc(bc))

    content = bc.readfile(manifest_id)

    try:
        content_new = operate(content)
    except DoNotWriteBack:
        return False
    except WriteBack as exc:
        content_new = exc.data
        if content_new is None:
            return False

    if content != content_new:
        bc.writefile(manifest_id, content_new)
        return True

    return False


@contextmanager
def ctx_edit(
    manifest_id: str, 
    bc: Optional[BookContainer] = None, 
    wrap_me: bool = False, 
) -> Generator[Union[dict, bytes, str], None, bool]:
    """Read and yield the file data, and then take in and write back the changed data.

    :param manifest_id: Manifest id, is listed in OPF file, 
        The XPath as following (the `namespace` depends on the specific situation):

            /namespace:package/namespace:manifest/namespace:item/@id

    :param bc: `BookContainer` object. 
        If it is None (the default), will be found in caller's globals().
        `BookContainer` object is an object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    :param wrap_me: Whether to wrap up object, if True, 
        return a dict containing keys ("manifest_id", "data", "write_back").

    :return: A context manager that returns the `data`

        .. code-block:: python

            if wrap_me:
                data: dict = {
                    "manifest_id": manifest_id, 
                    "data": bc.readfile(manifest_id), 
                    "write_back": True, 
                }
            else:
                data: Union[bytes, str] = bc.readfile(manifest_id)

    :Examples:

        .. code-block:: python

            def operations_on_content(data_old):
                ...
                return data_new

            with ctx_edit(manifest_id, bc) as content:
                content_new = operations_on_content(content)
                # If you need writing back
                if you_need_writing_back:
                    raise WriteBack(content_new)
                else: # If you don"t need writing back, just pass
                    pass

            # OR equivalent to
            with ctx_edit(manifest_id, bc, wrap_me=True) as data:
                content = data["data"]
                content_new = operations_on_content(content)
                # If you need writing back
                if you_need_writing_back:
                    data["data"] = content_new
                else: # If you don"t need writing back
                    raise DoNotWriteBack
                    # OR equivalent to:
                    # data["write_back"] = False
                    # OR equivalent to:
                    ## del data["write_back"]
                    # OR equivalent to:
                    ## data["data"] = None
                    # OR equivalent to:
                    ## del data["data"]
    """
    bc = cast(BookContainer, _ensure_bc(bc, 3))

    content = bc.readfile(manifest_id)

    try:
        if wrap_me:
            data = {
                "manifest_id": manifest_id, 
                "data": content,
                "write_back": True,
            }
            yield data
            if data.get("data") is None or not data.get("write_back"):
                raise DoNotWriteBack
            content_new = data["data"]
        else:
            yield content
            raise DoNotWriteBack
    except DoNotWriteBack:
        return False
    except WriteBack as exc:
        content_new = exc.data
        if content_new is None:
            return False

    if content != content_new:
        bc.writefile(manifest_id, content_new)
        return True

    return False


@contextmanager
def ctx_edit_sgml(
    manifest_id: str,
    bc: Optional[BookContainer] = None, 
    fromstring: Callable = xml_fromstring,
    tostring: Callable[..., Union[bytes, bytearray, str]] = xml_tostring,
) -> Generator[Any, Any, bool]:
    """Read and yield the etree object (parsed from a xml file), 
    and then write back the above etree object.

    :param manifest_id: Manifest id, is listed in OPF file, 
        The XPath as following (the `namespace` depends on the specific situation):

            /namespace:package/namespace:manifest/namespace:item/@id

    :param bc: `BookContainer` object. 
        If it is None (the default), will be found in caller's globals().
        `BookContainer` object is an object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    :param fromstring: Parses an XML or SGML document or fragment from a string.
        Returns the root node (or the result returned by a parser target).
    :param tostring: Serialize an element to an encoded string representation of its XML or SGML tree.

    :Examples:

        .. code-block:: python

            def operations_on_etree(etree):
                ...

            with ctx_edit_sgml(manifest_id, bc) as etree:
                operations_on_etree(etree)
                # If you don"t need writing back
                ## raise DoNotWriteBack
    """
    bc = cast(BookContainer, _ensure_bc(bc, 3))

    content = bc.readfile(manifest_id)
    tree = fromstring(content.encode("utf-8"))

    try:
        yield tree
    except DoNotWriteBack:
        return False
    except WriteBack as exc:
        content_new = exc.data
        if content_new is None:
            return False
        elif not isinstance(content_new, (bytes, bytearray, str)):
            content_new = tostring(content_new)
    else:
        content_new = tostring(tree)

    if isinstance(content_new, (bytes, bytearray)):
        content_new = content_new.decode("utf-8")

    if content != content_new:
        bc.writefile(manifest_id, content_new)
        return True

    return False


@contextmanager
def ctx_edit_html(
    manifest_id: str, 
    bc: Optional[BookContainer] = None, 
) -> Generator[Any, Any, bool]:
    """Read and yield the etree object (parsed from a (X)HTML file), 
    and then write back the above etree object.

    :param manifest_id: Manifest id, is listed in OPF file, 
        The XPath as following (the `namespace` depends on the specific situation):

            /namespace:package/namespace:manifest/namespace:item/@id

    :param bc: `BookContainer` object. 
        If it is None (the default), will be found in caller's globals().
        `BookContainer` object is an object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.

    :Examples:

        .. code-block:: python

            def operations_on_etree(etree):
                ...

            with ctx_edit_html(manifest_id, bc) as etree:
                operations_on_etree(etree)
                # If you don"t need writing back
                ## raise DoNotWriteBack
    """
    bc = cast(BookContainer, _ensure_bc(bc, 3))

    return (yield from ctx_edit_sgml.__wrapped__( # type: ignore
        manifest_id, 
        bc, 
        html_fromstring, 
        partial(
            html_tostring, 
            method="xhtml" if "xhtml" in bc.id_to_mime(manifest_id) else "html",
        ),
    ))


def read_iter(
    manifest_id_s: Union[None, str, Iterable[str]] = None, 
    bc: Optional[BookContainer] = None, 
) -> Generator[Tuple[str, str, Union[bytes, str]], None, None]:
    """Iterate over the data of each manifest_id_s.

    :param manifest_id_s: Manifest id collection, are listed in OPF file,
        The XPath as following (the `namespace` depends on the specific situation):

            /namespace:package/namespace:manifest/namespace:item/@id

        If manifest_id_s is None (the default), it will get by `bc.manifest_iter()`.
    :param bc: `BookContainer` object. 
        If it is None (the default), will be found in caller's globals().
        `BookContainer` object is an object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    """
    bc = cast(BookContainer, _ensure_bc(bc))

    it: Iterable[Tuple[str, str]]
    if manifest_id_s is None:
        it = (info[:2] for info in bc.manifest_iter())
    elif isinstance(manifest_id_s, str):
        it = (manifest_id_s, bc.id_to_href(manifest_id_s)), 
    else:
        it = ((id, bc.id_to_href(id)) for id in manifest_id_s)

    for fid, href in it:
        yield fid, href, bc.readfile(fid)


def read_html_iter(
    manifest_id_s: Union[None, str, Iterable[str]] = None, 
    bc: Optional[BookContainer] = None, 
) -> Generator[Tuple[str, str, Element], None, None]:
    """Iterate over the data as (X)HTML etree object of each manifest_id_s.

    :param manifest_id_s: Manifest id collection, are listed in OPF file,
        The XPath as following (the `namespace` depends on the specific situation):

            /namespace:package/namespace:manifest/namespace:item/@id

        If manifest_id_s is None (the default), it will get by `bc.manifest_iter()`.
    :param bc: `BookContainer` object. 
        If it is None (the default), will be found in caller's globals().
        `BookContainer` object is an object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    """
    bc = cast(BookContainer, _ensure_bc(bc))

    it: Iterable[Tuple[str, str]]
    if manifest_id_s is None:
        it = (info[:2] for info in bc.text_iter())
    elif isinstance(manifest_id_s, str):
        it = (manifest_id_s, bc.id_to_href(manifest_id_s)), 
    else:
        it = ((id, bc.id_to_href(id)) for id in manifest_id_s)

    for fid, href in it:
        yield fid, href, html_fromstring(bc.readfile(fid).encode("utf-8"))


def edit_iter(
    manifest_id_s: Union[None, str, Iterable[str]] = None, 
    bc: Optional[BookContainer] = None, 
    wrap_me: bool = False, 
    yield_cm: bool = False, 
):
    """Used to process a collection of specified files in ePub file one by one

    :param manifest_id_s: Manifest id collection, are listed in OPF file,
        The XPath as following (the `namespace` depends on the specific situation):

            /namespace:package/namespace:manifest/namespace:item/@id

        If manifest_id_s is None (the default), it will get by `bc.manifest_iter()`.
    :param bc: `BookContainer` object. 
        If it is None (the default), will be found in caller's globals().
        `BookContainer` object is an object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    :param wrap_me: Will pass to function ctx_edit as keyword argument.
    :param yield_cm: Determines whether each iteration returns the context manager.

    :Examples:

        .. code-block:: python

            def operations_on_content(data_old):
                ...
                return data_new

            edit_worker = edit_iter(manifest_id_s, bc)
            for fid, content in edit_worker:
                content_new = operations_on_content(content)
                # **NOTE**: `content_new` can"t be None
                if you_need_writing_back:
                    edit_worker.send(content_new)
                else: # If you don"t need writing back, just pass
                    pass

            # OR equivalent to
            for fid, data in edit_iter(manifest_id_s, bc, wrap_me=True):
                content = data["data"]
                content_new = operations_on_content()
                if you_need_writing_back:
                    data["data"] = content_new
                else: # If you don"t need writing back
                    data["write_back"] = False
                    # OR equivalent to:
                    ## del data["write_back"]
                    # OR equivalent to:
                    ## data["data"] = None
                    # OR equivalent to:
                    ## del data["data"]

            # OR equivalent to
            for fid, cm in edit_iter(manifest_id_s, bc, yield_cm=True):
                with cm as content:
                    content_new = operations_on_content()
                    if you_need_writing_back:
                        raise WriteBack(content_new)
                    else: # If you don"t need writing back, just pass
                        pass
                        # OR equivalent to:
                        ## raise DoNotWriteBack
    """
    bc = cast(BookContainer, _ensure_bc(bc))

    if manifest_id_s is None:
        manifest_id_s = (info[0] for info in bc.manifest_iter())
    elif isinstance(manifest_id_s, str):
        manifest_id_s = (manifest_id_s,)

    for fid in manifest_id_s:
        if yield_cm:
            yield fid, ctx_edit(fid, bc, wrap_me=wrap_me)
        else:
            with ctx_edit(fid, bc, wrap_me=wrap_me) as data:
                recv_data = yield fid, data
                if recv_data is not None:
                    while True:
                        send_data = recv_data
                        recv_data = yield
                        if recv_data is None:
                            raise WriteBack(send_data)


class SuccessStatus(NamedTuple):
    """This class is used to illustrate the running result
    """
    manifest_id: str
    is_success: bool = True
    error: Optional[Exception] = None


def edit_batch(
    operate: Callable, 
    manifest_id_s: Union[None, str, Iterable[str]] = None, 
    bc: Optional[BookContainer] = None, 
) -> List[SuccessStatus]:
    """Used to process a collection of specified files in ePub file one by one

    :param manifest_id_s: Manifest id collection, are listed in OPF file,
        The XPath as following (the `namespace` depends on the specific situation):

            /namespace:package/namespace:manifest/namespace:item/@id

        If manifest_id_s is None (the default), it will get by `bc.manifest_iter()`.
    :param operate: Take data in, operate on, and then return the changed data.
    :param bc: `BookContainer` object. 
        If it is None (the default), will be found in caller's globals().
        `BookContainer` object is an object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.

    :return: List of tuples of success status.

    :Examples:

        .. code-block:: python

            def operations_on_content(data_old):
                ...
                return data_new

            edit_batch(operations_on_content, manifest_id_s, bc)
    """
    bc = cast(BookContainer, _ensure_bc(bc))

    if manifest_id_s is None:
        manifest_id_s = (info[0] for info in bc.manifest_iter())
    elif isinstance(manifest_id_s, str):
        manifest_id_s = (manifest_id_s,)

    success_status: List[SuccessStatus] = []
    for fid in manifest_id_s:
        try:
            with ctx_edit(fid, bc) as content:
                raise WriteBack(operate(content))
            success_status.append(SuccessStatus(fid))
        except Exception as exc:
            success_status.append(SuccessStatus(fid, False, exc))
    return success_status


def edit_html_iter(
    manifest_id_s: Union[None, str, Iterable[str]] = None, 
    bc: Optional[BookContainer] = None, 
    wrap_me: bool = False, 
    yield_cm: bool = False, 
):
    """Used to process a collection of specified (X)HTML files in ePub file one by one

    :param manifest_id_s: Manifest id collection, are listed in OPF file,
        The XPath as following (the `namespace` depends on the specific situation):

            /namespace:package/namespace:manifest/namespace:item/@id

        If manifest_id_s is None (the default), it will get by `bc.text_iter()`.
    :param bc: `BookContainer` object. 
        If it is None (the default), will be found in caller's globals().
        `BookContainer` object is an object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    :param wrap_me: Whether to wrap up object, if True, return a dict containing keys 
        ("manifest_id", "data", "write_back")
    :param yield_cm: Determines whether each iteration returns the context manager.

    :Examples:

        .. code-block:: python

            def operations_on_etree(etree):
                ...

            edit_worker = edit_html_iter(manifest_id_s, bc)
            for fid, etree in edit_worker:
                operations_on_etree(etree)
                # If you don"t need writing back
                ## edit_worker.throw(DoNotWriteBack)

            # OR equivalent to
            for fid, data in edit_html_iter(manifest_id_s, bc, wrap_me=True):
                operations_on_etree(data["etree"])
                # If you don"t need writing back
                ## data["write_back"] = False
                # OR equivalent to:
                ## del data["write_back"]
                # OR equivalent to:
                ## data["data"] = None
                # OR equivalent to:
                ## del data["data"]

            # OR equivalent to
            for fid, cm in edit_html_iter(manifest_id_s, bc, yield_cm=True):
                with cm as etree:
                    operations_on_etree(etree)
                    # If you don"t need writing back
                    ## raise DoNotWriteBack
    """
    bc = cast(BookContainer, _ensure_bc(bc))

    if manifest_id_s is None:
        manifest_id_s = (info[0] for info in bc.text_iter())
    elif isinstance(manifest_id_s, str):
        manifest_id_s = (manifest_id_s,)

    for fid in manifest_id_s:
        if yield_cm:
            yield fid, ctx_edit_html(fid, bc)
        else:
            with ctx_edit_html(fid, bc) as tree:
                if wrap_me:
                    data = {
                        "manifest_id": fid, 
                        "data": tree, 
                        "write_back": True, 
                    }
                    recv_data = yield fid, data
                    if recv_data is None:
                        if data.get("data") is None or not data.get("write_back"):
                            raise DoNotWriteBack
                        raise WriteBack(data["data"])
                else:
                    recv_data = yield fid, tree
                if recv_data is not None:
                    while True:
                        send_data = recv_data
                        recv_data = yield
                        if recv_data is None:
                            raise WriteBack(send_data)


def edit_html_batch(
    operate: Callable[[Element], Any], 
    manifest_id_s: Union[None, str, Iterable[str]] = None, 
    bc: Optional[BookContainer] = None, 
) -> List[SuccessStatus]:
    """Used to process a collection of specified (X)HTML files in ePub file one by one

    :param operate: Take etree object in, operate on.
    :param manifest_id_s: Manifest id collection, are listed in OPF file,
        The XPath as following (the `namespace` depends on the specific situation):

            /namespace:package/namespace:manifest/namespace:item/@id

        If manifest_id_s is None (the default), it will get by `bc.text_iter()`.
    :param bc: `BookContainer` object. 
        If it is None (the default), will be found in caller's globals().
        `BookContainer` object is an object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.

    :return: List of tuples of success status.

    :Examples:

        .. code-block:: python

            def operations_on_etree(etree):
                ...

            edit_html_batch(operations_on_etree, manifest_id_s, bc)
    """
    bc = cast(BookContainer, _ensure_bc(bc))

    if manifest_id_s is None:
        manifest_id_s = (info[0] for info in bc.text_iter())
    elif isinstance(manifest_id_s, str):
        manifest_id_s = (manifest_id_s,)

    success_status: List[SuccessStatus] = []
    for fid in manifest_id_s:
        try:
            with ctx_edit_html(fid, bc) as tree:
                operate(tree)
            success_status.append(SuccessStatus(fid))
        except Exception as exc:
            success_status.append(SuccessStatus(fid, False, exc))
    return success_status


if _LXML_IMPORTED:
    class IterElementInfo(NamedTuple):
        """The wrapper for the output tuple, contains the following fields

        - **bc**:          The ePub editor object `BookContainer`
        - **manifest_id**: The file's manifest id (listed in the OPF file)
        - **local_no**:    Number in the current file (from 1)
        - **global_no**:   Number in all files (from 1)
        - **file_no**:     Number of processed files (from 1)
        - **href**:        OPF href
        - **mimetype**:    Media type
        - **element**:     (X)HTML element object
        - **etree**:       (X)HTML tree object
        """
        bc: BookContainer
        manifest_id: str
        local_no: int  # unsigned integer
        global_no: int # unsigned integer
        file_no: int   # unsigned integer
        href: str
        mimetype: str
        element: Element
        etree: Element

    class EnumSelectorType(Enum):
        """Selector type enumeration.

        .xpath:  Indicates that the selector type is XPath.
        .cssselect: Indicates that the selector type is CSS Selector.
        """

        xpath  = 1
        XPath  = 1
        cssselect = 2
        CSS_Selector = 2

        @classmethod
        def of(enum_cls, value):
            val_cls = type(value)
            if val_cls is enum_cls:
                return value
            elif issubclass(val_cls, int):
                return enum_cls(value)
            elif issubclass(val_cls, str):
                try:
                    return enum_cls[value]
                except KeyError as exc:
                    raise ValueError(value) from exc
            raise TypeError(f"expected value's type in ({enum_cls!r}"
                            f", int, str), got {val_cls}")

    def element_iter(
        path: Union[str, XPath] = "descendant-or-self::*", 
        bc: Optional[BookContainer] = None, 
        seltype: Union[int, str, EnumSelectorType] = EnumSelectorType.cssselect, 
        namespaces: Optional[Mapping] = None, 
        translator: Union[str, GenericTranslator] = "xml",
        more_info: bool = False,
    ) -> Union[Generator[Element, None, None], Generator[IterElementInfo, None, None]]:
        """Traverse all (X)HTML files in epub, search the elements that match the path, 
        and return the relevant information of these elements one by one.

        :param path: A XPath expression or CSS Selector expression.
                    If its `type` is `str`, then it is a XPath expression or 
                    CSS Selector expression determined by `seltype`.
                    If its type is a subclass of "lxml.etree.XPath"`, then 
                    parameters `seltype`, `namespaces`, `translator` are ignored.
        :param bc: `BookContainer` object. 
            If it is None (the default), will be found in caller's globals().
            `BookContainer` object is an object of ePub book content provided by Sigil, 
            which can be used to access and operate the files in ePub.
        :param seltype: Selector type. It can be any value that can be 
                        accepted by `EnumSelectorType.of`, the return value called final value.
                        If its final value is `EnumSelectorType.xpath`, then parameter
                        `translator` is ignored.
        :param namespaces: Prefix-namespace mappings used by `path`.

            To use CSS namespaces, you need to pass a prefix-to-namespace
            mapping as `namespaces` keyword argument::

                >>> from lxml import cssselect, etree
                >>> rdfns = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
                >>> select_ns = cssselect.CSSSelector("root > rdf|Description",
                ...                                   namespaces={"rdf": rdfns})

                >>> rdf = etree.XML((
                ...     "<root xmlns:rdf="%s">"
                ...       "<rdf:Description>blah</rdf:Description>"
                ...     "</root>") % rdfns)
                >>> [(el.tag, el.text) for el in select_ns(rdf)]
                [("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description", "blah")]

        :param translator: A CSS Selector expression to XPath expression translator object.
        :param more_info: Determine whether to wrap the yielding results.
            If false, the yielding results are the match objects of the `path` expression,
            else are the namedtuple `IterElementInfo` objects (with some context information).

        :return: Generator, if `more_info` is True, then yield `IterElementInfo` object, 
                else yield `Element` object.

        :Examples:

            .. code-block:: python

                def operations_on_element(element):
                    ...

                for info in element_iter(css_selector, bc):
                    operations_on_element(element)

                # OR equivalent to
                for element in element_iter(css_selector, bc, more_info=True):
                    operations_on_element(info.element)
        """
        select: XPath
        if isinstance(path, str):
            if EnumSelectorType.of(seltype) is EnumSelectorType.cssselect:
                select = CSSSelector(
                    path, namespaces=namespaces, translator=translator)
            else:
                select = XPath(path, namespaces=namespaces)
        else:
            select = path

        bc = cast(BookContainer, _ensure_bc(bc))

        global_no: int = 0
        data: dict
        for file_no, (fid, tree) in enumerate(edit_html_iter(bc=bc), 1): # type: ignore
            href = bc.id_to_href(fid)
            mime = bc.id_to_mime(fid)
            els = select(tree)
            if not els:
                del data["write_back"]
                continue
            if more_info:
                for local_no, (global_no, el) in enumerate(enumerate(els, global_no + 1), 1):
                    yield IterElementInfo(
                        bc, fid, local_no, global_no, file_no, href, mime, el, tree)
            else:
                yield from els

    __all__.extend(("IterElementInfo", "EnumSelectorType", "element_iter"))


class EditCache(MutableMapping[str, T]):
    """Initialize an `EditCache` object that can proxy accessing to 
    `bookcontainer.Bookcontainer` object.
    The edited files" data of this `EditCache` object are cached and not immediately 
    written back to the `bookcontainer.Bookcontainer` object, until the `__exit__` 
    method or the `clear` method are called, and then this `EditCache` object is cleared.

    **NOTE**: This can operate all the files declared in the OPF file in ePub.

    **NOTE**: A manifest id is available or not, can be determined by `__contains__` method.

    **NOTE**: If you need to directly operate on the corresponding `bookcontainer.Bookcontainer` object (e.g., delete a file), please clear this editcache first.

    :param bc: `BookContainer` object. 
        If it is None (the default), will be found in caller's globals().
        `BookContainer` object is an object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.

    :Examples:

        .. code-block:: python

            # Change "utf-8" to "UTF-8" in all (X)HTML texts

            .. code-block:: python


                with EditCache(bc) as cache:
                    for fid, *_ in cache.bookcontainer.text_iter():
                        cache[fid] = cache[fid].replace("utf-8", "UTF-8")
    """

    __context_factory__: Callable[[str, BookContainer], ContextManager] = lambda fid, bc: ctx_edit(fid, bc)

    def __init__(self, bc: Optional[BookContainer] = None) -> None:
        bc = cast(BookContainer, _ensure_bc(bc))
        self._exit_cbs: Dict[str, Tuple[ContextManager, Callable]]= {}
        self._data: Dict[str, T] = {}
        self._bc: BookContainer = bc

    @contextmanager
    def _cm(self, fid: str, bc: BookContainer, /) -> Generator[T, None, None]:
        with type(self).__context_factory__(fid, bc) as data:
            yield data
            if fid in self._data:
                raise WriteBack(self._data[fid])
            else:
                raise DoNotWriteBack

    @property
    def data(self) -> MappingProxyType:
        """A dictionary as a set of [file's manifest id]: [file data object] pairs."""
        return MappingProxyType(self._data)

    @property
    def bookcontainer(self) -> BookContainer:
        """Internal `BookContainer` object. 
        `BookContainer` object is an object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
        """
        return self._bc

    bc = bk = bookcontainer

    def __contains__(self, fid):
        "Determine whether `fid` is an available manifest id."
        return fid in self._bc._w.id_to_mime

    def __len__(self) -> int:
        """Count of all available [files" manifest ids]."""
        return len(self._bc._w.id_to_mime)

    def __iter__(self) -> Iterator[str]:
        """Iterate over all available [files" manifest ids] 
        (roughly from `bookcontainer.Bookcontainer.manifest_iter`)."""
        yield from self._bc._w.id_to_mime

    def iteritems(self) -> Iterator[Tuple[str, T]]:
        """Iterate over all files (manifest ids are offered by `__iter__` method), 
        and yield a tuple of [file's manifest id] and [file data object] 
        (this will cause the file to be opened) at each time"""
        for fid in self:
            yield fid, self[fid]

    def itervalues(self) -> Iterator[T]:
        """Iterate over all files (manifest ids are offered by `__iter__` method), 
        and yield [file data object] (this will cause the file to be opened) 
        at each time"""
        for fid in self:
            yield self[fid]

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        "Write all opened files back, and clear the `EditCache` object."
        try:
            received_exc = exc_info[0] is not None

            # We manipulate the exception state so it behaves as though
            # we were actually nesting multiple with statements
            frame_exc = sys.exc_info()[1]
            def _fix_exception_context(new_exc, old_exc):
                # Context may not be correct, so find the end of the chain
                while True:
                    exc_context = new_exc.__context__
                    if exc_context is old_exc:
                        # Context is already set correctly (see issue 20317)
                        return
                    if exc_context is None or exc_context is frame_exc:
                        break
                    new_exc = exc_context
                # Change the end of the chain to point to the exception
                # we expect it to reference
                new_exc.__context__ = old_exc

            # Callbacks are invoked in LIFO order to match the behaviour of
            # nested context managers
            suppressed_exc = False
            pending_raise = False
            for cm, cm_exit in self._exit_cbs.values():
                try:
                    if cm_exit(cm, *exc_info):
                        suppressed_exc = True
                        pending_raise = False
                        exc_info = (None, None, None)
                except:
                    new_exc_info = sys.exc_info()
                    # simulate the stack of exceptions by setting the context
                    _fix_exception_context(new_exc_info[1], exc_info[1])
                    pending_raise = True
                    exc_info = new_exc_info
            if pending_raise:
                # bare "raise exc_info[1]" replaces our carefully set-up context
                fixed_ctx = exc_info[1].__context__
                try:
                    raise exc_info[1]
                except BaseException:
                    exc_info[1].__context__ = fixed_ctx
                    raise
            return received_exc and suppressed_exc
        finally:
            self._data.clear()
            self._exit_cbs.clear()

    def clear(self) -> None:
        "Write all opened files back, and clear the `EditCache` object."
        self.__exit__(*sys.exc_info())

    __del__ = clear

    def __getitem__(self, fid) -> T:
        """Receive a file's manifest id `fid`, return the corresponding 
        of the file data object, otherwise raise `KeyError`."""
        data = self._data
        if fid not in data:
            try:
                cm = type(self)._cm(self, fid, self._bc)
                cm_type = type(cm)
                data[fid] = cm_type.__enter__(cm) # type: ignore
                self._exit_cbs[fid] = (cm, cm_type.__exit__)
            except Exception as exc:
                raise KeyError(fid) from exc
        return data[fid]

    def __setitem__(self, fid, data) -> None:
        """Update the data of the corresponding manifest id `fid` to `data`.
        There are 2 restrictions:
            1. The manifest id `fid` must be available, otherwise raise `KeyError`.
            2. The data type of `data` must the same as original data, 
               otherwise raise `TypeError`.
        """
        original_type = type(self._data[fid])
        data_type = type(data)
        if original_type is not data_type:
            raise TypeError(
                "The data type does not match. It must be the same as the data type of "
                "the original data, expected %r, got %r." % (original_type, data_type))
        self._data[fid] = data

    def __delitem__(self, fid) -> None:
        """If the manifest id `fid` available and the corresponding data were modified, 
        then clear the modified data."""
        if fid in self._data:
            del self._data[fid]
            cm, cm_exit = self._exit_cbs.pop(fid)
            try:
                raise DoNotWriteBack
            except:
                cm_exit(cm, *sys.exc_info())


    def read_id(self, key) -> T:
        """Receive a file's manifest id, return the content of the file, 
        otherwise raise `KeyError`."""
        return self[key]

    def read_href(self, key) -> T:
        """Receive a file's OPF href, return the content of the file, 
        otherwise raise `KeyError`"""
        try:
            return self[self._bc.href_to_id(key)]
        except Exception as exc:
            raise KeyError(key) from exc

    def read_basename(self, key) -> T:
        """Receive a file's basename (with extension), return the 
        content of the file, otherwise raise `KeyError`"""
        try:
            return self[self._bc.basename_to_id(key)]
        except Exception as exc:
            raise KeyError(key) from exc

    def read_bookpath(self, key) -> T:
        """Receive a file's bookpath (aka "book_href" aka "bookhref"), 
        return the content of the file, otherwise raise `KeyError`"""
        try:
            return self[self._bc.bookpath_to_id(key)]
        except Exception as exc:
            raise KeyError(key) from exc


class TextEditCache(EditCache[T]):
    """Initialize an `TextEditCache` object that can proxy accessing to 
    `bookcontainer.Bookcontainer` object.
    The edited files" data of this `TextEditCache` object are cached and not immediately 
    written back to the `bookcontainer.Bookcontainer` object, until the `__exit__` 
    method or the `clear` method are called, and then this `TextEditCache` object is cleared.

    **NOTE**: This can operate all the text (HTML / XHTML only) files declared 
          in the OPF file in ePub.

    **NOTE**: A manifest id is available or not, can be determined by `__contains__` method.

    **NOTE**: If you need to directly operate on the corresponding `bookcontainer.Bookcontainer` object (e.g., delete a file), please clear this editcache first.

    :param bc: `BookContainer` object. 
        If it is None (the default), will be found in caller's globals().
        `BookContainer` object is an object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.

    :Examples:

        .. code-block:: python

            # Delete the first <title> element that appears in each (X)HTML etree
            with TextEditCache(bc) as cache:
                for fid, tree in cache.iteritems():
                    el_title = tree.find(".//title")
                    if el_title is not None:
                        el_title.getparent().remove(el_title)
    """
    __context_factory__: Callable[[str, BookContainer], ContextManager] = ctx_edit_html

    def __contains__(self, fid):
        "Determine whether `fid` is an available manifest id."
        return fid in iter(self)

    def __len__(self) -> int:
        """Count of all available [files" manifest ids] (HTML / XHTML only)."""
        return sum(1 for _ in self._bc.text_iter())

    def __iter__(self) -> Iterator[str]:
        """Iterate over all available [files" manifest ids] (HTML / XHTML only)
        (from `bookcontainer.Bookcontainer.text_iter`)."""
        for fid, *_ in self._bc.text_iter():
            yield fid

