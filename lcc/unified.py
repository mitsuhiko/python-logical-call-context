from .aio import get_task_call_context
from .threads import get_thread_call_context


def get_call_context():
    """Returns the current call context."""
    rv = get_task_call_context(create=True)
    if rv is not None:
        return rv
    return get_thread_call_context(create=True)
