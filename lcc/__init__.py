def __patch():
    from .common import patch_sys, patch_threads
    from .aio import patch_asyncio
    patch_sys()
    patch_threads()
    patch_asyncio()


__patch()
del __patch


from .common import isolated_call_context
