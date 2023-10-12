#!/usr/bin/env python
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)
__all__ = ['pinyincc', 'remove_ruby_pinyincc']

plugin.ensure_import('pypinyin') # type: ignore

from re import compile as re_compile, Pattern

from pypinyin import pinyin
from typing import Callable, Final, List, Optional, Union


bc = bc # type: ignore

CRE_TEXT_CONTENT: Final[Pattern] = re_compile('(?<=>)[^<]+')
CRE_RUBY_EL: Final[Pattern]  = re_compile('<ruby(?:\s[^>]*|)>((?s:.*?))</ruby>')
CRE_RP_EL: Final[Pattern]  = re_compile('<rp(?:\s[^>]*|)>(?s:.*?)</rp>')
CRE_RT_EL: Final[Pattern]  = re_compile('<rt(?:\s[^>]*|)>(?s:.*?)</rt>')
TPL1: Final[str] = '{char}<rt>{pinyin}</rt>'
TPL2: Final[str] = '{char}<rp>(</rp><rt>{pinyin}</rt><rp>)</rp>'


def with_pinyin(
    s: str, /, 
    get_pinyin: Union[
        Callable[..., List[str]], 
        Callable[..., List[List[str]]], 
    ] = pinyin, 
    wordcut: Optional[Callable[[str], List[str]]] = None, 
    tpl: str = TPL1, 
    tpl_prefix: str = '<ruby>', 
    tpl_suffix: str = '</ruby>', 
) -> str:
    '''给文本字符串加上注音 | 基于 pypinyin (https://pypi.org/project/pypinyin/)

    :param s: 要被注音的文本字符串
    :param get_pinyin: 拼音函数，用于获取文字、词组或者句子的拼音，
        默认使用`pypinyin.pinyin`，但你也可以使用其他函数，比如`pypinyin.lazy_pinyin`
        你也可以用`functools.partial`绑定了一些参数后函数，作为`get_pinyin`参数传入
        如果你想要仅仅给某些文字或词组注音（比如生僻字），则只需要加载相应的字集的拼音字典即可，操作如下：
            >>> import pypinyin
            # 清空已加载的单字集的拼音字典
            >>> pypinyin.constants.PINYIN_DICT.clear()
            # 加载某个单字集的拼音字典 a_single_dict
            >>> pypinyin.load_single_dict(a_single_dict)
            # NOTE: 生僻字的拼音字典，可以用【某个较完整拼音字典】减去【某个常用字的拼音字典】
            # NOTE: pypinyin-dict 这个包包含了一些拼音字典，详见对应文档
            # 清空已加载的词组集的拼音字典
            >>> pypinyin.constants.PHRASES_DICT.clear()
            # 加载某个单字集的拼音字典 a_phrases_dict
            >>> pypinyin.load_phrases_dict(a_phrases_dict)
        > 更具体的请参考下列文档
            - https://pypi.org/project/pypinyin/
            - https://pypinyin.readthedocs.io
            - https://pypi.org/project/pypinyin-dict/
            - https://github.com/mozillazg/pinyin-data
            - https://github.com/mozillazg/phrase-pinyin-data
    :param wordcut: 分词函数，文本会被先分词再用`get_pinyin`获得拼音，省略或者为 None 则不分词
    :param tpl: 模版，用于替换被注音的文字的位置，可以有两个占位符：
        `char`是被注音的文字，`pinyin`是文字的注音（如果是列表，则用 ','.join 连接起来）
    :param tpl_prefix: 当文字被注音后，在文本中它会被替换为`tpl`，
        在连续的多个（包括一个）`tpl`前面，插入一个`tpl_prefix`
    :param tpl_suffix: 当文字被注音后，在文本中它会被替换为`tpl`，
        在连续的多个（包括一个）`tpl`后面，会插入一个`tpl_suffix`

    :return: 注音后的文本字符串
    '''
    ls: List[str] = []
    push = ls.append
    format = tpl.format
    idx = 0
    prev_is_pinyin = False
    py0: str
    for py in get_pinyin(wordcut(s) if wordcut else s):
        if isinstance(py, str):
            is_single = True
            py0 = py
        else:
            is_single = len(py) == 1
            py0 = py[0]
        if not py0:
            if prev_is_pinyin:
                push(tpl_suffix)
            push(s[idx])
            idx += 1
            prev_is_pinyin = False
        elif py0[0] == s[idx]:
            if prev_is_pinyin:
                push(tpl_suffix)
            push(py0)
            idx += len(py0)
            prev_is_pinyin = False
        else:
            if not prev_is_pinyin:
                push(tpl_prefix)
            push(format(
                char=s[idx], 
                pinyin=py0 if is_single else ','.join(py)
            ))
            idx += 1
            prev_is_pinyin = True
    else:
        if prev_is_pinyin:
            push(tpl_suffix)
    return ''.join(ls)


def make_text_pinyin(
    text: str, /, 
    get_pinyin: Union[
        Callable[..., List[str]], 
        Callable[..., List[List[str]]], 
    ] = pinyin, 
    wordcut: Optional[Callable[[str], List[str]]] = None, 
    tpl: str = TPL1, 
    tpl_prefix: str = '<ruby>', 
    tpl_suffix: str = '</ruby>', 
    text_node_only: bool = True, 
) -> str:
    '''给文本字符串加上注音 | 基于 pypinyin (https://pypi.org/project/pypinyin/)

    :param text: 要被注音的文本字符串，文本也可以是 html 或 xhtml
    :param get_pinyin: 拼音函数，用于获取文字、词组或者句子的拼音，
        默认使用`pypinyin.pinyin`，但你也可以使用其他函数，比如`pypinyin.lazy_pinyin`
        你也可以用`functools.partial`绑定了一些参数后函数，作为`get_pinyin`参数传入
        如果你想要仅仅给某些文字或词组注音（比如生僻字），则只需要加载相应的字集的拼音字典即可，操作如下：
            >>> import pypinyin
            # 清空已加载的单字集的拼音字典
            >>> pypinyin.constants.PINYIN_DICT.clear()
            # 加载某个单字集的拼音字典 a_single_dict
            >>> pypinyin.load_single_dict(a_single_dict)
            # NOTE: 生僻字的拼音字典，可以用【某个较完整拼音字典】减去【某个常用字的拼音字典】
            # NOTE: pypinyin-dict 这个包包含了一些拼音字典，详见对应文档
            # 清空已加载的词组集的拼音字典
            >>> pypinyin.constants.PHRASES_DICT.clear()
            # 加载某个单字集的拼音字典 a_phrases_dict
            >>> pypinyin.load_phrases_dict(a_phrases_dict)
        > 更具体的请参考下列文档
            - https://pypi.org/project/pypinyin/
            - https://pypinyin.readthedocs.io
            - https://pypi.org/project/pypinyin-dict/
            - https://github.com/mozillazg/pinyin-data
            - https://github.com/mozillazg/phrase-pinyin-data
    :param wordcut: 分词函数，文本会被先分词再用`get_pinyin`获得拼音，省略或者为 None 则不分词
    :param tpl: 模版，用于替换被注音的文字的位置，可以有两个占位符：
        `char`是被注音的文字，`pinyin`是文字的注音（如果是列表，则用 ','.join 连接起来）
    :param tpl_prefix: 当文字被注音后，在文本中它会被替换为`tpl`，
        在连续的多个（包括一个）`tpl`前面，插入一个`tpl_prefix`
    :param tpl_suffix: 当文字被注音后，在文本中它会被替换为`tpl`，
        在连续的多个（包括一个）`tpl`后面，会插入一个`tpl_suffix`
    :param text_node_only: 如果为 True，则把文本视为 html 或 xhtml，而只对文本节点注音，
        否则，不会对文本类型（即 MIMEType）做假设，而会对整个文本注音

    :return: 注音后的文本字符串
    '''
    if not text_node_only:
        return with_pinyin(
            text, 
            get_pinyin=get_pinyin, 
            wordcut=wordcut, 
            tpl=tpl, 
            tpl_prefix=tpl_prefix, 
            tpl_suffix=tpl_suffix, 
        )

    def repl(m):
        satrt_idx = m.start()
        if any(satrt_idx in rng for rng in ls_ignored_range):
            return m[0]
        return with_pinyin(
            m[0], 
            get_pinyin=get_pinyin, 
            wordcut=wordcut, 
            tpl=tpl, 
            tpl_prefix=tpl_prefix, 
            tpl_suffix=tpl_suffix, 
        )

    text_len = len(text)
    ls_ignored_range = []
    try:
        start = text.index('<body>')
    except ValueError:
        try:
            start = text.index('<body ')
        except ValueError:
            start = 0
    if start > 0:
        ls_ignored_range.append(range(start))
    try:
        stop = text.index('</body>')
    except ValueError:
        stop = text_len
    if stop < text_len:
        ls_ignored_range.append(range(stop, text_len))
    ls_ignored_range.extend(range(*m.span()) for m in CRE_RUBY_EL.finditer(text))

    return CRE_TEXT_CONTENT.sub(repl, text)


def pinyincc(
    get_pinyin: Union[
        Callable[..., List[str]], 
        Callable[..., List[List[str]]], 
    ] = pinyin, 
    wordcut: Optional[Callable[[str], List[str]]] = None, 
    tpl: str = TPL1, 
    tpl_prefix: str = '<ruby>', 
    tpl_suffix: str = '</ruby>', 
    text_node_only: bool = True, 
) -> None:
    '''批量对 epub 书中 html/xhtml 的文本注音 | 基于 pypinyin (https://pypi.org/project/pypinyin/)

    :param get_pinyin: 拼音函数，用于获取文字、词组或者句子的拼音，
        默认使用`pypinyin.pinyin`，但你也可以使用其他函数，比如`pypinyin.lazy_pinyin`
        你也可以用`functools.partial`绑定了一些参数后函数，作为`get_pinyin`参数传入
        如果你想要仅仅给某些文字或词组注音（比如生僻字），则只需要加载相应的字集的拼音字典即可，操作如下：
            >>> import pypinyin
            # 清空已加载的单字集的拼音字典
            >>> pypinyin.constants.PINYIN_DICT.clear()
            # 加载某个单字集的拼音字典 a_single_dict
            >>> pypinyin.load_single_dict(a_single_dict)
            # NOTE: 生僻字的拼音字典，可以用【某个较完整拼音字典】减去【某个常用字的拼音字典】
            # NOTE: pypinyin-dict 这个包包含了一些拼音字典，详见对应文档
            # 清空已加载的词组集的拼音字典
            >>> pypinyin.constants.PHRASES_DICT.clear()
            # 加载某个单字集的拼音字典 a_phrases_dict
            >>> pypinyin.load_phrases_dict(a_phrases_dict)
        > 更具体的请参考下列文档
            - https://pypi.org/project/pypinyin/
            - https://pypinyin.readthedocs.io
            - https://pypi.org/project/pypinyin-dict/
            - https://github.com/mozillazg/pinyin-data
            - https://github.com/mozillazg/phrase-pinyin-data
    :param wordcut: 分词函数，文本会被先分词再用`get_pinyin`获得拼音，省略或者为 None 则不分词
    :param tpl: 模版，用于替换被注音的文字的位置，可以有两个占位符：
        `char`是被注音的文字，`pinyin`是文字的注音（如果是列表，则用 ','.join 连接起来）
    :param tpl_prefix: 当文字被注音后，在文本中它会被替换为`tpl`，
        在连续的多个（包括一个）`tpl`前面，插入一个`tpl_prefix`
    :param tpl_suffix: 当文字被注音后，在文本中它会被替换为`tpl`，
        在连续的多个（包括一个）`tpl`后面，会插入一个`tpl_suffix`
    :param text_node_only: 如果为 True，则把文本视为 html 或 xhtml，而只对文本节点注音，
        否则，不会对文本类型（即 MIMEType）做假设，而会对整个文本注音
    '''
    for fid, href in bc.text_iter():
        content = bc.readfile(fid)
        content_new = make_text_pinyin(
            content, 
            get_pinyin=get_pinyin, 
            wordcut=wordcut, 
            tpl=tpl, 
            tpl_prefix=tpl_prefix, 
            tpl_suffix=tpl_suffix, 
            text_node_only=text_node_only, 
        )
        if content != content_new:
            bc.writefile(fid, content_new)
            print('Modified file:', href) 


def remove_ruby_pinyin(text: str) -> str:
    '把所有<ruby>标签去除注音，保留被注音的文字'
    return CRE_RUBY_EL.sub(
        lambda m: CRE_RT_EL.sub('', CRE_RP_EL.sub('', m[1])), text)


def remove_ruby_pinyincc() -> None:
    '批量对 epub 书中 html/xhtml 的去除<ruby>标签注音'
    for fid, href in bc.text_iter():
        content = bc.readfile(fid)
        content_new = remove_ruby_pinyin(content)
        if content != content_new:
            bc.writefile(fid, content_new)
            print('Modified file:', href) 

