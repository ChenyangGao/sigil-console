#!/usr/bin/env python
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)
__all__ = ['convertcc']

plugin.ensure_import('opencc', 'OpenCC') # type: ignore

from re import compile as re_compile, Pattern
from typing import Final, List, Optional

from opencc import OpenCC # type: ignore


bc = bc # type: ignore
CRE_TEXT_CONTENT: Final[Pattern] = re_compile('(?<=>)[^<]+')
LANG_JSON_LIST: Final[List[str]] = [
    's2t.json', 't2s.json', 's2tw.json', 'tw2s.json', 's2hk.json', 
    'hk2s.json', 's2twp.json', 'tw2sp.json', 't2tw.json', 'hk2t.json', 
    't2hk.json', 't2jp.json', 'jp2t.json', 'tw2t.json', 
]
LANG_LABEL_LIST: Final[List[str]] = [
    's2t.json|简体到繁體（OpenCC 標準）|Simplified Chinese to Traditional Chinese',
    't2s.json|繁體（OpenCC 標準）到简体|Traditional Chinese to Simplified Chinese',
    's2tw.json|简体到臺灣正體|Simplified Chinese to Traditional Chinese (Taiwan Standard)',
    'tw2s.json|臺灣正體到简体|Traditional Chinese (Taiwan Standard) to Simplified Chinese',
    's2hk.json|简体到香港繁體|Simplified Chinese to Traditional Chinese (Hong Kong variant)',
    'hk2s.json|香港繁體到简体|Traditional Chinese (Hong Kong variant) to Simplified Chinese',
    's2twp.json|简体到繁體（臺灣正體標準）並轉換爲臺灣常用詞彙|Simplified Chinese to Traditional Chinese (Taiwan Standard) with Taiwanese idiom',
    'tw2sp.json|繁體（臺灣正體標準）到简体并转换为中国大陆常用词汇|Traditional Chinese (Taiwan Standard) to Simplified Chinese with Mainland Chinese idiom',
    't2tw.json|繁體（OpenCC 標準）到臺灣正體|Traditional Chinese (OpenCC Standard) to Taiwan Standard',
    'hk2t.json|香港繁體到繁體（OpenCC 標準）|Traditional Chinese (Hong Kong variant) to Traditional Chinese',
    't2hk.json|繁體（OpenCC 標準）到香港繁體|Traditional Chinese (OpenCC Standard) to Hong Kong variant',
    't2jp.json|繁體（OpenCC 標準，舊字體）到日文新字體|Traditional Chinese Characters (Kyūjitai) to New Japanese Kanji (Shinjitai)',
    'jp2t.json|日文新字體到繁體（OpenCC 標準，舊字體）|New Japanese Kanji (Shinjitai) to Traditional Chinese Characters (Kyūjitai)',
    'tw2t.json|臺灣正體到繁體（OpenCC 標準）|Traditional Chinese (Taiwan standard) to Traditional Chinese',
]
LANG_TARGET_LIST: Final[List[str]] = [
    'zh-CHT', 'zh-CN', 'zh-TW', 'zh-CN', 'zh-HK', 'zh-CN', 'zh-TW', 'zh-CN', 
    'zh-TW', 'zh-CHT', 'zh-HK', 'ja-JP', 'zh-CHT', 'zh-CHT', 
]


try:
    from PyQt5.QtWidgets import QApplication, QComboBox, QWidget

    class AskPlan(QWidget):
        def __init__(self):
            super().__init__()
            self.initUI()

        def initUI(self):
            combobox = self.combobox = QComboBox(self)
            combobox.addItems(LANG_LABEL_LIST)
            combobox.setCurrentIndex(0)
            self.setWindowTitle('选择一个转换方案 | Powered by OpenCC')
            self.resize(300, combobox.height())
            self.setFixedHeight(combobox.height())
            self.show()

    def ask_for_plan() -> int:
        app = QApplication([])
        try:
            ask = AskPlan()
            app.exec_()
            return ask.combobox.currentIndex()
        finally:
            ask.close()
            app.quit()
except ImportError:
    import tkinter
    from tkinter import ttk

    def ask_for_plan() -> int:
        curidx = 0
        def on_selected(*args):
            nonlocal curidx
            curidx = comboxlist.current()
        app = tkinter.Tk()
        try:
            app.title('选择一个转换方案 | Powered by OpenCC')
            app.resizable(width=True, height=False)
            comvalue = tkinter.StringVar()
            comboxlist = ttk.Combobox(app, state='readonly', textvariable=comvalue)
            comboxlist["values"] = LANG_LABEL_LIST
            comboxlist.current(curidx)
            comboxlist.bind("<<ComboboxSelected>>", on_selected)
            comboxlist.pack(fill="x", expand=1)
            app.mainloop()
            return curidx
        finally:
            app.quit()


def convertcc(
    lang_json: Optional[str] = None, 
    text_node_only: bool = True, 
) -> None:
    '''中文简繁体转换 | 基于 OpenCC (https://pypi.org/project/OpenCC/)

    :param lang_json: 传给 OpenCC 的配置文件，包含了转换的映射关系，如果不提供或者为 None，
        则会弹出一个对话框，可以通过选择下拉框来指定配置文件，关闭对话框后生效
    :param text_node_only: 如果为 True，则把文本视为 html 或 xhtml，而只对文本节点做简繁转换，
        否则，不会对文本类型（即 MIMEType）做假设，而会对整个文本做简繁转换
    '''
    if lang_json is None:
        idx = ask_for_plan()
        lang_json = LANG_JSON_LIST[idx]
        print('You select:', lang_json)
        print(LANG_LABEL_LIST[idx])

    converter = OpenCC(lang_json)
    convert = _convert = converter.convert

    if text_node_only:
        def repl(m):
            content = m[0]
            if not content.strip():
                return m[0]
            return _convert(content)
        convert = lambda s: CRE_TEXT_CONTENT.sub(repl, s)

    files = list(bc.text_iter())
    ncxid = bc.gettocid()
    if ncxid is not None:
        files.append((ncxid, bc.id_to_href(ncxid)))

    for fid, href in files:
        content = bc.readfile(fid)
        content_new = convert(content)
        if content != content_new:
            bc.writefile(fid, content_new)
            print('Modified file:', href) 

    content = bc.getmetadataxml()
    content_new = convert(content)
    if content != content_new:
        bc.setmetadataxml(content_new)
        print('Modified: metadata in %s' % bc.get_opfbookpath())

    guide = bc.getguide()
    new_guide = [tuple(map(converter.convert, t)) for t in guide]
    if guide != new_guide:
        bc.setguide(new_guide)
        print('Modified: guide in %s' % bc.get_opfbookpath())

