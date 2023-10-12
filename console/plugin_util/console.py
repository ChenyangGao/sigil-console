#!/usr/bin/env python3
# coding: utf-8

# Fork From: https://github.com/scrapy/scrapy/blob/master/scrapy/utils/console.py
# Reference:
#   - https://github.com/django/django/blob/master/django/core/management/commands/shell.py
#   - https://django-extensions.readthedocs.io/en/latest/shell_plus.html
#   - https://flask-shellplus.readthedocs.io/en/latest/
#   - https://python-prompt-toolkit.readthedocs.io/en/latest/

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 1)

from functools import update_wrapper
from typing import Optional


__all__ = [
    "__shell__", "DEFAULT_PYTHON_SHELLS", "PYTHON_SHELL_REQUIREMENTS", 
    "get_current_shell", "list_shells", "get_shell_embed_func", 
    "start_python_console", "start_specific_python_console"
]


__shell__: Optional[str] = None


def _embed_ipython_shell(namespace={}, banner=""):
    """Start an IPython Shell"""
    try:
        from IPython.terminal.embed import InteractiveShellEmbed # type: ignore
        from IPython.terminal.ipapp import load_default_config # type: ignore
    except ImportError:
        from IPython.frontend.terminal.embed import InteractiveShellEmbed # type: ignore
        from IPython.frontend.terminal.ipapp import load_default_config # type: ignore

    def wrapper(namespace=namespace, banner=""):
        config = load_default_config()
        # Always use .instance() to ensure _instance propagation to all parents
        # this is needed for <TAB> completion works well for new imports
        # and clear the instance to always have the fresh env
        # on repeated breaks like with inspect_response()
        InteractiveShellEmbed.clear_instance()
        shell = InteractiveShellEmbed.instance(
            banner1=banner, user_ns=namespace, config=config)
        shell()

    return update_wrapper(wrapper, _embed_ipython_shell)


def _embed_bpython_shell(namespace={}, banner=""):
    """Start a bpython shell"""
    import bpython # type: ignore

    def wrapper(namespace=namespace, banner=""):
        bpython.embed(locals_=namespace, banner=banner)

    return update_wrapper(wrapper, _embed_bpython_shell)


def _embed_ptpython_shell(namespace={}, banner=""):
    """Start a ptpython shell"""
    import ptpython.repl # type: ignore

    def wrapper(namespace=namespace, banner=""):
        ptpython.repl.embed(locals=namespace)

    return update_wrapper(wrapper, _embed_ptpython_shell)


def _embed_ptipython_shell(namespace={}, banner=""):
    """Start an ptipython Shell"""
    from ptpython.ipython import InteractiveShellEmbed, load_default_config # type: ignore

    def wrapper(namespace=namespace, banner=""):
        config = load_default_config()
        # Always use .instance() to ensure _instance propagation to all parents
        # this is needed for <TAB> completion works well for new imports
        # and clear the instance to always have the fresh env
        # on repeated breaks like with inspect_response()
        InteractiveShellEmbed.clear_instance()
        shell = InteractiveShellEmbed.instance(
            banner1=banner, user_ns=namespace, config=config)
        shell()

    return update_wrapper(wrapper, _embed_ptipython_shell)


def _embed_standard_shell(namespace={}, banner=""):
    """Start a standard python shell"""
    import code

    try:
        # readline module is only available on unix systems
        import readline
    except ImportError:
        pass
    else:
        import rlcompleter  # noqa: F401
        readline.parse_and_bind("tab: complete")

    def wrapper(namespace=namespace, banner=""):
        code.interact(banner=banner, local=namespace)

    return update_wrapper(wrapper, _embed_standard_shell)


if __import__("sys").version_info >= (3, 6):
    odict = dict
else:
    from collections import OrderedDict as odict

DEFAULT_PYTHON_SHELLS = odict([
    ("ptipython", _embed_ptipython_shell),
    ("ipython",   _embed_ipython_shell),
    ("ptpython",  _embed_ptpython_shell),
    ("bpython",   _embed_bpython_shell),
    ("python",    _embed_standard_shell),
])

PYTHON_SHELL_REQUIREMENTS = odict([
    ("ptipython", ("ptpython", "ipython")),
    ("ipython",   ("ipython",)),
    ("ptpython",  ("ptpython",)),
    ("bpython",   ("bpython",)),
])


def get_current_shell():
    return __shell__


def list_shells():
    """List all registered shells, return a dictionary of shell names 
    and Installed flags (True: installed, False: otherwise)
    """
    shells = {}
    for k in DEFAULT_PYTHON_SHELLS:
        try:
            DEFAULT_PYTHON_SHELLS[k]()
        except ImportError:
            shells[k] = False
        else:
            shells[k] = True
    return shells


def get_shell_embed_func(shells=None, shell_embed_mapping=None):
    """Return the first acceptable shell-embed function
    from a given list of shell names.
    """
    if shells is None:  # list, preference order of shells
        shells = DEFAULT_PYTHON_SHELLS.keys()
    if shell_embed_mapping is None:  # available embeddable shells
        shell_embed_mapping = DEFAULT_PYTHON_SHELLS.copy()
    for shell in shells:
        if shell in shell_embed_mapping:
            try:
                # function test: run all setup code (imports),
                # but dont fall into the shell
                return shell, shell_embed_mapping[shell]()
            except ImportError:
                continue


def start_python_console(
    namespace=None, banner="", shells=None, shell_embed_mapping=None,
):
    """Start Python console bound to the given namespace.
    Readline support and tab completion will be used on Unix, if available.
    """
    global __shell__
    if namespace is None:
        namespace = {}

    try:
        selected_shell = get_shell_embed_func(shells, shell_embed_mapping)
        if selected_shell is None:
            raise RuntimeError('Could not get console')
        shell, shell_ebf = selected_shell
        if shell_ebf is not None:
            __shell__ = shell
            shell_ebf(namespace=namespace, banner=banner)
    except SystemExit:  # raised when using exit() in python code.interact
        pass


def start_specific_python_console(namespace=None, banner="", shell=None):
    """Start Python console bound to the given namespace.
    Readline support and tab completion will be used on Unix, if available.
    """
    if shell is None:
        return start_python_console(namespace, banner)
    else:
        if shell not in DEFAULT_PYTHON_SHELLS:
            raise NotImplementedError('No shell %r added' % shell)
        try:
            DEFAULT_PYTHON_SHELLS[shell]()
        except ImportError:
            if __name__ == "__main__":
                from pip_tool import pip_install # type: ignore
            else:
                from .pip_tool import pip_install
            pip_install(*PYTHON_SHELL_REQUIREMENTS[shell])
        return start_python_console(namespace, banner, (shell,))


if __name__ == "__main__":
    from argparse import ArgumentParser

    from colored import colored # type: ignore

    ap = ArgumentParser(
        description='Start Python Interactive REPL Environment. If not specified '
                    '(means all is specified), or more than one is specified, '
                    'tries to use the first available shell in the specified shells, '
                    'in the order of %(shells)s.'
                    % {'shells' : (' > '.join(colored(sh, attrs=['bold']) 
                                              for sh in DEFAULT_PYTHON_SHELLS))})
    for shell in DEFAULT_PYTHON_SHELLS:
        ap.add_argument(
            '--'+shell, action='store_true', dest=shell,
            help='Tells me to use Interactive REPL Environment: ' + colored(shell, attrs=['bold']))

    args = ap.parse_args()
    shell_ = next((k for k, v in args.__dict__.items() if v), None)
    start_specific_python_console(shell=shell_)

