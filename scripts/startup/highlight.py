#!/usr/bin/env python
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)
__all__ = ['make_highlighter', 'render']

try:
    plugin.ensure_import('pygments', 'Pygments') # type: ignore
except:
    pass

from html import escape
from typing import Callable, Optional, Union
from pygments import highlight # type: ignore
from pygments.formatter import Formatter # type: ignore
from pygments.formatters import HtmlFormatter # type: ignore
from pygments.lexer import Lexer # type: ignore
from pygments.lexers import ( # type: ignore
    get_lexer_by_name, get_lexer_for_filename, guess_lexer, 
    TextLexer, 
)


def make_highlighter(
    formatter: Formatter = HtmlFormatter(), 
) -> Callable[[str, Union[str, Lexer, Callable[..., Lexer]]], str]:
    '''高阶函数，创建一个做代码高亮的函数 | Powered by [Pygments](https://pygments.org/)
    NOTE: 你可以创建自定义的格式化器 formatter，并且给予自定义的 style
        可参考：
            - [Available formatters](https://pygments.org/docs/formatters/)
            - [Styles](https://pygments.org/docs/styles/)
    NOTE: 你可以创建自定义的词法分析器 lexer，并且给予自定义的 filter，
        如果你想让自定义的词法分析器可以被诸如 
            · pygments.lexers.get_lexer_by_name
            · pygments.lexers.get_lexer_for_filename
            · pygments.lexers.get_lexer_for_mimetype
        等函数获取到，可以把一些相关的信息添加到 pygments.lexers.LEXERS
        可参考：
            - [Available lexers](https://pygments.org/docs/lexers/)
            - [Filters](https://pygments.org/docs/filters/)

    :param formatter: 某个 pygments 格式化器

    :return: 代码高亮函数
    '''
    def highlighter(
        code: str, 
        lexer: Union[str, Lexer, Callable[..., Lexer]] = TextLexer(), 
    ) -> str:
        '''代码高亮 | Powered by [Pygments](https://pygments.org/)
        NOTE: 这个函数还有几个属性：
            · highlighter.formatter: 关联的 pygments 格式化器
            · highlighter.highlight: 就是这个函数的引用，即 highlighter is highlighter.highlight
            · highlighter.style: 样式表，如果没有则为 ''

        :param code: 代码文本
        :param lexer: 某个 pygments 词法分析器
            · 如果为 pygments.lexer.Lexer 实例，则直接使用之
            · 如果为 ''，则根据代码文本猜测一个 lexer
            · 如果为非空字符串，则被认为是编程语言名或文件名，而尝试获取 lexer
            · 否则，应该是一个返回 pygments.lexer.Lexer 实例的类或工厂函数，直接调用之

        :return: 高亮处理后的代码文本
        '''
        if not isinstance(lexer, Lexer):
            if isinstance(lexer, str):
                if lexer == '':
                    lexer = guess_lexer(code)
                else:
                    try:
                        lexer = get_lexer_by_name(lexer)
                    except:
                        lexer = get_lexer_for_filename(lexer)
            else:
                lexer = lexer()
        return highlight(code, lexer, formatter)
    highlighter.formatter = formatter # type: ignore
    highlighter.highlight = highlighter # type: ignore
    try:
        highlighter.style = formatter.get_style_defs() # type: ignore
    except NotImplementedError:
        highlighter.style = '' # type: ignore
    return highlighter


def render(
    code: str, 
    lang: Optional[str] = '', 
    formatter: Formatter = HtmlFormatter(), 
) -> str:
    '''代码高亮 | Powered by [Pygments](https://pygments.org/)
    NOTE: 你可以创建自定义的格式化器 formatter，并且给予自定义的 style
        可参考：
            - [Available formatters](https://pygments.org/docs/formatters/)
            - [Styles](https://pygments.org/docs/styles/)
    NOTE: 你可以创建自定义的词法分析器 lexer，并且给予自定义的 filter，
        如果你想让自定义的词法分析器可以被诸如 
            · pygments.lexers.get_lexer_by_name
            · pygments.lexers.get_lexer_for_filename
            · pygments.lexers.get_lexer_for_mimetype
        等函数获取到，可以把一些相关的信息添加到 pygments.lexers.LEXERS
        可参考：
            - [Available lexers](https://pygments.org/docs/lexers/)
            - [Filters](https://pygments.org/docs/filters/)

    :param code: 代码文本
    :param lang: 编程语言
        · 如果为 None，则不进行高亮
        · 如果为 ''，则根据代码文本猜测一个 lexer
        · 否则，会用相应编程语言的 lexer
    :param formatter: 某个 pygments 格式化器

    :return: 高亮处理后的代码文本，html 格式
    '''
    assert isinstance(formatter, HtmlFormatter), \
        'formatter 必须是 pygments.formatters.html.HtmlFormatter 实例'
    if lang is None:
        return '<pre><code>%s</code></pre>' % escape(code)
    elif lang == '':
        lexer = guess_lexer(code)
    else:
        lexer = get_lexer_by_name(lang)
    return highlight(code, lexer, formatter)

