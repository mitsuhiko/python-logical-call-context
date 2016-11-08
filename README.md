# python-logical-call-context

A repository for experiments with logical call contexts in Python.
The idea is that this stuff moves into contextlib which is why the
examples assume it's there and the code monkeypatches on import.

Examples::

```
from contextlib import get_call_context

# Returns the current call context
ctx = get_call_context()

# Isolate some calls
from contextlib import isolate_call_context
with isolate_call_context():
    ...

# Register a new context provider
from contextlib import register_context_provider, new_call_context
@register_context_provider
def get_my_context(create=False):
    rv = get_current_context_object()
    if rv is not None:
        return rv
    if not create:
        return
    rv = new_call_context(parent=...)
    bind_the_new_context(rv)
    return rv
```
