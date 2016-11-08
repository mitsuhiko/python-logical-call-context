import asyncio
import threading
import contextlib

from weakref import WeakKeyDictionary

from .threads import get_thread_call_context


_local = threading.local()


def set_task_call_context(task, ctx):
    """Binds the given call context to the current asyncio task."""
    try:
        contexts = _local.asyncio_contexts
    except AttributeError:
        _local.asyncio_contexts = contexts = WeakKeyDictionary()
    contexts[task] = ctx
    return ctx


def get_task_call_context(create=False):
    """Returns the call context associated with the current task."""
    try:
        loop = asyncio.get_event_loop()
    except (AssertionError, RuntimeError):
        return

    task = asyncio.Task.current_task(loop=loop)
    if task is None:
        return

    try:
        return _local.asyncio_contexts[task]
    except (AttributeError, LookupError):
        ctx = None

    if not create:
        return

    ctx = contextlib.new_call_context(parent=get_thread_call_context())
    return set_task_call_context(task, ctx)


def patch_asyncio():
    # asyncio support
    ensure_future = asyncio.ensure_future

    def better_ensure_future(coro_or_future, *, loop=None):
        ctx = contextlib.get_call_context()
        task = ensure_future(coro_or_future, loop=loop)
        new_ctx = contextlib.new_call_context(name='Task-0x%x' % id(task), parent=ctx)
        set_task_call_context(task, new_ctx)
        return task

    asyncio.ensure_future = better_ensure_future
    asyncio.tasks.ensure_future = better_ensure_future
    asyncio.get_task_call_context = get_task_call_context
