import pytest
import asyncio
import threading
import contextlib


def test_basic_context():
    ctx = contextlib.get_call_context()
    ctx.set_data('foo', 42)
    assert ctx.get_data('foo') == 42
    ctx.unset_data('foo')

    with pytest.raises(LookupError):
        ctx.get_data('foo')


def test_context_nesting():
    ctx = contextlib.get_call_context()
    with ctx.nested():
        ctx.set_data('bar', 23)

    with pytest.raises(LookupError):
        ctx.get_data('bar')


def test_local_context_behavior():
    ctx = contextlib.get_call_context()
    ctx.set_data('foo', 23, local=True)

    with ctx.nested():
        assert ctx.get_data('foo') == 23

    rv = []
    def test_thread():
        rv.append(contextlib.get_call_context().get_data('foo', default=None))

    t = threading.Thread(target=test_thread)
    t.start()
    t.join()

    with contextlib.isolated_call_context():
        t = threading.Thread(target=test_thread)
        t.start()
        t.join()

    assert rv == [23, None]


def test_sync_data():
    ctx = contextlib.get_call_context()
    ctx.set_data('foo', 23, sync=False)

    rv = []
    rv.append(contextlib.get_call_context().get_data('foo', default=None))

    def test_thread():
        rv.append(contextlib.get_call_context().get_data('foo', default=None))

    t = threading.Thread(target=test_thread)
    t.start()
    t.join()

    assert rv == [23, None]


def test_async():
    ctx = contextlib.get_call_context()
    ctx.set_data('__locale__', 'en_US')

    rv = []

    async def x(val):
        ctx = contextlib.get_call_context()
        rv.append(ctx.get_data('__locale__'))
        ctx.set_data('__locale__', val)
        rv.append(ctx.get_data('__locale__'))

    asyncio.get_event_loop().run_until_complete(x('de_DE'))
    asyncio.get_event_loop().run_until_complete(x('fr_FR'))
    rv.append(ctx.get_data('__locale__'))

    assert rv == ['en_US', 'de_DE', 'en_US', 'fr_FR', 'en_US']
