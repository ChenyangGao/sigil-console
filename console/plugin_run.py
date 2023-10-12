#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__all__ = ["run"]

# TODO: Allow users to set the configuration of `pip`
# TODO: Allow users to create `venv`

from contextlib import contextmanager
from copy import deepcopy
from importlib import import_module
from os import chdir, environ, path as os_path
from typing import Final, Optional

from plugin_util.run import run_in_process
from plugin_help.console import CONSOLE_MAP


_IS_MACOS = __import__("platform").system() == "Darwin"
MUDULE_DIR: Final[str] = os_path.dirname(os_path.abspath(__file__))
CONFIG_JSON_FILE: Final[str] = os_path.join(MUDULE_DIR, "config.json")


def _import_all(mod_name):
    mod = import_module(mod_name)
    get = mod.__dict__.get
    return {k: get(k) for k in mod.__all__}


@contextmanager
def _ctx_conifg(bc):
    config = bc.getPrefs()
    default_config = config["default_config"] = {
        "console": "python", "errors": "ignore", "startup": [], 
        "terminal": "", "terminal_args": "", "terminal_wait": True, 
        "pip_index_url": "https://mirrors.aliyun.com/pypi/simple/", 
        "pip_trusted_host": "mirrors.aliyun.com", 
    }
    if "config" not in config:
        config["config"] = deepcopy(default_config)
    else:
        config["config"].update(
            (k, default_config[k])
            for k in default_config.keys() - config["config"].keys()
        )
    if "configs" not in config:
        config["configs"] = []
    yield config
    config.pop("default_config", None)
    bc.savePrefs(config)


def update_config_webui() -> dict:
    raise NotImplementedError


def update_config_tui() -> dict:
    raise NotImplementedError


def update_config_gui_tk(
    # Tips: After closing the `tkinter` GUI in Mac OSX, it will get stuck, 
    # so I specify to run the `tkinter` GUI in a new process.
    config: dict, 
    new_process: bool = _IS_MACOS, 
) -> dict:
    try:
        from plugin_util.xml_tkinter import TkinterXMLConfigParser
    except ImportError:
        __import__("traceback").print_exc(file=__import__("sys").stdout)
        print("WARNING:", "Probably cannot import `tkinter` module, skipping configuration...")
        return {}
    if new_process:
        config_new = run_in_process(update_config_gui_tk, config, False)
        config.clear()
        config.update(config_new)
        return config
    else:
        namespace = _import_all("plugin_util.tkinter_extensions")
        namespace.update(config=config, CONSOLES=list(CONSOLE_MAP))

        tkapp = TkinterXMLConfigParser(
            os_path.join(MUDULE_DIR, "plugin_src", "config.xml"), namespace)
        tkapp.start()
        return config


def update_config_gui_qt(new_process: bool = _IS_MACOS) -> dict:
    raise NotImplementedError


def run(bc) -> Optional[int]:
    with _ctx_conifg(bc) as config:
        config = update_config_gui_tk(config)["config"]

    laucher_file, ebook_root, outdir, _, target_file = __import__("sys").argv
    this_plugin_dir = os_path.dirname(target_file)
    sigil_package_dir = os_path.dirname(laucher_file)

    paths = dict(
        laucher_file      = laucher_file,
        sigil_package_dir = sigil_package_dir,
        this_plugin_dir   = this_plugin_dir,
        plugins_dir       = os_path.dirname(this_plugin_dir),
        ebook_root        = ebook_root,
        outdir            = outdir,
    )

    env = {}
    env["PLUGIN_OUTDIR"]       = outdir
    env["PLUGIN_DUMP_FILE"]    = os_path.join(outdir, "sigil_console.dump.pkl")
    env["PLUGIN_ABORT_FILE"]   = abort_file       = os_path.join(outdir, "sigil_console.abort")
    env["PLUGIN_STARTUP_FILE"] = startup_file     = os_path.join(outdir, "sigil_console_startup.py")
    env["PLUGIN_MAIN_FILE"]    = main_file        = os_path.join(this_plugin_dir, "plugin_main.py")
    env["PIP_INDEX_URL"]       = pip_index_url    = config["pip_index_url"]
    env["PIP_TRUSTED_HOST"]    = pip_trusted_host = config["pip_trusted_host"]
    env["PYTHONSTARTUP"]       = startup_file
    environ.update(env)

    open(startup_file, "w", encoding="utf-8").write(f"""\
#!/usr/bin/env python3
# coding: utf-8

import builtins

__import__("warnings").filterwarnings("ignore", category=DeprecationWarning)

if hasattr(builtins, "PLUGIN_SETTING"):
    if __name__ != "__init__":
        # Execution success information
        print('''
    🦶🦶🦶 Environment had been loaded, ignoring
''')
else:
    # Changing working directory
    __import__("os").chdir({outdir!r})

    # Setting os.environ
    __import__("os").environ.update({env!r})

    # Injecting module paths
    if {sigil_package_dir!r} not in __import__("sys").path:
        __import__("sys").path[:0] = [{sigil_package_dir!r}, {this_plugin_dir!r}]

    # Introducing global variables
    import plugin_help as plugin
    from plugin_help import editor
    bc = bk = __import__("bookcontainer").BookContainer(plugin.load_wrapper())

    # Injecting builtins variable: PLUGIN_SETTING
    from types import MappingProxyType
    PLUGIN_SETTING = builtins.PLUGIN_SETTING = MappingProxyType({{
        "config": MappingProxyType({config!r}), 
        "path": MappingProxyType({paths!r}), 
        "env": MappingProxyType({env!r}), 
    }})
    del MappingProxyType

    # Perform startup scripts
    if __name__ == "__main__":
        plugin.function._startup(globals())

    # Callback at exit
    __import__("atexit").register(plugin.dump_wrapper)

    # Wrapped exit function for idlelib
    try:
        if isinstance(exit, __import__("_sitebuiltins").Quitter):
            @staticmethod
            @__import__("functools").wraps(exit)
            def exit(*args, _exit=exit):
                plugin.dump_wrapper()
                _exit()
            exit = type("", (), {{"__repr__": lambda self: self(), "__call__": exit}})()
    except (NameError, ImportError):
        pass

    if __name__ != "__init__":
        # Execution success information
        print('''
    🎉🎉🎉 Environment loaded successfully
''')

del builtins
""")
    print("WARNING:", "Created startup file\n%r\n" %startup_file)

    chdir(outdir)

    import plugin_help as plugin

    wrapper = bc._w
    plugin.WRAPPER = wrapper
    plugin.dump_wrapper(bc._w)

    console = config.get("console")
    if console in ("qtconsole", "spyder", "idle", "idlex", "idlea", "thonny", "eric"):
        plugin.start_console(console)
    else:
        args = [__import__("sys").executable, main_file, "--startup", startup_file]
        if console:
            args.extend(("--console", console))
        kwds = {}
        if config.get("terminal"):
            kwds["app"] = config["terminal"]
        if config.get("terminal_args"):
            kwds["app_args"] = config["terminal_args"]
        kwds["wait"] = config.get("terminal_wait", True)
        from plugin_util.terminal import start_terminal
        start_terminal(args, **kwds)

    # check whether the console is aborted.
    if os_path.exists(abort_file):
        return 1

    bc._w = plugin.load_wrapper()

    return 0

