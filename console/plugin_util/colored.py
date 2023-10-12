#!/usr/bin/env python3
# coding: utf-8

"""ANSII Color formatting for output in terminal.

[Reference]
[Colors and formatting (ANSI/VT100 Control sequences)](https://misc.flogisoft.com/bash/tip_colors_and_formatting)
[ANSI escape code](https://en.wikipedia.org/wiki/ANSI_escape_code)
[rich](https://pypi.org/project/rich/)
[blessings](https://pypi.org/project/blessings/)
[colorama](https://pypi.org/project/colorama/)
[termcolor](https://pypi.org/project/termcolor/)
[colored](https://pypi.org/project/colored/)
[search@pypi.org:color](https://pypi.org/search/?q=color)
"""

from __future__ import annotations

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)

from abc import ABC, abstractproperty
from collections import namedtuple
from enum import Enum
from typing import cast, Optional, Sequence, Tuple, Union


__all__ = [
    'SET', 'STD_COLORS', 'MAP_NAME_RGBCOLOR', 'MAP_NAME_HEXCOLOR',  
    'BaseColor', 'Color', 'RGBColor', 'HexColor', 'colored',
]


FMTSTR = '\x1b[%sm'
RESET  = '\x1b[0m' # reset all


class BaseColor(ABC):

    def __new__(cls, *args, **kwargs):
        if cls.__abstractmethods__:
            abcmethods = ', '.join(cls.__abstractmethods__)
            raise TypeError(
                f"Can't instantiate abstract class {cls.__qualname__} "
                f"with abstract methods {abcmethods}"
            )
        return super().__new__(cls, *args, **kwargs)

    @abstractproperty
    def fgcolor(self):
        return NotImplemented

    @abstractproperty
    def bgcolor(self):
        return NotImplemented


class Color(BaseColor, namedtuple('Color', 'color')): # 8 bit color = 256 colors
    'See: https://en.wikipedia.org/wiki/ANSI_escape_code#8-bit'

    def __new__(cls, color: int):
        assert 0 <= color < 256, 'color value out of range(256)' # color in range(256)
        return super().__new__(cls, color)

    @property
    def fgcolor(self):
        return '38;5;%d' % self

    @property
    def bgcolor(self):
        return '48;5;%d' % self


class RGBColor(BaseColor, namedtuple('RGB', 'red, green, blue')): # 24 bit color = 16777216 colors
    'See: https://en.wikipedia.org/wiki/ANSI_escape_code#24-bit'

    def __new__(cls, red: int = 0, green: int = 0, blue: int = 0):
        assert 0 <= red < 256,   'red value out of range(256)'   # red in range(256)
        assert 0 <= green < 256, 'green value out of range(256)' # green in range(256)
        assert 0 <= blue < 256,  'blue value out of range(256)'  # blue in range(256)
        return super().__new__(cls, red, green, blue)

    @property
    def fgcolor(self):
        return '38;2;%d;%d;%d' % self

    @property
    def bgcolor(self):
        return '48;2;%d;%d;%d' % self


class HexColor(BaseColor, namedtuple('Hex', 'hexcolor')): # 24 bit color = 16777216 colors
    'See: https://en.wikipedia.org/wiki/ANSI_escape_code#24-bit'

    def __new__(
        cls, 
        hexcolor: str, 
        _match=__import__('re').compile('#[0-9A-Fa-f]{3}|#[0-9A-Fa-f]{6}').fullmatch
    ):
        assert _match(hexcolor) is not None, f'invalid `hexcolor`: {hexcolor!r}'
        return super().__new__(cls, hexcolor)

    @property
    def rgb_color(self):
        hexcolor = self.hexcolor
        if len(hexcolor) == 4:
            rgb = (int(h*2, 16) for h in hexcolor[1:])
        else:
            rgb = (int(hexcolor[i:i+2], 16) for i in range(1, 7, 2))
        return RGBColor(*rgb)

    @property
    def fgcolor(self):
        return self.rgb_color.fgcolor

    @property
    def bgcolor(self):
        return self.rgb_color.bgcolor


# See: https://en.wikipedia.org/wiki/ANSI_escape_code#SGR_.28Select_Graphic_Rendition.29_parameters
# from itertools import count
# _sets = (
#     'bold', 'dim', 'italic', 'underline', 'blink', 'rapid_blink', 
#     'reverse', 'hidden', 'cross_out'
# )
# SET = {'reset': 0}
# SET.update(zip(_sets, count(1)))
# SET.update((zip(('reset'+s for s in _sets), count(21))))
# SET.update((zip(('-'+s for s in _sets), count(21)))
SET = {
    'reset': 0,
    'bold': 1,
    'dim': 2,
    'italic': 3,
    'underline': 4,
    'blink': 5,
    'rapid_blink': 6,
    'reverse': 7,
    'hidden': 8,
    'cross_out': 9,
    'reset_bold': 21,
    'reset_dim': 22,
    'reset_italic': 23,
    'reset_underline': 24,
    'reset_blink': 25,
    'reset_rapid_blink': 26,
    'reset_reverse': 27,
    'reset_hidden': 28,
    'reset_cross_out': 29,
    '-bold': 21,
    '-dim': 22,
    '-italic': 23,
    '-underline': 24,
    '-blink': 25,
    '-rapid_blink': 26,
    '-reverse': 27,
    '-hidden': 28,
    '-cross_out': 29,
}
# See: https://en.wikipedia.org/wiki/ANSI_escape_code#Colors
# from itertools import count
# _colors = (
#     'black', 'red', 'green', 'yellow', 'blue', 
#     'magenta', 'cyan', 'white'
# )
# STD_COLORS = {'default': 39}
# STD_COLORS.update(zip(_colors, count(30)))
# STD_COLORS.update(zip(('bright'+c for c in _colors), count(90)))
# STD_COLORS.update(zip(('+'+c for c in _colors), count(90)))
STD_COLORS = {
    'default': 39,
    'black': 30,
    'red': 31,
    'green': 32,
    'yellow': 33,
    'blue': 34,
    'magenta': 35,
    'cyan': 36,
    'lightgray': 37,
    'darkgray': 90,
    'lightred': 91,
    'lightgreen': 92,
    'lightyellow': 93,
    'lightblue': 94,
    'lightmagenta': 95,
    'lightcyan': 96,
    'white': 97,
    '+black': 90,
    '+red': 91,
    '+green': 92,
    '+yello': 93,
    '+blue': 94,
    '+magenta': 95,
    '+cyan': 96,
    '+white': 97,
}
# See: https://www.runoob.com/html/html-colorvalues.html
MAP_NAME_HEXCOLOR = {
    'Black': HexColor('#000000'),
    'Navy': HexColor('#000080'),
    'DarkBlue': HexColor('#00008B'),
    'MediumBlue': HexColor('#0000CD'),
    'Blue': HexColor('#0000FF'),
    'DarkGreen': HexColor('#006400'),
    'Green': HexColor('#008000'),
    'Teal': HexColor('#008080'),
    'DarkCyan': HexColor('#008B8B'),
    'DeepSkyBlue': HexColor('#00BFFF'),
    'DarkTurquoise': HexColor('#00CED1'),
    'MediumSpringGreen': HexColor('#00FA9A'),
    'Lime': HexColor('#00FF00'),
    'SpringGreen': HexColor('#00FF7F'),
    'Aqua': HexColor('#00FFFF'),
    'Cyan': HexColor('#00FFFF'),
    'MidnightBlue': HexColor('#191970'),
    'DodgerBlue': HexColor('#1E90FF'),
    'LightSeaGreen': HexColor('#20B2AA'),
    'ForestGreen': HexColor('#228B22'),
    'SeaGreen': HexColor('#2E8B57'),
    'DarkSlateGray': HexColor('#2F4F4F'),
    'LimeGreen': HexColor('#32CD32'),
    'MediumSeaGreen': HexColor('#3CB371'),
    'Turquoise': HexColor('#40E0D0'),
    'RoyalBlue': HexColor('#4169E1'),
    'SteelBlue': HexColor('#4682B4'),
    'DarkSlateBlue': HexColor('#483D8B'),
    'MediumTurquoise': HexColor('#48D1CC'),
    'Indigo': HexColor('#4B0082'),
    'DarkOliveGreen': HexColor('#556B2F'),
    'CadetBlue': HexColor('#5F9EA0'),
    'CornflowerBlue': HexColor('#6495ED'),
    'MediumAquaMarine': HexColor('#66CDAA'),
    'DimGray': HexColor('#696969'),
    'SlateBlue': HexColor('#6A5ACD'),
    'OliveDrab': HexColor('#6B8E23'),
    'SlateGray': HexColor('#708090'),
    'LightSlateGray': HexColor('#778899'),
    'MediumSlateBlue': HexColor('#7B68EE'),
    'LawnGreen': HexColor('#7CFC00'),
    'Chartreuse': HexColor('#7FFF00'),
    'Aquamarine': HexColor('#7FFFD4'),
    'Maroon': HexColor('#800000'),
    'Purple': HexColor('#800080'),
    'Olive': HexColor('#808000'),
    'Gray': HexColor('#808080'),
    'SkyBlue': HexColor('#87CEEB'),
    'LightSkyBlue': HexColor('#87CEFA'),
    'BlueViolet': HexColor('#8A2BE2'),
    'DarkRed': HexColor('#8B0000'),
    'DarkMagenta': HexColor('#8B008B'),
    'SaddleBrown': HexColor('#8B4513'),
    'DarkSeaGreen': HexColor('#8FBC8F'),
    'LightGreen': HexColor('#90EE90'),
    'MediumPurple': HexColor('#9370DB'),
    'DarkViolet': HexColor('#9400D3'),
    'PaleGreen': HexColor('#98FB98'),
    'DarkOrchid': HexColor('#9932CC'),
    'YellowGreen': HexColor('#9ACD32'),
    'Sienna': HexColor('#A0522D'),
    'Brown': HexColor('#A52A2A'),
    'DarkGray': HexColor('#A9A9A9'),
    'LightBlue': HexColor('#ADD8E6'),
    'GreenYellow': HexColor('#ADFF2F'),
    'PaleTurquoise': HexColor('#AFEEEE'),
    'LightSteelBlue': HexColor('#B0C4DE'),
    'PowderBlue': HexColor('#B0E0E6'),
    'FireBrick': HexColor('#B22222'),
    'DarkGoldenRod': HexColor('#B8860B'),
    'MediumOrchid': HexColor('#BA55D3'),
    'RosyBrown': HexColor('#BC8F8F'),
    'DarkKhaki': HexColor('#BDB76B'),
    'Silver': HexColor('#C0C0C0'),
    'MediumVioletRed': HexColor('#C71585'),
    'IndianRed': HexColor('#CD5C5C'),
    'Peru': HexColor('#CD853F'),
    'Chocolate': HexColor('#D2691E'),
    'Tan': HexColor('#D2B48C'),
    'LightGray': HexColor('#D3D3D3'),
    'Thistle': HexColor('#D8BFD8'),
    'Orchid': HexColor('#DA70D6'),
    'GoldenRod': HexColor('#DAA520'),
    'PaleVioletRed': HexColor('#DB7093'),
    'Crimson': HexColor('#DC143C'),
    'Gainsboro': HexColor('#DCDCDC'),
    'Plum': HexColor('#DDA0DD'),
    'BurlyWood': HexColor('#DEB887'),
    'LightCyan': HexColor('#E0FFFF'),
    'Lavender': HexColor('#E6E6FA'),
    'DarkSalmon': HexColor('#E9967A'),
    'Violet': HexColor('#EE82EE'),
    'PaleGoldenRod': HexColor('#EEE8AA'),
    'LightCoral': HexColor('#F08080'),
    'Khaki': HexColor('#F0E68C'),
    'AliceBlue': HexColor('#F0F8FF'),
    'HoneyDew': HexColor('#F0FFF0'),
    'Azure': HexColor('#F0FFFF'),
    'SandyBrown': HexColor('#F4A460'),
    'Wheat': HexColor('#F5DEB3'),
    'Beige': HexColor('#F5F5DC'),
    'WhiteSmoke': HexColor('#F5F5F5'),
    'MintCream': HexColor('#F5FFFA'),
    'GhostWhite': HexColor('#F8F8FF'),
    'Salmon': HexColor('#FA8072'),
    'AntiqueWhite': HexColor('#FAEBD7'),
    'Linen': HexColor('#FAF0E6'),
    'LightGoldenRodYellow': HexColor('#FAFAD2'),
    'OldLace': HexColor('#FDF5E6'),
    'Red': HexColor('#FF0000'),
    'Fuchsia': HexColor('#FF00FF'),
    'Magenta': HexColor('#FF00FF'),
    'DeepPink': HexColor('#FF1493'),
    'OrangeRed': HexColor('#FF4500'),
    'Tomato': HexColor('#FF6347'),
    'HotPink': HexColor('#FF69B4'),
    'Coral': HexColor('#FF7F50'),
    'DarkOrange': HexColor('#FF8C00'),
    'LightSalmon': HexColor('#FFA07A'),
    'Orange': HexColor('#FFA500'),
    'LightPink': HexColor('#FFB6C1'),
    'Pink': HexColor('#FFC0CB'),
    'Gold': HexColor('#FFD700'),
    'PeachPuff': HexColor('#FFDAB9'),
    'NavajoWhite': HexColor('#FFDEAD'),
    'Moccasin': HexColor('#FFE4B5'),
    'Bisque': HexColor('#FFE4C4'),
    'MistyRose': HexColor('#FFE4E1'),
    'BlanchedAlmond': HexColor('#FFEBCD'),
    'PapayaWhip': HexColor('#FFEFD5'),
    'LavenderBlush': HexColor('#FFF0F5'),
    'SeaShell': HexColor('#FFF5EE'),
    'Cornsilk': HexColor('#FFF8DC'),
    'LemonChiffon': HexColor('#FFFACD'),
    'FloralWhite': HexColor('#FFFAF0'),
    'Snow': HexColor('#FFFAFA'),
    'Yellow': HexColor('#FFFF00'),
    'LightYellow': HexColor('#FFFFE0'),
    'Ivory': HexColor('#FFFFF0'),
    'White': HexColor('#FFFFFF')
}
MAP_NAME_RGBCOLOR = {
    'Black': RGBColor(red=0, green=0, blue=0),
    'Navy': RGBColor(red=0, green=0, blue=128),
    'DarkBlue': RGBColor(red=0, green=0, blue=139),
    'MediumBlue': RGBColor(red=0, green=0, blue=205),
    'Blue': RGBColor(red=0, green=0, blue=255),
    'DarkGreen': RGBColor(red=0, green=100, blue=0),
    'Green': RGBColor(red=0, green=128, blue=0),
    'Teal': RGBColor(red=0, green=128, blue=128),
    'DarkCyan': RGBColor(red=0, green=139, blue=139),
    'DeepSkyBlue': RGBColor(red=0, green=191, blue=255),
    'DarkTurquoise': RGBColor(red=0, green=206, blue=209),
    'MediumSpringGreen': RGBColor(red=0, green=250, blue=154),
    'Lime': RGBColor(red=0, green=255, blue=0),
    'SpringGreen': RGBColor(red=0, green=255, blue=127),
    'Aqua': RGBColor(red=0, green=255, blue=255),
    'Cyan': RGBColor(red=0, green=255, blue=255),
    'MidnightBlue': RGBColor(red=25, green=25, blue=112),
    'DodgerBlue': RGBColor(red=30, green=144, blue=255),
    'LightSeaGreen': RGBColor(red=32, green=178, blue=170),
    'ForestGreen': RGBColor(red=34, green=139, blue=34),
    'SeaGreen': RGBColor(red=46, green=139, blue=87),
    'DarkSlateGray': RGBColor(red=47, green=79, blue=79),
    'LimeGreen': RGBColor(red=50, green=205, blue=50),
    'MediumSeaGreen': RGBColor(red=60, green=179, blue=113),
    'Turquoise': RGBColor(red=64, green=224, blue=208),
    'RoyalBlue': RGBColor(red=65, green=105, blue=225),
    'SteelBlue': RGBColor(red=70, green=130, blue=180),
    'DarkSlateBlue': RGBColor(red=72, green=61, blue=139),
    'MediumTurquoise': RGBColor(red=72, green=209, blue=204),
    'Indigo': RGBColor(red=75, green=0, blue=130),
    'DarkOliveGreen': RGBColor(red=85, green=107, blue=47),
    'CadetBlue': RGBColor(red=95, green=158, blue=160),
    'CornflowerBlue': RGBColor(red=100, green=149, blue=237),
    'MediumAquaMarine': RGBColor(red=102, green=205, blue=170),
    'DimGray': RGBColor(red=105, green=105, blue=105),
    'SlateBlue': RGBColor(red=106, green=90, blue=205),
    'OliveDrab': RGBColor(red=107, green=142, blue=35),
    'SlateGray': RGBColor(red=112, green=128, blue=144),
    'LightSlateGray': RGBColor(red=119, green=136, blue=153),
    'MediumSlateBlue': RGBColor(red=123, green=104, blue=238),
    'LawnGreen': RGBColor(red=124, green=252, blue=0),
    'Chartreuse': RGBColor(red=127, green=255, blue=0),
    'Aquamarine': RGBColor(red=127, green=255, blue=212),
    'Maroon': RGBColor(red=128, green=0, blue=0),
    'Purple': RGBColor(red=128, green=0, blue=128),
    'Olive': RGBColor(red=128, green=128, blue=0),
    'Gray': RGBColor(red=128, green=128, blue=128),
    'SkyBlue': RGBColor(red=135, green=206, blue=235),
    'LightSkyBlue': RGBColor(red=135, green=206, blue=250),
    'BlueViolet': RGBColor(red=138, green=43, blue=226),
    'DarkRed': RGBColor(red=139, green=0, blue=0),
    'DarkMagenta': RGBColor(red=139, green=0, blue=139),
    'SaddleBrown': RGBColor(red=139, green=69, blue=19),
    'DarkSeaGreen': RGBColor(red=143, green=188, blue=143),
    'LightGreen': RGBColor(red=144, green=238, blue=144),
    'MediumPurple': RGBColor(red=147, green=112, blue=219),
    'DarkViolet': RGBColor(red=148, green=0, blue=211),
    'PaleGreen': RGBColor(red=152, green=251, blue=152),
    'DarkOrchid': RGBColor(red=153, green=50, blue=204),
    'YellowGreen': RGBColor(red=154, green=205, blue=50),
    'Sienna': RGBColor(red=160, green=82, blue=45),
    'Brown': RGBColor(red=165, green=42, blue=42),
    'DarkGray': RGBColor(red=169, green=169, blue=169),
    'LightBlue': RGBColor(red=173, green=216, blue=230),
    'GreenYellow': RGBColor(red=173, green=255, blue=47),
    'PaleTurquoise': RGBColor(red=175, green=238, blue=238),
    'LightSteelBlue': RGBColor(red=176, green=196, blue=222),
    'PowderBlue': RGBColor(red=176, green=224, blue=230),
    'FireBrick': RGBColor(red=178, green=34, blue=34),
    'DarkGoldenRod': RGBColor(red=184, green=134, blue=11),
    'MediumOrchid': RGBColor(red=186, green=85, blue=211),
    'RosyBrown': RGBColor(red=188, green=143, blue=143),
    'DarkKhaki': RGBColor(red=189, green=183, blue=107),
    'Silver': RGBColor(red=192, green=192, blue=192),
    'MediumVioletRed': RGBColor(red=199, green=21, blue=133),
    'IndianRed': RGBColor(red=205, green=92, blue=92),
    'Peru': RGBColor(red=205, green=133, blue=63),
    'Chocolate': RGBColor(red=210, green=105, blue=30),
    'Tan': RGBColor(red=210, green=180, blue=140),
    'LightGray': RGBColor(red=211, green=211, blue=211),
    'Thistle': RGBColor(red=216, green=191, blue=216),
    'Orchid': RGBColor(red=218, green=112, blue=214),
    'GoldenRod': RGBColor(red=218, green=165, blue=32),
    'PaleVioletRed': RGBColor(red=219, green=112, blue=147),
    'Crimson': RGBColor(red=220, green=20, blue=60),
    'Gainsboro': RGBColor(red=220, green=220, blue=220),
    'Plum': RGBColor(red=221, green=160, blue=221),
    'BurlyWood': RGBColor(red=222, green=184, blue=135),
    'LightCyan': RGBColor(red=224, green=255, blue=255),
    'Lavender': RGBColor(red=230, green=230, blue=250),
    'DarkSalmon': RGBColor(red=233, green=150, blue=122),
    'Violet': RGBColor(red=238, green=130, blue=238),
    'PaleGoldenRod': RGBColor(red=238, green=232, blue=170),
    'LightCoral': RGBColor(red=240, green=128, blue=128),
    'Khaki': RGBColor(red=240, green=230, blue=140),
    'AliceBlue': RGBColor(red=240, green=248, blue=255),
    'HoneyDew': RGBColor(red=240, green=255, blue=240),
    'Azure': RGBColor(red=240, green=255, blue=255),
    'SandyBrown': RGBColor(red=244, green=164, blue=96),
    'Wheat': RGBColor(red=245, green=222, blue=179),
    'Beige': RGBColor(red=245, green=245, blue=220),
    'WhiteSmoke': RGBColor(red=245, green=245, blue=245),
    'MintCream': RGBColor(red=245, green=255, blue=250),
    'GhostWhite': RGBColor(red=248, green=248, blue=255),
    'Salmon': RGBColor(red=250, green=128, blue=114),
    'AntiqueWhite': RGBColor(red=250, green=235, blue=215),
    'Linen': RGBColor(red=250, green=240, blue=230),
    'LightGoldenRodYellow': RGBColor(red=250, green=250, blue=210),
    'OldLace': RGBColor(red=253, green=245, blue=230),
    'Red': RGBColor(red=255, green=0, blue=0),
    'Fuchsia': RGBColor(red=255, green=0, blue=255),
    'Magenta': RGBColor(red=255, green=0, blue=255),
    'DeepPink': RGBColor(red=255, green=20, blue=147),
    'OrangeRed': RGBColor(red=255, green=69, blue=0),
    'Tomato': RGBColor(red=255, green=99, blue=71),
    'HotPink': RGBColor(red=255, green=105, blue=180),
    'Coral': RGBColor(red=255, green=127, blue=80),
    'DarkOrange': RGBColor(red=255, green=140, blue=0),
    'LightSalmon': RGBColor(red=255, green=160, blue=122),
    'Orange': RGBColor(red=255, green=165, blue=0),
    'LightPink': RGBColor(red=255, green=182, blue=193),
    'Pink': RGBColor(red=255, green=192, blue=203),
    'Gold': RGBColor(red=255, green=215, blue=0),
    'PeachPuff': RGBColor(red=255, green=218, blue=185),
    'NavajoWhite': RGBColor(red=255, green=222, blue=173),
    'Moccasin': RGBColor(red=255, green=228, blue=181),
    'Bisque': RGBColor(red=255, green=228, blue=196),
    'MistyRose': RGBColor(red=255, green=228, blue=225),
    'BlanchedAlmond': RGBColor(red=255, green=235, blue=205),
    'PapayaWhip': RGBColor(red=255, green=239, blue=213),
    'LavenderBlush': RGBColor(red=255, green=240, blue=245),
    'SeaShell': RGBColor(red=255, green=245, blue=238),
    'Cornsilk': RGBColor(red=255, green=248, blue=220),
    'LemonChiffon': RGBColor(red=255, green=250, blue=205),
    'FloralWhite': RGBColor(red=255, green=250, blue=240),
    'Snow': RGBColor(red=255, green=250, blue=250),
    'Yellow': RGBColor(red=255, green=255, blue=0),
    'LightYellow': RGBColor(red=255, green=255, blue=224),
    'Ivory': RGBColor(red=255, green=255, blue=240),
    'White': RGBColor(red=255, green=255, blue=255)
}


GroundColorEnum = Enum('GroundColorEnum', 'fg, bg', start=0)

def ensure_enum(obj, cls):
    if isinstance(obj, cls):
        return obj
    elif isinstance(obj, int):
        return cls(obj)
    elif isinstance(obj, str):
        return cls[obj]
    raise TypeError


def _make_color(
    color: Union[str, int, Tuple[int, ...], BaseColor], 
    kind: Union[int, str, GroundColorEnum] = GroundColorEnum.fg, 
) -> Union[BaseColor, int]:
    kind = cast(GroundColorEnum, ensure_enum(kind, GroundColorEnum))
    if not isinstance(color, BaseColor):
        if isinstance(color, int):
            color = Color(color)
        elif isinstance(color, tuple):
            color = RGBColor(*color[:3])
        elif isinstance(color, str):
            if color.startswith('#'):
                color = HexColor(color)
            elif color in STD_COLORS:
                return STD_COLORS[color] + kind.value * 10
            elif color in MAP_NAME_RGBCOLOR:
                color = MAP_NAME_RGBCOLOR[color]
            else:
                raise ValueError(f'invalid color {color!r}')
    return color.bgcolor if kind.value else color.fgcolor


def colored(
    text: str, 
    color: Union[str, int, Tuple[int, ...], BaseColor, None] = None, 
    bgcolor: Union[str, int, Tuple[int, ...], BaseColor, None] = None, 
    attrs: Optional[Sequence] = None, 
    reset_at_end: bool = True, 
) -> str:
    """Colorize text.

    :param text:            text that is about to be colorized
    :param color:           foreground color, if any
    :param bgcolor:         background color, if any
    :param attrs:            sequence of set and reset, if any
    :param reset_at_end:    reset all at text end, if True, default True

    :return:                colorized text
    """
    attrs_ = []
    if color is not None:
        attrs_.append(_make_color(color))
    if bgcolor is not None:
        attrs_.append(_make_color(bgcolor, 'bg'))
    if attrs is not None:
        attrs_.extend(SET.get(s, s) for s in attrs)
    set_fmt = FMTSTR % ';'.join(map(str, attrs_))
    reset = RESET if reset_at_end else ''
    return f'{set_fmt}{text}{reset}'


# TODO: Provides a special template syntax to make it easier to set colors and effects

