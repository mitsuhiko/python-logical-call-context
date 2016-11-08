# python-logical-call-context

A repository for experiments with logical call contexts in Python.
The idea is that this stuff moves into contextlib which is why the
examples assume it's there and the code monkeypatches on import.

Examples:

```python
from contextlib import get_call_context

# Returns the current call context
ctx = get_call_context()

# Isolate some calls
from contextlib import isolated_call_context
with isolated_call_context():
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

What you can do with the call context:

```python
# Sets some data
ctx.set_data('key', 'value')

# Sets some data but mark it so that it cannot cross a thread
# or something similar which would require external synchronization.
ctx.set_data('key', 'value', sync=False)

# Set some data so that it does not pass over to isolated contexts
# (these contexts are created with `isolated_call_context` and set up
# a new logical call context.
ctx.set_data('werkzeug.request', ..., local=True)

# Looks up stored data (or raise a LookupError)
ctx.get_data('key')

# Looks up stored data or return a default
ctx.get_data('key', default=None)

# Deletes some data
ctx.del_data('key')

# Return the current logical key (a hashable object)
ctx.logical_key

# Return the current concurrency key (a hashable object)
ctx.key

# Nest the context (throws away local modifications later)
with ctx.nested():
    ...
```

Other things patched:

```python
from threading import get_thread_call_context
from asyncio import get_task_call_context
```
