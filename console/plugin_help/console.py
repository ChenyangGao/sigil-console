#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 1)
__all__ = ["CONSOLE_MAP", "register_console", "start_console", "start_embedded_python_shell"]

from os import environ, path as os_path
from subprocess import CompletedProcess
from sys import _getframe, executable
from typing import Callable, Final, Optional

from plugin_util.console import start_specific_python_console
from plugin_util.pip_tool import ensure_install
from plugin_util.register import bind_function_registry
from plugin_util.run import prun, prun_module, restart_program


_SYSTEM_IS_WINDOWS: Final[bool] = __import__("platform").system() == "Windows"
CONSOLE_MAP: Final[dict[str, Callable]] = {}


register_console = bind_function_registry(CONSOLE_MAP)
register_console.__doc__ = """\
Register a console with a specified name.

You can register a function with the name `"console_name"` through these ways

.. code-block:: python

    @register_console("console_name")
    def start_specific_console():
        ...

**OR**

.. code-block:: python

    @register_console
    def console_name():
        ...

"""


def start_console(name: str, /):
    "Run a console with a specified name."
    try:
        start = CONSOLE_MAP[name]
    except KeyError:
        raise ValueError(f"no such console: {name!r}, only accept: {tuple(CONSOLE_MAP)!r}")
    start()


def start_embedded_python_shell(
    shell: Optional[str] = None, 
    namespace: Optional[dict] = None, 
    banner: str = "", 
):
    "Start the specified embedded Python shell."
    if namespace is None:
        frame = _getframe(1)
        namespace = frame.f_locals
        while namespace.get("__name__") != "__main__" and frame.f_back:
            frame = frame.f_back
            namespace = frame.f_locals
    if namespace is None:
        namespace = {}
    if "plugin" not in namespace:
        import plugin_help as plugin
        bc = __import__("bookcontainer").BookContainer(plugin.Wrapper)
        namespace.update({"bc": bc, "bk": bc, "plugin": plugin, "editor": plugin.editor})
    start_specific_python_console(namespace, banner, shell)


@register_console("python(embed)")
def start_embedded_python():
    start_embedded_python_shell("python")


@register_console("ipython(embed)")
def start_embedded_ipython():
    start_embedded_python_shell("ipython")


@register_console("bpython(embed)")
def start_embedded_bpython():
    start_embedded_python_shell("bpython")


@register_console("ptpython(embed)")
def start_embedded_ptpython():
    start_embedded_python_shell("ptpython")


@register_console("ptipython(embed)")
def start_embedded_ptipython():
    start_embedded_python_shell("ptipython")


@register_console("python")
def start_python() -> CompletedProcess:
    """Start an python process, and wait until it is terminated.
    Reference:
        - https://www.python.org
        - https://docs.python.org/3/
    """
    from .function import _ctx_wrapper
    with _ctx_wrapper():
        return prun(executable)


@register_console("ipython")
def start_ipython() -> CompletedProcess:
    """Start an ipython process, and wait until it is terminated.
    Reference:
        - https://ipython.org
        - https://ipython.org/documentation.html
        - https://pypi.org/project/ipython/
        - https://github.com/ipython/ipython
    """
    ensure_install("IPython", "ipython")
    from .function import _ctx_wrapper
    with _ctx_wrapper():
        return prun_module("IPython")


@register_console("bpython")
def start_bpython() -> CompletedProcess:
    """Start an bpython process, and wait until it is terminated.
    Reference:
        - https://pypi.org/project/bpython/
        - https://bpython-interpreter.org
        - https://docs.bpython-interpreter.org/en/latest/
    """
    ensure_install("bpython")
    from .function import _ctx_wrapper
    with _ctx_wrapper():
        return prun_module("bpython")


@register_console("ptpython")
def start_ptpython() -> CompletedProcess:
    """Start an ptpython process, and wait until it is terminated.
    Reference:
        - https://pypi.org/project/ptpython/
        - https://github.com/prompt-toolkit/ptpython
        - https://pypi.org/project/prompt-toolkit/
        - https://www.asmeurer.com/mypython/
    """
    ensure_install("ptpython")
    from .function import _ctx_wrapper
    with _ctx_wrapper():
        return prun_module("ptpython")


@register_console("ptipython")
def start_ptipython() -> CompletedProcess:
    """Start an ptipython process, and wait until it is terminated.
    Reference:
        - https://github.com/prompt-toolkit/ptpython#ipython-support
    """
    ensure_install("IPython", "ipython")
    ensure_install("ptpython")
    from .function import _ctx_wrapper
    with _ctx_wrapper():
        return prun_module("ptpython.entry_points.run_ptipython")


@register_console("xonsh")
def start_xonsh() -> CompletedProcess:
    """Start a xonsh process, and wait until it is terminated.
    Reference:
        - https://github.com/xonsh/xonsh
        - https://xon.sh/contents.html
    """
    ensure_install("xonsh")
    from .function import _ctx_wrapper
    with _ctx_wrapper():
        return prun_module("xonsh", ("--rc", environ["PYTHONSTARTUP"]))


@register_console("jupyter console")
def start_jupyter_console() -> CompletedProcess:
    """Start a jupyter console process, and wait until it is terminated.
    Reference:
        - https://jupyter-console.readthedocs.io/en/latest/
    """
    ensure_install("jupyter_console")
    from .function import _ctx_wrapper
    with _ctx_wrapper():
        return prun_module("jupyter_console")


@register_console("jupyter lab")
def start_jupyter_lab() -> CompletedProcess:
    """Start a jupyter lab process, and wait until it is terminated.
    Reference:
        - https://jupyterlab.readthedocs.io/en/latest/
    """
    ensure_install("jupyterlab")
    from .function import _ctx_wrapper
    with _ctx_wrapper():
        if not os_path.exists("sigil_console.ipynb"):
            open("sigil_console.ipynb", "w", encoding="utf-8").write(
                '{"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}')
        return prun_module("jupyterlab", ("--notebook-dir='.'", "--ServerApp.open_browser=True", "-y", "sigil_console.ipynb"))


@register_console("jupyter notebook")
def start_jupyter_notebook() -> CompletedProcess:
    """Start a jupyter notebook process, and wait until it is terminated.
    Reference:
        - https://jupyter-notebook.readthedocs.io/en/latest/
    """
    ensure_install("notebook")
    from .function import _ctx_wrapper
    with _ctx_wrapper():
        if not os_path.exists("sigil_console.ipynb"):
            open("sigil_console.ipynb", "w", encoding="utf-8").write(
                '{"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}')
        return prun_module("notebook", ("--NotebookApp.notebook_dir='.'", "--NotebookApp.open_browser=True", "-y", "sigil_console.ipynb"))


@register_console("euporie console")
def start_euporie_console() -> CompletedProcess:
    """Start an euporie process, and wait until it is terminated.
    Reference:
        - https://pypi.org/project/euporie/
        - https://euporie.readthedocs.io/en/latest/apps/console.html
    """
    ensure_install("euporie")
    from .function import _ctx_wrapper
    with _ctx_wrapper():
        return prun_module("euporie.core", ("console",))


@register_console("euporie notebook")
def start_euporie_notebook() -> CompletedProcess:
    """Start an euporie process, and wait until it is terminated.
    Reference:
        - https://pypi.org/project/euporie/
        - https://euporie.readthedocs.io/en/latest/apps/notebook.html
    """
    ensure_install("euporie")
    from .function import _ctx_wrapper
    with _ctx_wrapper():
        return prun_module("euporie.core", ("notebook", "sigil_console.ipynb"))


# @register_console("jpterm")
# def start_jpterm() -> CompletedProcess:
#     """Start a jpterm process, and wait until it is terminated.
#     Reference:
#         - https://pypi.org/project/jpterm/
#     """
#     ensure_install("jpterm")
#     from .function import _ctx_wrapper
#     with _ctx_wrapper():
#         return prun([executable, "-c", "from jpterm.cli import main; main()"])


@register_console("qtconsole")
def start_qtconsole() -> CompletedProcess:
    """Start a qtconsole process, and wait until it is terminated.
    Reference:
        - https://pypi.org/project/qtconsole/
    """
    ensure_install("qtconsole")
    from .function import _ctx_wrapper
    with _ctx_wrapper():
        return prun_module("qtconsole")


@register_console("spyder")
def start_spyder() -> CompletedProcess:
    """Start a spyder IDE process, and wait until it is terminated.
    Reference:
        - https://pypi.org/project/spyder/
    """
    ensure_install("spyder")
    from .function import _ctx_wrapper
    with _ctx_wrapper():
        return prun_module("spyder.app.start", ("--window-title", "Sigil Console", "--workdir", environ["PLUGIN_OUTDIR"]))


@register_console("idle")
def start_idle() -> CompletedProcess:
    """Start an idle process, and wait until it is terminated.
    Reference:
        - https://docs.python.org/3/library/idle.html
        - 
    """
    from .function import _ctx_wrapper
    with _ctx_wrapper():
        return prun_module("idlelib", ("-t", "Sigil Console", "-s"))


@register_console("idlex")
def start_idlex() -> CompletedProcess:
    """Start an idlex process, and wait until it is terminated.
    Reference:
        - https://idlex.sourceforge.net
    """
    ensure_install("idlexlib")
    from .function import _ctx_wrapper
    with _ctx_wrapper():
        return prun_module("idlexlib.launch", ("-t", "Sigil Console", "-r", environ["PYTHONSTARTUP"]))


@register_console("idlea")
def start_idlea() -> CompletedProcess:
    """Start an idlea process, and wait until it is terminated.
    Reference:
        - https://pypi.org/project/idlea/
    """
    ensure_install("idlea")
    from .function import _ctx_wrapper
    with _ctx_wrapper():
        return prun_module("idlealib", ("-t", "Sigil Console", "-r", environ["PYTHONSTARTUP"]))


@register_console("thonny")
def start_thonny() -> CompletedProcess:
    """Start a thonny IDE process, and wait until it is terminated.
    Reference:
        - https://thonny.org
    """
    ensure_install("thonny")
    from .function import _ctx_wrapper
    with _ctx_wrapper():
        return prun_module("thonny", (environ["PYTHONSTARTUP"],))


@register_console("eric")
def start_eric() -> CompletedProcess:
    """Start an eric IDE process, and wait until it is terminated.
    Reference:
        - https://eric-ide.python-projects.org
    """
    ensure_install("eric-ide")
    from .function import _ctx_wrapper
    with _ctx_wrapper():
        return prun_module("eric7.eric7_ide", (environ["PYTHONSTARTUP"],))

