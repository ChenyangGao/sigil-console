#!/usr/bin/env python
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)
__all__ = ['add_markdown', 'add_markdowns']

plugin.ensure_import('mdtex2html') # type: ignore

from os import PathLike
from pathlib import Path
from typing import Callable, Iterable, Union

import mdtex2html # type: ignore


bc = bc # type: ignore

PathType = Union[str, PathLike]


def markdown_to_xhtml(text: str) -> str:
    '''把 markdown 文本转换为 xhtml 文本

    :param text: markdown 文本

    :return: 转换后的 xhtml 文本
    '''
    return f'''\
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
  "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">

<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title></title>
</head>

<body>
{mdtex2html.convert(text)}
</body>
</html>'''


def add_markdown(
    path: Union[str, PathType], 
    to_html: Callable[[str], str] = markdown_to_xhtml, 
) -> None:
    '''添加一个本地的 markdown 文件到 epub，它会被转化为 xhtml
    NOTE: 会以 markdown 文件的文件名（扩展名变成 .xhtml）作为 manifest_id 添加到 epub 中

    :param path: markdown 文本的本地路径，扩展名必须是 .md
    :param to_html: 函数，用于把 markdown 文本转换为 xhtml 文本
    '''
    path = Path(path)
    if path.suffix != '.md':
        return
    markdown = open(path).read()
    xhtml = to_html(markdown)
    name = path.stem + '.xhtml'
    bc.addfile(name, name, xhtml)
    print('Add file:', name)


def add_markdowns(
    path_or_pathes: Union[PathType, Iterable[PathType]], 
    to_html: Callable[[str], str] = markdown_to_xhtml, 
) -> None:
    '''添加一批本地的 markdown 文件到 epub，它们会被转化为 xhtml
    NOTE: 会以 markdown 文件的文件名（扩展名变成 .xhtml）作为 manifest_id 添加到 epub 中

    :param path_or_pathes: 本地地址或者一批本地地址，如果遇到文件夹，则遍历其中的文件
    :param to_html: 函数，用于把 markdown 文本转换为 xhtml 文本
    '''
    path: PathType
    if isinstance(path_or_pathes, (str, PathLike)):
        path = Path(path_or_pathes)
        if path.is_dir():
            for child_path in path.iterdir():
                add_markdowns(child_path, to_html)
        else:
            add_markdown(path, to_html)
    else:
        for path in path_or_pathes:
            add_markdowns(path, to_html)

