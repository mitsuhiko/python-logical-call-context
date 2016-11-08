from .aio import get_task_call_context
from .threads import get_thread_call_context


providers = [
    get_task_call_context,
]


def register(func):
    """Registers an unified provider."""
    providers.append(func)
    return func


def get_call_context():
    """Returns the current call context."""
    for provider in providers:
        rv = provider(create=True)
        if rv is not None:
            return rv
    return get_thread_call_context(create=True)
