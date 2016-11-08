import asyncio

from weakref import WeakKeyDictionary

from .common import _local, get_call_context, new_call_context


def set_task_call_context(task, ctx):
    """Binds the given call context to the current asyncio task."""
    try:
        contexts = _local.asyncio_contexts
    except AttributeError:
        _local.asyncio_contexts = contexts = WeakKeyDictionary()
    contexts[task] = ctx
    return ctx


def patch_asyncio():
    # asyncio support
    ensure_future = asyncio.ensure_future

    def better_ensure_future(coro_or_future, *, loop=None):
        ctx = get_call_context()
        task = ensure_future(coro_or_future, loop=loop)
        new_ctx = new_call_context(name='Task-0x%x' % id(task), parent=ctx)
        set_task_call_context(task, new_ctx)
        return task

    asyncio.ensure_future = better_ensure_future
    asyncio.tasks.ensure_future = better_ensure_future
