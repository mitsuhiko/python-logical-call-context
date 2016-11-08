import os
import sys
import asyncio
import _thread
import threading

from weakref import WeakKeyDictionary
from contextlib import contextmanager
from collections import MutableMapping
from weakref import ref as weakref


_local = threading.local()
_missing = object()


class CallContextKey(object):
    """An immutable, hashable and comparable object to uniquely identify
    the call context.  This can be used by code to map data to a specific
    call context.
    """

    def __init__(self, name=None):
        self.name = name
        self.pid = os.getpid()
        self.tid = _thread.get_ident()

    def __repr__(self):
        return '<CallContextKey name=%r pid=%d tid=%d>' % (
            self.name,
            self.pid,
            self.tid,
        )


class LogicalCallContextKey(object):
    """Uniquely identifies a logical call context."""


class _ContextData(object):

    def __init__(self, value, key, logical_key, sync=True, local=False):
        self.value = value
        self.key = key
        self.logical_key = logical_key
        self.sync = sync
        self.local = local

    def unsafe_context_crossing(self, call_context):
        # Synchronous objects always cross safely 
        if self.sync:
            return False
        # If we cross over to another process the crossing is safe
        if self.key.pid != call_context.key.pid:
            return False
        # Otherwise the crossing is only safe if we are on the same
        # thread
        return self.key.tid != call_context.key.tid


class CallContext(object):
    """Represents the call context."""

    def __init__(self, name, parent=None):
        logical_key = None
        if parent is not None:
            data = parent._data.copy()
            if not parent.isolates:
                logical_key = parent.logical_key
        else:
            data = {}

        if logical_key is None:
            logical_key = LogicalCallContextKey()

        self.key = CallContextKey(name)
        self.logical_key = logical_key
        self.isolates = False
        self._data = data
        self._backup = None

    def __repr__(self):
        return '<CallContext name=%r id=0x%x>' % (
            self.key.name,
            id(self),
        )

    def __eq__(self, other):
        return self.__class__ is other.__class__ and \
            self.key == other.key

    def __ne__(self, other):
        return not self.__eq__(other)

    def get_data(self, name, *, default=_missing):
        """Returns the data for the given key.  By default if the key cannot
        be found a `LookupError` is raised.  If a default is provided it's
        returned instead.
        """
        try:
            cd = self._data.get(name)
            if cd is None:
                raise KeyError(name)

            # If the key is local pretend it never exists in this context
            if cd.local and cd.logical_key != self.logical_key:
                raise KeyError(name)

            # Do not let non sync values cross contexts
            if cd.unsafe_context_crossing(self):
                raise LookupError('The stored context data was created for '
                                  'a different context and cannot be shared '
                                  'because it was not marked as synchronous.')

            return cd.value
        except LookupError:
            if default is not _missing:
                return default
            raise

    def set_data(self, name, value, *, sync=True, local=False):
        """Sets a key to a given value.  By default the value is set nonlocal
        and sync which means that it shows up in any derived context.  If the
        value is set to ``sync=False`` the value will not be travelling to a
        context that would require external synchronization (eg: a different
        thread).  If the value is set to local with ``local=True`` the value
        will not travel to a context belonging to a different logical call
        context.
        """
        if self._backup is not None and name not in self._backup:
            self._backup[name] = self._data.get(name)
        self._data[name] = _ContextData(value, self.key, self.logical_key,
                                         sync=sync, local=local)

    def unset_data(self, name):
        """Deletes a key"""
        self._data[name] = None

    @contextmanager
    def nested(self):
        """Helper context manager to """
        backup = self._backup
        self._backup = {}
        try:
            yield
        finally:
            self._data.update(self._backup)
            self._backup = backup


def new_call_context(name=None, parent=None):
    """Creates a new call context which optionally is created from a given
    parent.
    """
    if name is None:
        name = threading.current_thread().name
    return CallContext(name, parent)


def _get_call_context():
    """Returns the current call context."""
    try:
        loop = asyncio.get_event_loop()
    except (AssertionError, RuntimeError):
        pass
    else:
        task = asyncio.Task.current_task(loop=loop)

        # If we have a task we look up the correct context 
        if task is not None:
            try:
                ctx = _local.asyncio_contexts[task]
            except (AttributeError, LookupError):
                ctx = None
            if ctx is not None:
                return ctx
            try:
                parent = _local.context
            except AttributeError:
                parent = None
            ctx = new_call_context(parent=parent)
            return set_task_call_context(task, ctx)

    # Final fallback, make a new context and bind it to the thread.
    try:
        return _local.context
    except AttributeError:
        return set_thread_call_context(new_call_context())


def set_thread_call_context(ctx):
    """Binds the given call context to the current thread."""
    _local.context = ctx
    return ctx


def set_task_call_context(task, ctx):
    """Binds the given call context to the current asyncio task."""
    try:
        contexts = _local.asyncio_contexts
    except AttributeError:
        _local.asyncio_contexts = contexts = WeakKeyDictionary()
    contexts[task] = ctx
    return ctx


@contextmanager
def isolated_call_context(isolate=True):
    """Context manager that temporarily isolates the call context.  This means
    that new contexts created out of the current context until the end of the
    context manager will be created isolated from the current one.  All values
    that are marked as "local" will be unavailable in the newly created call
    context.

    When a context is created while the parent is isolated a new logical call
    context will be created.

    Example::

        import contextlib

        with contextlib.isolated_call_context():
            ...
    """
    ctx = sys.get_call_context()
    old = ctx.isolates
    ctx.isolates = isolate
    try:
        yield
    finally:
        ctx.isolates = old


def __patch():
    # Hook us into the sys module
    sys.get_call_context = _get_call_context

    # Thread Support
    thread_init = threading.Thread.__init__
    thread_bootstrap = threading.Thread._bootstrap

    def better_thread_init(self, *args, **kwargs):
        self.__outer_call_ctx = sys.get_call_context()
        return thread_init(self, *args, **kwargs)

    def better_thread_bootstrap(self):
        set_thread_call_context(new_call_context(
            name=self.name, parent=self.__outer_call_ctx))
        return thread_bootstrap(self)

    threading.Thread.__init__ = better_thread_init
    threading.Thread._bootstrap = better_thread_bootstrap

    # asyncio support
    ensure_future = asyncio.ensure_future

    def better_ensure_future(coro_or_future, *, loop=None):
        ctx = _get_call_context()
        task = ensure_future(coro_or_future, loop=loop)
        new_ctx = new_call_context(name='Task-0x%x' % id(task), parent=ctx)
        set_task_call_context(task, new_ctx)
        return task

    asyncio.ensure_future = better_ensure_future
    asyncio.tasks.ensure_future = better_ensure_future


__patch()
del __patch
