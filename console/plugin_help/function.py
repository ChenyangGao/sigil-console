#!/usr/bin/env python3
# coding: utf-8

from __future__ import annotations

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 10)
__all__ = [
    "abort", "exit", "dump_wrapper", "load_wrapper", "get_container", 
    "run_env", "load_script", "run_plugin", 
]

import builtins
import re
import subprocess
import sys

from contextlib import contextmanager
from copy import deepcopy
from os import _exit, path as _path, environ
from os.path import abspath
from pickle import load as pickle_load, dump as pickle_dump
from runpy import run_path
from tempfile import NamedTemporaryFile
from traceback import print_exc
from typing import cast, Final, Iterable, Mapping, Optional
from zipfile import ZipFile

try:
    from lxml.etree import parse as parse_xml_file # type: ignore
except ImportError:
    from xml.etree.ElementTree import parse as parse_xml_file

try:
    from wrapper import Wrapper # type: ignore
    from bookcontainer import BookContainer # type: ignore
    from inputcontainer import InputContainer # type: ignore
    from outputcontainer import OutputContainer # type: ignore
    from validationcontainer import ValidationContainer # type: ignore
except ImportError:
    pass

from plugin_util.colored import colored
from plugin_util.dictattr import DictAttr
from plugin_util.run import ctx_load, run_file
from plugin_util.temporary import temp_list


_SYSTEM_IS_WINDOWS: Final[bool] = __import__("platform").system() == "Windows"


def abort() -> None:
    "Abort console to discard all changes."
    open(environ["PLUGIN_ABORT_FILE"], "wb").close()
    _exit(1)


def exit() -> None:
    "Exit console for no more operations."
    dump_wrapper()
    _exit(0)


def dump_wrapper(wrapper: Optional[Wrapper] = None) -> None:
    "Dump wrapper to file."
    if wrapper is None:
        wrapper = __import__("plugin_help").WRAPPER
    pickle_dump(wrapper, open(environ["PLUGIN_DUMP_FILE"], "wb"))


def load_wrapper() -> Wrapper:
    "Load wrapper from file."
    wrapper = pickle_load(open(environ["PLUGIN_DUMP_FILE"], "rb"))
    __import__("plugin_help").WRAPPER = wrapper
    return wrapper


@contextmanager
def _ctx_wrapper():
    dump_wrapper()
    yield __import__("plugin_help").WRAPPER
    load_wrapper()


def get_container(wrapper=None) -> Mapping:
    "Get the sigil containers."
    if wrapper is None:
        wrapper = __import__("plugin_help").WRAPPER
    return DictAttr(
        wrapper    = wrapper, 
        edit       = BookContainer(wrapper), 
        input      = InputContainer(wrapper), 
        output     = OutputContainer(wrapper), 
        validation = ValidationContainer(wrapper), 
    )


def run_env(forcible_execution: bool = False, /) -> None:
    'Run env.py, to inject some configuration and global variables'
    if forcible_execution:
        try:
            delattr(__import__("builtins"), "PLUGIN_SETTING")
        except AttributeError:
            pass
    run_file(environ["PLUGIN_STARTUP_FILE"], sys._getframe(1).f_globals)


def load_script(
    path: str, 
    globals: Optional[dict] = None, 
    include_single: bool = False, 
    include__dunder: bool = False, 
    include__special__: bool = False, 
    _cre=re.compile('^(?P<special>__.+__)|(?P<dunder>__.*)|(?P<single>_.*)|(?P<normal>.*)$', re.S | re.U), 
) -> Optional[dict]:
    '''To execute or register some script.

    :param path: Path of a script (a file or folder).
    :param globals: The global namespace used to execute the script.
    :param include_single: 
        Determine whether to include these key-value pairs that their keys are like _var.
    :param include__dunder: 
        Determine whether to include these key-value pairs that their keys are like __var.
    :param include__special__: 
        Determine whether to include these key-value pairs that their keys are like __var__.

    :return: `dict` (that is for updating) means that the script has been executed, 
             `None` means that the script (as a package) has been appended to `sys.path`.

    TIPS: It will deal with the following situations separately:
        1. A file (e.g., suffixed by .py or .pyz), or a folder (or a .zip file) 
           with __main__.py, will be executed directly.
        2. A folder (or .zip file) without __main__.py will be appended to sys.path.
    Tips: In the result dictionary of the script (result is the return value of `runpy.run_path`), 
          all the key-value pairs, their keys are not excluded and their values are different from 
          those of the same key in `globals`, were updated to `globals`.
    '''
    if not _path.exists(path):
        raise FileNotFoundError('No such file or directory: %r' % path)

    as_sys_path: bool = False
    if _path.isdir(path):
        as_sys_path = not _path.exists(_path.join(path, '__main__.py'))
    elif path.endswith('.zip'):
        as_sys_path = '__main__.py' not in ZipFile(path).NameToInfo

    if as_sys_path:
        sys.path.append(path)
        return None

    if globals is None:
        globals = sys._getframe(1).f_globals

    def check_group(name):
        group = _cre.fullmatch(name).lastgroup
        if group == 'single':
            return include_single
        elif group == 'dunder':
            return include__dunder
        elif group == 'special':
            return include__special__
        else:
            return True

    sentinel = object()
    ret: dict = cast(dict, run_path(path, globals, '__main__'))
    updating_dict: dict
    if '__all__' in ret:
        updating_dict = {
            k: v for k in ret['__all__']
            if k in ret and (v := ret[k]) and v is not globals.get(k, sentinel)
        }
    else:
        updating_dict = {
            k: v for k, v in ret.items() 
            if check_group(k) and v is not globals.get(k, sentinel)
        }
    globals.update(updating_dict)
    return updating_dict


def _startup(
    namespace: Optional[dict] = None, 
    startups: Optional[Iterable[str]] = None, 
    errors: Optional[str] = None, 
) -> dict:
    if namespace is None:
        namespace = {}

    if startups is None:
        startups = cast(tuple[str], tuple(PLUGIN_SETTING["config"].get("startup", ())))
    else:
        startups = cast(tuple[str], tuple(startups))
    if not startups:
        return namespace

    if errors is None:
        errors = cast(str, str(PLUGIN_SETTING["config"].get("errors", "ignore")))

    success_count: int = 0
    error_count: int = 0
    keys_updated: set = set()
    for i, path in enumerate(startups, 1):
        try:
            ret = load_script(path, namespace)
            if ret is None:
                print(colored('◉ APPENDED', 'yellow', attrs=['bold', 'blink']), '➜', i, path)
            else:
                keys_updated |= ret.keys()
                print(colored('◉ LOADED', 'green', attrs=['bold', 'blink']), '➜', i, path)
            success_count += 1
        except BaseException:
            print(colored('◉ ERROR', 'red', attrs=['bold', 'blink']), '➜', i, path)
            if errors == 'raise':
                raise
            print_exc()
            if errors == 'stop':
                print(colored(
                    '🤗 %s SUCCESSES, 🤯 AN ERROR OCCURRED, 🤕 SKIPPING THE REMAINING %s STARTUPS' 
                    % (success_count, len(startups) - success_count - 1), 
                    'red', attrs=['bold', 'blink']))
                break
            error_count += 1
    else:
        if error_count:
            print(colored('😀 PROCESSED ALL, 🤗 %s SUCCESSES, 😷 %s ERRORS FOUND' % (success_count, error_count), 
                          'yellow', attrs=['bold', 'blink']))
        else:
            print(colored('😀 PROCESSED ALL, 🤗 %s SUCCESSES, 😏 NO ERRORS FOUND' % success_count, 
                          'green', attrs=['bold', 'blink']))

    if keys_updated:
        print('The following keys had been updated\n\t|_', tuple(keys_updated))
        keys_updated_but_removed = keys_updated - namespace.keys()
        if keys_updated_but_removed:
            print('But these keys were eventually removed\n\t|_', 
                  tuple(keys_updated_but_removed))

    return namespace


def _run_plugin(file_or_dir: str, bc: BookContainer):
    container = get_container(deepcopy(bc._w))

    target_dir: str
    target_file: str
    if _path.isdir(file_or_dir):
        target_dir = file_or_dir
        target_file = _path.join(file_or_dir, 'plugin.py')
    else:
        target_file = file_or_dir
        target_dir = _path.dirname(target_file)

    try:
        et = parse_xml_file(_path.join(target_dir, 'plugin.xml'))
    except FileNotFoundError:
        plugin_type = 'edit'
    else:
        plugin_type = et.findtext('type', 'edit')

    if plugin_type not in ('edit', 'input', 'validation', 'output'):
        raise ValueError(
            'Invalid plugin type %r' % plugin_type
        ) from NotImplementedError

    with ctx_load(
            target_file, 
            wdir=target_dir, 
            prefixes_not_clean=(
                *set(__import__('site').PREFIXES), 
                PLUGIN_SETTING["path"]['sigil_package_dir'], 
            ), 
        ) as mod, \
        temp_list(sys.argv) as av, \
        _ctx_wrapper() \
    :
        sys.modules['__main__'] = __import__('launcher')
        sys.modules[getattr(mod, '__name__')] = mod
        av[:] = [PLUGIN_SETTING["path"]['laucher_file'], 
                 PLUGIN_SETTING["path"]['ebook_root'], 
                 PLUGIN_SETTING["path"]['outdir'], 
                 plugin_type, target_file]

        bk = container[plugin_type]
        try:
            ret = getattr(mod, 'run')(bk)
            if ret == 0 or type(ret) is not int:
                dump_wrapper(bk._w)
            else:
                # Restore to unmodified (no guarantee of right result)
                dump_wrapper(bc._w)
        except BaseException:
            # Restore to unmodified (no guarantee of right result)
            dump_wrapper(bc._w)
            raise
        return ret


def run_plugin(
    file_or_dir: str, 
    bc: Optional[BookContainer] = None,
    run_in_process: bool = False,
    executable: str = sys.executable,
):
    '''Running a Sigil plug-in

    :param file_or_dir: Path of Sigil plug-in folder or script file.
    :param bc: `BookContainer` object. 
        If it is None (the default), will be found in caller's globals().
        `BookContainer` object is an object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    :param run_in_process: Determine whether to run the program in a child process.

    :return: If `run_in_process` is True, return `subprocess.CompletedProcess`, else 
             return the return value of the plugin function.
    '''
    if not _path.exists(file_or_dir):
        raise FileNotFoundError('No such file or directory: %r' % file_or_dir)

    file_or_dir = _path.abspath(file_or_dir)

    if run_in_process:
        with NamedTemporaryFile(suffix='.py', mode='w', encoding='utf-8') as f, _ctx_wrapper():
            f.write(
f'''#!/usr/bin/env python3
# coding: utf-8

exec(open({environ["PLUGIN_STARTUP_FILE"]!r}, encoding="utf-8").read(), globals())

try:
    retcode = __import__("plugin_help").function._run_plugin({file_or_dir!r}, bc)
    print("plugin %r \\n\\t |_ return ➜ %r" % (r'{file_or_dir}', retcode))
    if type(retcode) is not int:
        retcode = 0
except BaseException:
    retcode = -1

if retcode != 0:
    __import__("atexit").unregister(plugin.dump_wrapper)
    __import__("os")._exit(retcode)
''')
            f.flush()
            return subprocess.run(
                [executable, f.name], 
                check=True, shell=_SYSTEM_IS_WINDOWS)
    else:
        if bc is None:
            try:
                bc = cast(BookContainer, sys._getframe(1).f_globals['bc'])
            except KeyError:
                bc = cast(BookContainer, _EDIT_CONTAINER)

        return _run_plugin(file_or_dir, bc)

