#!/usr/bin/env python
# coding: utf-8

"""
Simple lightweight HTML / XHTML parser with XPath support.

Fork From: https://github.com/willforde/python-htmlement

Reference:
    - https://python-htmlement.readthedocs.io/en/stable/
    - https://pypi.org/project/htmlement/
    - https://github.com/marmelo/python-htmlparser
"""

from __future__ import annotations

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)
__all__ = ['ElementTree', 'Element', 'HTMLParser', 'make_element', 
           'make_html_element', 'parse', 'fromstring', 'fromstringlist', 
           'tostring', 'xml_fromstring', 'xml_tostring', 'html_fromstring', 
           'html_tostring', ]

import re
import warnings

from html.parser import HTMLParser as _HTMLParser
from html.entities import name2codepoint
from os import PathLike
from typing import (
    cast, Any, BinaryIO, Dict, List, Optional, Tuple, 
    Sequence, TextIO, Union, 
)
from xml.etree.ElementTree import (
    fromstring as xml_fromstring, tostring as xml_tostring, 
    Comment, Element as _Element, ElementTree as _ElementTree
)


# Add missing codepoints
name2codepoint["apos"] = 0x0027

PathType = Union[str, bytes, PathLike]
HandledAttrType = List[Tuple[str, Optional[str]]]


def _ensure_bytes(o: Any) -> bytes:
    'Ensure the return value is `bytes` type'
    if isinstance(o, bytes):
        return o
    elif isinstance(o, str):
        return bytes(o, encoding='utf-8')
    else:
        return bytes(o)


class ElementTree(_ElementTree):

    _root: Optional[Element]   = None
    doctype: Optional[str]     = None
    encoding: Optional[str]    = None
    xmlinfo: Optional[Element] = None
    raw: str                   = ''


class Element(_Element):
    '''Element class. This class defines the Element interface, 
    and provides a reference implementation of this interface.

    :param tag: The element name. 
    :param attrib: An optional dictionary, containing element attributes. 
    :param extra: Contains additional attributes, given as keyword arguments.

    The element name, attribute names, and attribute values can be 
    either bytestrings or Unicode strings.
    '''

    def __init__(self, tag, attrib: Optional[dict]=None, **extra) -> None:
        if attrib is None:
            attrib = {}
        super().__init__(tag, attrib, **extra)

    _roottree = None

    @property
    def roottree(self) -> Optional[ElementTree]:
        return self._roottree

    @roottree.setter
    def roottree(self, elementtree: ElementTree):
        self._roottree = elementtree

    def getroottree(self) -> Optional[ElementTree]:
        return self._roottree


class HTMLParser(_HTMLParser):
    """
    Python HTMLParser extension with ElementTree Parser support.

    This HTML Parser extends :class:`html.parser.HTMLParser`, 
        returning an :class:`xml.etree.ElementTree.Element` instance. 
        The returned root element natively supports the ElementTree API.
        (e.g. you may use its limited support for `XPath expressions`)
        [XPath](https://docs.python.org/3/library/xml.etree.elementtree.html#xpath-support)

    When a "tag" and "tag attributes" are given, the parser will search for a required section. 
        Only when the required section is found, does the parser start parsing the "HTML document". 
        The element that matches the search criteria will then become the new "root element".

    Attributes are given as a dict of {'name': 'value'}. Value can be the string to match, `True` or `False.`
        `True` will match any attribute with given name and any value.
        `False` will only give a match if given attribute does not exist in the element.

    :param tag: (optional) Name of "tag / element" which is used to filter down "the tree" to a required section.
    :param attrib: (optional) The attributes of the element, that will be used, when searchingfor the required section.
    :param encoding: (optional) Encoding used, when decoding the source data before feeding it to the parser.
    """
    def __init__(
        self, 
        tag: str = '', 
        attrs: Optional[Dict[str, str]] = None, 
        encoding: Optional[str] = None,
    ) -> None:
        # Initiate HTMLParser
        super().__init__()
        self.tag: str = tag
        self.attrs: Dict[str, str]
        self.encoding: Optional[str] = encoding
        self._init_attrs: Dict[str, str] = {} if attrs is None else attrs

        # Some tags in html do not require closing tags so thoes tags will need to be auto closed (Void elements)
        # Refer to: https://www.w3.org/TR/html/syntax.html#void-elements
        self._voids = frozenset(("area", "base", "br", "col", "hr", "img", "input", "link", "meta", "param",
                                 # Only in HTML5
                                 "embed", "keygen", "source", "track",
                                 # Not supported in HTML5
                                 "basefont", "frame", "isindex",
                                 # SVG self closing tags
                                 "rect", "circle", "ellipse", "line", "polyline", "polygon",
                                 "path", "stop", "use", "image", "animatetransform"))

        self._init()

    def _init(self) -> None:
        self._root: Optional[Element] = None  # root element
        self._data: list = []  # data collector
        self._enabled: bool = not self.tag # top level tag flag
        self._unw_attrs: list = []
        self._finished: bool = False
        self._roottree: ElementTree = ElementTree(None)
        self._roottree.encoding = self.encoding
        self._doctype: Optional[str] = None
        self._xmlinfo: Optional[Element] = None

        attrs = self.attrs = self._init_attrs.copy()
        # Split attributes into wanted and unwanted attributes
        if attrs:
            for key, value in self._init_attrs.items():
                if value == 0:
                    self._unw_attrs.append(key)
                    del attrs[key]

        # Create temporary root element to protect from badly written sites that either
        # have no html starting tag or multiple top level elements
        elem: Element = Element("html")
        elem.roottree = self._roottree
        self._elem: List[Element] = [elem]
        self._last: Element = elem
        self._tail: int = 0

    def _make_unicode(
        self, 
        data: bytes, 
        _cre=re.compile(b'<meta.+?charset=[\'"]*(.+?)["\'].*?>', re.IGNORECASE), 
    ) -> str:
        """
        Convert *data* from type :class:`bytes` to type :class:`str`.

        :param data: The html document.
        :type data: bytes

        :return: HTML data decoded.
        :rtype: str
        """
        # Atemp to find the encoding from the html source
        if self._xmlinfo and self._xmlinfo.attrib.get('encoding'):
            self._roottree.encoding = self.encoding = cast(str, self._xmlinfo.attrib['encoding'])
            return data.decode(self.encoding)
        end_head_tag = data.find(b"</head>")
        if end_head_tag:
            # Search for the charset attribute within the meta tags
            charset = _cre.search(data[:end_head_tag])
            if charset:
                self._roottree.encoding = self.encoding = cast(str, charset.group(1).decode())
                return data.decode(self.encoding)

        # Decode the string into unicode using default encoding
        warn_msg = "Unable to determine encoding, defaulting to iso-8859-1"
        warnings.warn(warn_msg, UnicodeWarning, stacklevel=2)
        self.encoding = "iso-8859-1"
        return data.decode("iso-8859-1")

    def feed(self, data: Union[bytes, str]) -> None:
        """
        Feeds data to the parser.

        If *data*, is of type :class:`bytes` and where no encoding was specified, then the encoding
        will be extracted from *data* using "meta tags", if available.
        Otherwise encoding will default to "ISO-8859-1"

        :param data: HTML data
        :type data: str or bytes

        :raises UnicodeDecodeError: If decoding of *data* fails.
        """
        # Skip feeding data into parser if we already have what we want
        if self._finished == 1:
            return None

        # Make sure that we have unicode before continuing
        if isinstance(data, bytes):
            if self.encoding:
                data = data.decode(self.encoding)
            else:
                data = self._make_unicode(data)

        # Parse the html document
        try:
            super().feed(data)
        except EOFError:
            self._finished = True
            self.reset()

    def handle_decl(self, decl):
        if self._root is not None:
            raise RuntimeError
        elif self._doctype is not None:
            raise RuntimeError
        self._roottree.doctype = self._doctype = '<!%s>' % decl

    def handle_pi(self, data):
        pi_ = xml_fromstring('<' + data.rstrip('?') + '/>')
        if pi_.tag == 'xml':
            if self._root is not None:
                raise RuntimeError
            elif self._xmlinfo is not None:
                raise RuntimeError
            pi = Element('?xml', attrib=pi_.attrib)
            pi.raw = '<?%s>' % data
            self._roottree.xmlinfo = self._xmlinfo = pi

    def handle_starttag(self, tag: str, attrs: HandledAttrType) -> None:
        self._handle_starttag(tag, attrs, self_closing=tag in self._voids)

    def handle_startendtag(self, tag: str, attrs: HandledAttrType) -> None:
        self._handle_starttag(tag, attrs, self_closing=True)

    def _handle_starttag(
        self, 
        tag: str, 
        attrs: HandledAttrType, 
        self_closing: bool = False, 
    ) -> None:
        # Add tag element to tree if we have no filter or that the filter matches
        if self._enabled or self._search(tag, attrs):
            # Convert attrs to dictionary
            attrs_: dict = dict(attrs) if attrs else {}
            self._flush()

            # Create the new element
            elem = Element(tag, attrs_)
            elem.roottree = self._roottree
            self._elem[-1].append(elem)
            self._last = elem

            # Only append the element to the list of elements if it's not a self closing element
            if self_closing:
                self._tail = 1
            else:
                self._elem.append(elem)
                self._tail = 0

            # Set this element as the root element when the filter search matches
            if not self._enabled:
                self._root = elem
                self._enabled = True

    def handle_endtag(self, tag: str) -> None:
        # Only process end tags when we have no filter or that the filter has been matched
        if self._enabled and tag not in self._voids:
            _elem = self._elem
            _root = self._root
            # Check that the closing tag is what's actualy expected
            if _elem[-1].tag == tag:
                self._flush()
                self._tail = 1
                self._last = elem = _elem.pop()
                if elem is _root:
                    raise EOFError

            # If the previous element is what we actually have then the expected element was not
            # properly closed so we must close that before closing what we have now
            elif len(_elem) >= 2 and _elem[-2].tag == tag:
                self._flush()
                self._tail = 1
                for _ in range(2):
                    self._last = elem = _elem.pop()
                    if elem is _root:
                        raise EOFError
            else:
                # Unable to match the tag to an element, ignoring it
                return None

    def handle_data(self, data) -> None:
        if self._enabled:
            self._data.append(data)

    def handle_entityref(self, name) -> None:
        if self._enabled:
            try:
                name = chr(name2codepoint[name])
            except KeyError:
                pass
            self._data.append(name)

    def handle_charref(self, name) -> None:
        if self._enabled:
            try:
                if name[0].lower() == "x":
                    name = chr(int(name[1:], 16))
                else:
                    name = chr(int(name))
            except ValueError:
                pass
            self._data.append(name)

    def handle_comment(self, data) -> None:
        data = data.strip()
        if data and self._enabled:
            elem = Comment(data)
            self._elem[-1].append(elem)

    def _close(self) -> Optional[Element]:
        self._flush()
        if self._enabled == 0:
            msg = "Unable to find requested section with tag of '{}' and attributes of {}"
            raise RuntimeError(msg.format(self.tag, self.attrs))
        elif self._root is not None:
            self._roottree._root = self._root
            return self._root
        else:
            # Search the root element to find a proper html root element if one exists
            tmp_root: Element = self._elem[0]
            proper_root = cast(Element, tmp_root.find("html"))
            if proper_root is None:
                # Not proper root was found
                self._roottree._root = tmp_root
                return tmp_root
            else:
                # Proper root found
                self._roottree._root = proper_root
                return proper_root

    def close(self) -> Optional[Element]: # type: ignore
        try:
            return self._close()
        finally:
            self._init()

    def _flush(self) -> None:
        if self._data:
            if self._last is not None:
                text = "".join(self._data)
                if self._tail:
                    self._last.tail = text
                else:
                    self._last.text = text
            self._data = []

    def _search(self, tag: str, attrs: HandledAttrType) -> bool:
        # Only search when the tag matches
        if tag == self.tag:
            # If we have required attrs to match then search all attrs for wanted attrs
            # And also check that we do not have any attrs that are unwanted
            if self.attrs or self._unw_attrs:
                if attrs:
                    wanted_attrs = self.attrs.copy()
                    unwanted_attrs = self._unw_attrs
                    for key, value in attrs:
                        # Check for unwanted attrs
                        if key in unwanted_attrs:
                            return False

                        # Check for wanted attrs
                        elif key in wanted_attrs:
                            c_value = wanted_attrs[key]
                            if c_value == value or c_value == 1:
                                # Remove this attribute from the wanted dict of attributes
                                # to indicate that this attribute has been found
                                del wanted_attrs[key]

                    # If wanted_attrs is now empty then all attributes must have been found
                    if not wanted_attrs:
                        return True
            else:
                # We only need to match tag
                return True

        # Unable to find required section
        return False


def make_element(
    tag: str, 
    attrib: Optional[dict] = None, 
    children: Optional[List[Element]] = None, 
    text: Optional[str] = '', 
    tail: Optional[str] = None, 
    **extra,
) -> _Element:
    '''Make an `xml.etree.ElementTree.Element` object.

    :param tag: A string identifying what kind of data this element represents 
                (the element type, in other words).
    :param attrib: A dictionary containing the element’s attributes.
    :param children: A list containing the element’s subelements.
    :param text: Used to hold additional data associated with the element.
        The text attribute holds either the text between the element’s start tag 
        and its first child or end tag, or None.
    :param tail: Used to hold additional data associated with the element.
        The tail attribute holds either the text between the element’s end tag 
        and the next tag, or None.
    :param extra: Keyword arguments passed to the constructor of `Element`.

    :return: An `xml.etree.ElementTree.Element` instance.
    '''
    if attrib is not None:
        extra['extra'] = attrib
    el = _Element(tag, **extra)
    if children is not None:
        el.extend(children)
    if text is not None:
        el.text = text
    if tail is not None:
        el.tail = tail
    return el


def make_html_element(
    tag: str, 
    attrib: Optional[dict] = None, 
    children: Optional[List[Element]] = None, 
    text: Optional[str] = '', 
    tail: Optional[str] = None, 
    **extra,
) -> Element:
    '''Make an `Element` object.

    :param tag: A string identifying what kind of data this element represents 
                (the element type, in other words).
    :param attrib: A dictionary containing the element’s attributes.
    :param children: A list containing the element’s subelements.
    :param text: Used to hold additional data associated with the element.
        The text attribute holds either the text between the element’s start tag 
        and its first child or end tag, or None.
    :param tail: Used to hold additional data associated with the element.
        The tail attribute holds either the text between the element’s end tag 
        and the next tag, or None.
    :param extra: Keyword arguments passed to the constructor of `Element`.

    :return: An `Element` instance.
    '''
    if attrib is not None:
        extra['extra'] = attrib
    el = Element(tag, **extra)
    if children is not None:
        el.extend(children)
    if text is not None:
        el.text = text
    if tail is not None:
        el.tail = tail
    return el


def parse(
    source: Union[PathType, BinaryIO, TextIO], 
    parser=None, 
    encoding: Optional[str] = None, 
) -> Element:
    """
    Load an external "HTML / XHTML document" into an element tree.

    :param source: A filename or file-like object containing HTML / XHTML data.
    :param parser: Optional parser instance defaulting to HTMLParser.
    :param encoding: (optional) Encoding used, when decoding the source data 
                     before feeding it to the parser.

    :return: The root element of the element tree.
    :raises UnicodeDecodeError: If decoding of *source* fails.
    """
    # Assume that source is a file-like object if the 'read' methods is found
    if hasattr(source, 'read'):
        source = cast(Union[BinaryIO, TextIO], source)
    else:
        source = cast(PathLike, source)
        source = cast(BinaryIO, open(source, 'rb', encoding=encoding))

    if parser is None:
        parser = HTMLParser()

    # Read in 64k at a time
    data: Union[bytes, str]
    while (data := source.read(65536)):
        # Feed the parser
        parser.feed(data)

    # Return the root element
    return parser.close()


def fromstring(text, parser=None) -> Element:
    """
    Parse HTML document from a string into an element tree.

    :param text: A string containing HTML / XHTML data to parse.
    :param parser: Optional parser instance defaulting to HTMLParser.

    :return: The root element of the element tree.
    :raises UnicodeDecodeError: If decoding of *text* fails.
    """
    if parser is None:
        parser = HTMLParser()
    parser.feed(text)
    return parser.close()


def fromstringlist(
    sequence: Sequence[Union[str, bytes]], 
    parser=None, 
) -> Element:
    """
    Parses a "HTML / XHTML document" from a sequence of "HTML / XHTML sections" 
    into an element tree.

    :param sequence: A sequence of "HTML / XHTML sections" to parse.
    :param parser: Optional parser instance defaulting to HTMLParser.

    :return: The root element of the element tree.
    :raises UnicodeDecodeError: If decoding of a section within *sequence* fails.
    """
    if parser is None:
        parser = HTMLParser()
    for text in sequence:
        parser.feed(text)
    return parser.close()


def html_fromstring(
    text: Union[str, bytes] = '', 
    parser=None, 
    full: bool = True,
) -> Element:
    """
    Parse HTML document from a string into an element tree.

    :param text: A string containing HTML / XHTML data to parse.
    :param parser: Optional parser instance defaulting to HTMLParser.
    :param full: Determine whether to ensure that the top level element <html> 
                 has child elements <head> and <body>.

    :return: The root element of the element tree.
    :raises UnicodeDecodeError: If decoding of *text* fails.
    """
    if not text.strip():
        text = b'''<html>
    <head>
        <meta charset="utf-8" />
    </head>
    <body/>
</html>'''

    element = fromstring(text, parser=parser)
    if full and element.tag.lower() == 'html':
        if element.find('head') is None:
            element.insert(0, make_element('head', tail='\n'))
        if element.find('body') is None:
            element.append(make_element('body', tail='\n'))
    return element


def tostring(
    element: Union[Element, ElementTree], 
    encoding: Optional[str] = None, 
    method: str = 'html',
    full: bool = True,
    *,
    xml_declaration=None,
    default_namespace=None,
    short_empty_elements=True,
) -> Union[bytes, str]:
    """Generate string representation of HTML / XHTML element.

    :param element: An `Element` or `ElementTree` instance.
    :param encoding: The optional output encoding.
        Note that you can pass the value 'unicode' as `encoding` argument 
        to serialise to a Unicode string.
    :param method: Either "html"(default), "xml", "xhtml", "text", or "c14n".
    :param full: If True, it will generate from the root element, 
        else generate from the specified element.
    :param xml_declaration: 
        Determine whether an XML declaration should be added to the output. 
        If None(default), an XML declaration is added if method IS NOT "html".
    :param default_namespace: Sets the default XML namespace (for "xmlns").
    :param short_empty_elements: 
        Controls the formatting of elements that contain no content. 
        If True (default) they are emitted as a single self-closed
        tag, otherwise they are emitted as a pair of start/end tags.

    :return: An (optionally) encoded string containing the XML data.
    """
    if not full or method not in ('xml', 'html', 'xhtml'):
        if method == 'xhtml':
            method = 'xml'
        if isinstance(element, ElementTree):
            element = cast(Element, element.getroot())
        return xml_tostring(
            element, encoding=encoding, method=method, 
            xml_declaration=xml_declaration,
            default_namespace=default_namespace,
            short_empty_elements=short_empty_elements)

    roottree = cast(ElementTree, element.getroottree() 
                    if isinstance(element, Element) else element)
    root: Element = cast(Element, roottree.getroot())
    doctype: Union[None, bytes, str] = roottree.doctype
    xmlinfo = roottree.xmlinfo
    if xmlinfo is None:
        xmlattrib = {}
    else:
        xmlattrib = xmlinfo.attrib.copy()
    encoding = cast(str, encoding or roottree.encoding or 'UTF-8')
    to_unicode: bool = encoding.lower() == 'unicode'

    if 'version' not in xmlattrib:
        xmlattrib['version'] = "1.0"
    if 'encoding' not in xmlattrib:
        xmlattrib['encoding'] = 'UTF-8' if to_unicode else encoding

    parts: list = []
    if to_unicode:
        if not doctype:
            if method == 'html':
                doctype = '<!DOCTYPE html>'
            elif method == 'xhtml':
                doctype = ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" '
                           '"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">')

        if method == 'xhtml':
            method = 'xml'

        if xml_declaration or (xml_declaration is None and method == 'xml'):
            parts.append('<?xml %s?>' % ' '.join(
                '%s="%s"' % (k, v.replace('"', '&quot;')) 
                for k, v in xmlattrib.items()
            ))
        if doctype:
            parts.append(doctype)
        parts.append(xml_tostring(
            root, encoding='unicode', method=method, 
            xml_declaration=False,
            default_namespace=default_namespace,
            short_empty_elements=short_empty_elements))

        return '\n'.join(parts)
    else:
        if not doctype:
            if method == 'html':
                doctype = b'<!DOCTYPE html>'
            elif method == 'xhtml':
                doctype = (b'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" '
                           b'"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">')

        if method == 'xhtml':
            method = 'xml'

        if xml_declaration or (xml_declaration is None and method == 'xml'):
            parts.append(b'<?xml %s?>' % b' '.join(
                b'%s="%s"' % (
                    _ensure_bytes(k), 
                    _ensure_bytes(v).replace(b'"', b'&quot;')
                ) for k, v in xmlattrib.items()
            ))
        if doctype:
            parts.append(_ensure_bytes(doctype))
        parts.append(xml_tostring(
            root, encoding=encoding, method=method, 
            xml_declaration=False,
            default_namespace=default_namespace,
            short_empty_elements=short_empty_elements))

        return b'\n'.join(parts)

html_tostring = tostring

