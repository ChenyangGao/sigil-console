# FORK FROM: https://github.com/glenfant/stopit

__all__ = ['TimeoutException', 'TimeoutContextState', 'BaseTimeout', 
           'SignalTimeout', 'ThreadingTimeout']

import ctypes
import enum
import functools
import signal
import sys
import threading
import warnings

from abc import abstractmethod, ABC
from typing import Union


class TimeoutException(Exception):
    """Raised when the block under context management takes longer to complete
    than the allowed maximum timeout value.
    """
    pass


TimeoutContextState = enum.IntEnum(
    'TimeoutContextState', 
    'INITIALIZED, EXECUTING, TIMED_OUT, INTERRUPTED, CANCELED', 
    start=0, 
)


class BaseTimeout(ABC):
    """Context manager for limiting in the time the execution of a block
    :param seconds: ``float`` or ``int`` duration enabled to run the context
      manager block
    :param suppress_exc: ``False`` if you want to manage the
      ``TimeoutException`` (or any other) in an outer ``try ... except``
      structure. ``True`` (default) if you just want to check the execution of
      the block with the ``state`` attribute of the context manager.
    """
    state: TimeoutContextState

    def __init__(self, seconds: Union[int, float], suppress_exc: bool = False):
        self.seconds = seconds
        self.suppress_exc = suppress_exc
        self.state = TimeoutContextState.INITIALIZED

    def __bool__(self) -> bool:
        return self.state in (TimeoutContextState.INITIALIZED, TimeoutContextState.EXECUTING)

    def __repr__(self) -> str:
        return '<%s object at 0x%x in state: %r>' % (
            type(self).__qualname__, id(self), self.state)

    def __enter__(self):
        self.state = TimeoutContextState.EXECUTING
        self.setup_interrupt()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is TimeoutException:
            if self.state is not TimeoutContextState.TIMED_OUT:
                self.state = TimeoutContextState.INTERRUPTED
                self.suppress_interrupt()
            return self.suppress_exc
        else:
            if exc_type is None:
                self.state = TimeoutContextState.INITIALIZED
            self.suppress_interrupt()

    def cancel(self):
        "In case in the block you realize you don't need anymore limitation"
        self.state = TimeoutContextState.CANCELED
        self.suppress_interrupt()

    @abstractmethod
    def setup_interrupt(self):
        "Installs/initializes the feature that interrupts the executed block"
        raise NotImplementedError

    @abstractmethod
    def suppress_interrupt(self):
        "Removes/neutralizes the feature that interrupts the executed block"
        raise NotImplementedError


class SignalTimeout(BaseTimeout):
    """Context manager for limiting in the time the execution of a block
    using signal.SIGALRM Unix signal.
    See :class:`stopit.utils.BaseTimeout` for more information
    """
    def __init__(self, seconds: Union[int, float], suppress_exc: bool = False):
        trunc_seconds = int(seconds)
        if trunc_seconds != seconds:
            warnings.warn('NOTE: alarm delay for signal MUST be int, '
                          '`seconds` has been truncated automatically')
        super().__init__(trunc_seconds, suppress_exc)

    def handle_timeout(self, signum, frame):
        self.state = TimeoutContextState.TIMED_OUT
        raise TimeoutException('Block exceeded maximum timeout '
                               'value (%d seconds).' % self.seconds)

    def setup_interrupt(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def suppress_interrupt(self):
        signal.alarm(0)
        signal.signal(signal.SIGALRM, signal.SIG_DFL)


def async_raise(target_tid, exception):
    """Raises an asynchronous exception in another thread.
    Read http://docs.python.org/c-api/init.html#PyThreadState_SetAsyncExc
    for further enlightenments.
    :param target_tid: target thread identifier
    :param exception: Exception class to be raised in that thread
    """
    # Ensuring and releasing GIL are useless since we're not in C
    # gil_state = ctypes.pythonapi.PyGILState_Ensure()
    ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(target_tid),
                                                     ctypes.py_object(exception))
    # ctypes.pythonapi.PyGILState_Release(gil_state)
    if ret == 0:
        raise ValueError("Invalid thread ID {}".format(target_tid))
    elif ret > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(target_tid), None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


class ThreadingTimeout(BaseTimeout):
    """Context manager for limiting in the time the execution of a block
    using asynchronous threads launching exception.
    See :class:`stopit.utils.BaseTimeout` for more information
    """
    def __init__(self, seconds: Union[int, float], suppress_exc: bool = False):
        super().__init__(seconds, suppress_exc)
        self.target_tid = threading.current_thread().ident
        self.timer = None  # PEP8

    def stop(self):
        """Called by timer thread at timeout. Raises a Timeout exception in the
        caller thread
        """
        self.state = TimeoutContextState.TIMED_OUT
        async_raise(self.target_tid, TimeoutException)

    # Required overrides
    def setup_interrupt(self):
        """Setting up the resource that interrupts the block
        """
        self.timer = threading.Timer(self.seconds, self.stop)
        self.timer.start()

    def suppress_interrupt(self):
        """Removing the resource that interrupts the block
        """
        self.timer.cancel()


# TODO: 参考 async_timeout
class AsyncTimeout(BaseTimeout):
    pass

