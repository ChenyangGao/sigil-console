#!/usr/bin/env python
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)
__all__ = ['make_element', 'make_html_element', 'xml_fromstring', 'xml_tostring', 
           'html_fromstring', 'html_tostring']

from typing import (
    cast, Any, Final, List, Mapping, Optional, Union, 
)

from lxml.etree import ( # type: ignore
    fromstring as xml_fromstring, tostring as _xml_tostring, 
    _Element, _ElementTree, Element, XPath, 
)
from lxml.html import ( # type: ignore
    fromstring as _html_fromstring, tostring as _html_tostring, 
    Element as HTMLElement, HtmlElement, HTMLParser, 
)


def _ensure_bytes(o: Any) -> bytes:
    'Ensure the return value is `bytes` type'
    if isinstance(o, bytes):
        return o
    elif isinstance(o, str):
        return bytes(o, encoding='utf-8')
    else:
        return bytes(o)


def make_element(
    tag: str, 
    attrib: Optional[Mapping] = None, 
    children: Optional[List[HtmlElement]] = None, 
    text: Optional[str] = '', 
    tail: Optional[str] = None, 
    nsmap: Optional[Mapping] = None, 
    **extra,
) -> _Element:
    '''Make a `lxml.etree._Element` object.

    Tips: Please read the following documentation(s) for details
        - lxml.etree.Element
        - lxml.html._Element

    :param tag: The tag name, possibly containing a namespace 
                in Clark notation.
    :param attrib: A dictionary containing the element’s attributes.
    :param children: A list containing the element’s subelements.
    :param text: Used to hold additional data associated with the element.
        The text attribute holds either the text between the element’s start tag 
        and its first child or end tag, or None.
    :param tail: Used to hold additional data associated with the element.
        The tail attribute holds either the text between the element’s end tag 
        and the next tag, or None.
    :param nsmap: The default namespace URI, unless provided as part
                  of the TAG attribute.
    :param extra: Keyword arguments passed to the constructor of `Element`.

    :return: An `lxml.etree._Element` instance.
    '''
    el = Element(tag, attrib=attrib, nsmap=nsmap, **extra)
    if text is not None:
        el.text = text
    if children is not None:
        el.extend(children)
    if tail is not None:
        el.tail = tail
    return el


def make_html_element(
    tag: str, 
    attrib: Optional[Mapping] = None, 
    children: Optional[List[HtmlElement]] = None, 
    text: Optional[str] = '', 
    tail: Optional[str] = None, 
    nsmap: Optional[Mapping] = None, 
    **extra, 
) -> HtmlElement:
    '''Make a `lxml.html.HtmlElement` object.

    Tips: Please read the following documentation(s) for details
        - lxml.etree.Element
        - lxml.html.HtmlElement

    :param tag: The tag name, possibly containing a namespace 
                in Clark notation.
    :param attrib: A dictionary containing the element’s attributes.
    :param children: A list containing the element’s subelements.
    :param text: Used to hold additional data associated with the element.
        The text attribute holds either the text between the element’s start tag 
        and its first child or end tag, or None.
    :param tail: Used to hold additional data associated with the element.
        The tail attribute holds either the text between the element’s end tag 
        and the next tag, or None.
    :param nsmap: The default namespace URI, unless provided as part
                  of the TAG attribute.
    :param extra: Keyword arguments passed to the constructor of `Element`.

    :return: An `lxml.html.HtmlElement` instance.
    '''
    el = HTMLElement(tag, attrib=attrib, nsmap=nsmap, **extra)
    if text is not None:
        el.text = text
    if children is not None:
        el.extend(children)
    if tail is not None:
        el.tail = tail
    return el


def xml_tostring(
    element: Union[_Element, _ElementTree], 
    encoding: Optional[str] = None, 
    method: str = 'xml', 
    **kwds, 
) -> Union[bytes, str]:
    '''Convert a root element node to string by using 
    `lxml.etree.tostring` function

    Tips: Please read the following documentation(s) for details
        - lxml.etree.tostring

    :param element: A `lxml.etree._Element` or `lxml.etree._ElementTree` instance.
    :param encoding: The optional output encoding.
        Note that you can pass the value 'unicode' as `encoding` argument 
        to serialise to a Unicode string.
    :param method: The argument 'method' selects the output method: 'xml'(default),
        'html', plain 'text' (text content without tags), 'c14n' or 'c14n2'.
        With `method="c14n"` (C14N version 1), the options `exclusive`,
        `with_comments` and `inclusive_ns_prefixes` request exclusive
        C14N, include comments, and list the inclusive prefixes respectively.
        With `method="c14n2"` (C14N version 2), the `with_comments` and
        `strip_text` options control the output of comments and text space
        according to C14N 2.0.
    :param kwds: Keyword arguments `kwds` will be passed to 
        `lxml.etree.tostring` function.

    :return: An XML string representation of the document.
    '''
    if method not in ('xml', 'html'):
        return _xml_tostring(element, encoding=encoding, method=method, **kwds)

    roottree = cast(_ElementTree, element.getroottree() 
                    if isinstance(element, _Element) else element)
    docinfo = roottree.docinfo
    encoding = cast(str, encoding or docinfo.encoding or 'UTF-8')
    to_unicode: bool = encoding.lower() == 'unicode'

    if to_unicode:
        string = _xml_tostring(roottree, encoding=encoding, method=method, **kwds)
        if method == 'xml':
            string = '<?xml version="%s" encoding="%s"?>\n' % (
                docinfo.xml_version or '1.0', encoding,
            ) + string
        return string
    else:
        string = _xml_tostring(roottree, encoding=encoding, method=method, **kwds)
        if method == 'xml':
            string = b'<?xml version="%s" encoding="%s"?>\n'% (
                _ensure_bytes(docinfo.xml_version or b'1.0'),
                _ensure_bytes(encoding),
            ) + string
        return string


def html_fromstring(
    text: Union[str, bytes] = '', 
    parser = None, 
    **kwds, 
) -> _Element:
    '''Convert a string to `lxml.etree._Element` object by using 
    `lxml.html.fromstring` function.

    Tips: Please read the following documentation(s) for details
        - lxml.html.fromstring
        - lxml.etree.fromstring
        - lxml.html.HTMLParser

    :params text: A string containing HTML / XHTML data to parse.
    :params parser: `parser` allows reading HTML into a normal XML tree, 
        this argument will be passed to `lxml.html.fromstring` function.
    :params kwds: Keyword arguments will be passed to 
        `lxml.html.fromstring` function.

    :return: The root element of the element tree.
    '''
    if parser is None:
        parser = HTMLParser(default_doctype=False)
    if not text.strip():
        return _html_fromstring(
b'''<html>
    <head/>
    <body/>
</html>''', parser=parser, **kwds)
    tree = _html_fromstring(text, parser=parser, **kwds)
    # get root element
    for tree in tree.iterancestors(): 
        pass
    if tree.tag.lower() == 'html':
        if tree.find('head') is None:
            tree.insert(0, make_html_element('head', tail='\n'))
        if tree.find('body') is None:
            tree.append(make_html_element('body', tail='\n'))
    return tree


def html_tostring(
    element: Union[_Element, _ElementTree], 
    encoding: Optional[str] = None, 
    method: str = 'html', 
    full: bool = True, 
    **kwds, 
) -> Union[bytes, str]:
    '''Convert a root element node to string by using 
    `lxml.html.tostring` function.

    Tips: Please read the following documentation(s) for details
        - lxml.html.tostring
        - lxml.etree.tostring

    :param element: A `lxml.etree._Element` or `lxml.etree._ElementTree` instance.
    :param encoding: The optional output encoding.
        Note that you can pass the value 'unicode' as `encoding` argument 
        to serialise to a Unicode string.
    :param method: The argument 'method' selects the output method: 'html'(default)
        'xml', 'xhtml', plain 'text' (text content without tags), 'c14n' or 'c14n2'.
        It defaults to 'html', but can also be 'xml' or 'xhtml' for xhtml output, 
        or 'text' to serialise to plain text without markup.
        With `method="c14n"` (C14N version 1), the options `exclusive`,
        `with_comments` and `inclusive_ns_prefixes` request exclusive
        C14N, include comments, and list the inclusive prefixes respectively.
        With `method="c14n2"` (C14N version 2), the `with_comments` and
        `strip_text` options control the output of comments and text space
        according to C14N 2.0.
    :param full: If True, it will generate from the root element, 
        else generate from the specified element.
    :param kwds: Keyword arguments `kwds` will be passed to 
        `lxml.html.tostring` function.

    :return: An string representation of the HTML / XHTML document.
    '''
    if not full or method not in ('xml', 'html', 'xhtml'):
        return _html_tostring(element, encoding=encoding, method=method, **kwds)

    roottree = cast(_ElementTree, element.getroottree() 
                    if isinstance(element, _Element) else element)
    root: _Element = roottree.getroot()
    docinfo = roottree.docinfo
    doctype = kwds.pop('doctype', docinfo.doctype)
    encoding = cast(str, encoding or docinfo.encoding or 'UTF-8')
    to_unicode: bool = encoding.lower() == 'unicode'

    if to_unicode:
        if not doctype:
            if method == 'html':
                doctype = '<!DOCTYPE html>'
            elif method == 'xhtml':
                doctype = ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" '
                           '"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">')

        if method == 'xhtml':
            method = 'xml'

        return (
            # However, to be honest, if it is an HTML file, 
            # it does not need to have a <?xml ?> header
            '<?xml version="%(xml_version)s" encoding="%(encoding)s"?>'
            '\n%(doctype)s\n%(doc)s'
        ) % {
            'xml_version': docinfo.xml_version or '1.0',
            'encoding': encoding,
            'doctype': doctype,
            'doc': _html_tostring(root, encoding=encoding, method=method, **kwds),
        }
    else:
        if not doctype:
            if method == 'html':
                doctype = b'<!DOCTYPE html>'
            elif method == 'xhtml':
                doctype = (b'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" '
                        b'"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">')

        if method == 'xhtml':
            method = 'xml'

        return (
            # However, to be honest, if it is an HTML file, 
            # it does not need to have a <?xml ?> header
            b'<?xml version="%(xml_version)s" encoding="%(encoding)s"?>'
            b'\n%(doctype)s\n%(doc)s'
        ) % {
            b'xml_version': _ensure_bytes(docinfo.xml_version or b'1.0'),
            b'encoding': _ensure_bytes(encoding),
            b'doctype': _ensure_bytes(doctype),
            b'doc': _html_tostring(root, encoding=encoding, method=method, **kwds),
        }

