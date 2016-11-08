def __patch():
    from .common import patch_contextlib
    from .threads import patch_threads
    from .aio import patch_asyncio
    patch_contextlib()
    patch_threads()
    patch_asyncio()


__patch()
del __patch
