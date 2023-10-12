#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)
__all__ = ['ElementTag', 'list_element_tags', 'text_remove_ranges']

from re import Match, Pattern, compile as re_compile
from dataclasses import dataclass
from tokenize import Name
from typing import Callable, Final, Iterable, Optional, Union


# 正则表达式：html/xml 标签名
PAT_QNAME: str = r'(?!\d)\w[\w-]*'
CRE_QNAME: Final[Pattern] = re_compile(PAT_QNAME)
# 正则表达式：html/xml 开始标签
CRE_OPEN: Final[Pattern] = re_compile(fr'<(?P<qname>{PAT_QNAME})[^>]*>(?<!/>)')
# 正则表达式：html/xml 结束标签
CRE_CLOSE : Final[Pattern]= re_compile(fr'</(?P<qname>{PAT_QNAME})>')
# 正则表达式：html/xml 自关闭标签
CRE_OPENCLOSE: Final[Pattern] = re_compile(fr'<(?P<qname>{PAT_QNAME})[^>]*>(?<=/>)')
# 正则表达式：html/xml 标签，正则表达式的匹配对象的.lastgroup属性可知类型：open, close, openclose
# 类型说明：open: 开始标签; close: 结束标签; openclose: 自关闭标签; 
CRE_TAG: Final[Pattern] = re_compile(
    fr'<(?P<_cl1>/)?(?P<qname>{PAT_QNAME})(?P<attrs>[^>]*)>(?P<_cl2>(?<=/>))?'
    r'(?(_cl1)(?P<close>)|(?(_cl2)(?P<openclose>)|(?P<open>)))'
)


class lazyproperty:

    def __init__(self, func):
        self.func = func

    def __get__(self, instance, type):
        if instance is None:
            return self
        value = self.func(instance)
        setattr(instance, self.func.__name__, value)
        return value


@dataclass
class ElementTag:
    '''元素标签，包含了标签名、原始文本、在元素文本中的索引等信息
    ----------------------------------------
    # 元素标签名
    tagname: str
    # 标签属性（如果需要拆分和解析，请自行解决）
    attributes: str
    # 元素标签所在的原始文本，一般是一个 html/xml/xhtml 文档
    text: str
    # 标签的开始标签的正则表达式匹配对象
    opentag_matchobj: typing.Optional[re.Match]
    # 标签的结束标签的正则表达式匹配对象
    # TIPS: 如果是自关闭标签(openclose)，opentag_matchobj 等同于 closetag_matchobj
    closetag_matchobj: typing.Optional[re.Match]
    ----------------------------------------
    # 是否自关闭标签
    is_openclose: bool
    # innerhtml的索引，从标签的开始标签的终止索引到结束标签的起始索引
    innerslice: slice
    # outerhtml的索引，从标签的开始标签的起始索引到结束标签的终止索引
    outerslice: slice
    # 等于text[innerslice]，也就是只有标签内部文本
    innerhtml: str
    # 等于text[outerslice]，也就是开始标签+标签内部文本+结束标签
    outerhtml: str
    # 开始标签的起始索引，等于 outer_start
    start: typing.Optional[int]
    # 结束标签的终止索引，等于 outer_stop
    stop: typing.Optional[int]
    # 开始标签的起始索引
    outer_start: typing.Optional[int]
    # 开始标签的结束索引
    inner_start: typing.Optional[int]
    # 结束标签的起始索引
    inner_stop: typing.Optional[int]
    # 结束标签的终止索引
    outer_stop: typing.Optional[int]
    '''
    tagname: str
    attributes: str = ''
    text: str = ''
    opentag_matchobj: Optional[Match] = None
    closetag_matchobj: Optional[Match] = None

    @property
    def is_openclose(self) -> bool:
        return self.opentag_matchobj is self.closetag_matchobj is not None

    @lazyproperty
    def innerslice(self) -> slice:
        return slice(self.inner_start, self.inner_stop)

    @lazyproperty
    def outerslice(self) -> slice:
        return slice(self.outer_start, self.outer_stop)

    @lazyproperty
    def innerhtml(self) -> str:
        return self.text[self.innerslice]

    @lazyproperty
    def outerhtml(self) -> str:
        return self.text[self.outerslice]

    @property
    def start(self) -> Optional[int]:
        return self.outer_start

    @property
    def stop(self) -> Optional[int]:
        return self.outer_stop

    @lazyproperty
    def outer_start(self) -> Optional[int]:
        m = self.opentag_matchobj
        return None if m is None else m.start()

    @lazyproperty
    def inner_start(self) -> Optional[int]:
        m = self.opentag_matchobj
        return None if m is None else m.end()

    @lazyproperty
    def inner_stop(self) -> Optional[int]:
        m = self.closetag_matchobj
        return None if m is None else m.start()

    @lazyproperty
    def outer_stop(self) -> Optional[int]:
        m = self.closetag_matchobj
        return None if m is None else m.end()

    @staticmethod
    def __len__() -> int:
        return 2

    def __getitem__(self, idx) -> Optional[int]:
        if idx == 0:
            return self.start
        elif idx == 1:
            return self.stop
        raise IndexError

    def __lt__(self, other) -> bool:
        if isinstance(other, ElementTag):
            if self.start is None:
                return True
            elif other.start is None:
                return False
            return self.start < other.start
        return NotImplemented

    def __repr__(self) -> str:
        return f'<{self.tagname}>@text[{self.start}:{self.stop}]'


def list_element_tags(
    text: str, 
    tags: Union[None, str, tuple[str, ...]] = None, 
    predicate: Optional[Callable[[ElementTag], bool]] = None, 
) -> list[ElementTag]:
    '''罗列 html/xml 文本中的元素标签

    :param text: html/xml 文本
    :param tags: 默认为 None，罗列所有元素标签。否则罗列特定的标签，不区分大小写，
        字符串: 一个或多个标签名，多个标签名可用|分隔
        字符串元组: 多个标签名
    :param predicate: 断言函数，默认为 None，即不作断言，被断言为 False 标签不会被收录

    :return: 所找出的元素标签的数组
    '''
    if tags is None:
        cre = CRE_TAG
    else:
        PAT_QNAME = '(?i:%s)' % tags if isinstance(tags, str) else '|'.join(tags)
        cre = re_compile(
            fr'<(?P<_cl1>/)?(?P<qname>{PAT_QNAME})(?P<attrs>[^>]*)>(?P<_cl2>(?<=/>))?'
            r'(?(_cl1)(?P<close>)|(?(_cl2)(?P<openclose>)|(?P<open>)))'
        )

    ls: list[ElementTag] = []
    append = ls.append
    cache_stack: list[ElementTag] = []
    push, pop = cache_stack.append, cache_stack.pop

    for m in cre.finditer(text):
        g = m.lastgroup
        if g == 'open':
            tag = ElementTag(
                tagname=m['qname'].lower(), 
                attributes=m['attrs'], 
                text=text, 
                opentag_matchobj=m, 
            )
            append(tag)
            push(tag)
        elif g == 'close':
            pop().closetag_matchobj = m
        elif g == 'openclose':
            append(ElementTag(
                tagname=m['qname'].lower(), 
                attributes=m['attrs'][:-1], 
                text=text, 
                opentag_matchobj=m, 
                closetag_matchobj=m, 
            ))

    if predicate:
        rm_idx_ls = [i for i, tag in enumerate(ls) if not predicate(tag)]
        if rm_idx_ls:
            rm = ls.pop
            for i in reversed(rm_idx_ls):
                rm(i)

    return ls


def text_remove_ranges(
    text: str, 
    ranges: Iterable, 
    is_sorted: bool = True, 
) -> str:
    '''把某个文本中，删除在一组的索引范围的文本，返回剩余部分

    :param text: 文本，可以处理任何文本，包括而不限于 html/xml/xhtml
    :param ranges: 一组索引范围，对于其中的每个索引范围r，r[0]是开始索引，r[1]是结束索引（不含），
                   这个索引范围r内的文本会被从`text`中删除
                   TIPS: 可以接受 list_element_tags 的返回值，会删除罗列出来的元素标签对应文本
    :param is_sorted: 这组索引范围`ranges`是不是有序的，如果不是有序的，会用`sorted`函数尝试排序

    :return: 删除一些索引范围内的文本后，剩余的文本
    '''
    if not is_sorted:
        ranges = sorted(ranges)
    ls: list[str] = []
    append = ls.append
    a = 0
    for b, d in ranges:
        if a < b:
            append(text[a:b])
        if a < d:
            a = d
    if a < len(text):
        append(text[a:])
    if not ls:
        return ''
    elif len(ls) == 1:
        return ls[0]
    return ''.join(ls)


try:
    from plugin_help.editor import edit_batch
except ModuleNotFoundError:
    pass
else:
    def ePub_remove_tags(
        tags: Union[None, str, tuple[str, ...]] = None, 
        predicate: Optional[Callable[[ElementTag], bool]] = None, 
        ids: Union[None, str, Iterable[str]] = None, 
        bc=globals().get('bc'), 
    ):
        '''批量删除指定 html/xhtml/xml 文件中的元素标签

        :param tags: 默认为 None，罗列所有元素标签。否则罗列特定的标签，不区分大小写，
            字符串: 一个或多个标签名，多个标签名可用|分隔
            字符串元组: 多个标签名
        :param predicate: 断言函数，默认为 None，即不作断言，被断言为 False 标签不会被删除
        :param ids: 一组待处理的文件的 id，默认用 bc.text_iter() 得到一组 id，
            这些 id 对应的文件会被处理
        :param bc: ePub 书籍编辑对象，由 Sigil 提供，你不需要传入

        :return: 处理结果的信息
        '''
        if bc is None:
            bc = __import__('sys')._getframe(1).f_globals['bc']
        if ids is None:
            ids = (fid for fid, *_ in bc.text_iter())
        return edit_batch(
            lambda text: text_remove_ranges(
                text, list_element_tags(text, tags, predicate)
            ), ids,
        )
    __all__.append('ePub_remove_tags')

