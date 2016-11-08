import threading
import contextlib


_local = threading.local()


def set_thread_call_context(ctx):
    """Binds the given call context to the current thread."""
    _local.context = ctx
    return ctx


def get_thread_call_context(create=False):
    """Returns the current thread's call context."""
    rv = getattr(_local, 'context', None)
    if rv is not None:
        return rv
    if not create:
        return
    return set_thread_call_context(contextlib.new_call_context())


def patch_threads():
    thread_init = threading.Thread.__init__
    thread_bootstrap = threading.Thread._bootstrap

    def better_thread_init(self, *args, **kwargs):
        self.__outer_call_ctx = contextlib.get_call_context()
        return thread_init(self, *args, **kwargs)

    def better_thread_bootstrap(self):
        set_thread_call_context(contextlib.new_call_context(
            name=self.name, parent=self.__outer_call_ctx))
        return thread_bootstrap(self)

    threading.Thread.__init__ = better_thread_init
    threading.Thread._bootstrap = better_thread_bootstrap
