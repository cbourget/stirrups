from typing import Any, Union


class StirrupsError(Exception):
    pass


class IncludeModuleError(StirrupsError):

    def __init__(self, module: object, mount: str):
        super().__init__(
            'Expected to find a method named "{}" in module "{}".'
            ' The module cannot be included.'.format(
                mount,
                module
            )
        )
        self.module = module
        self.mount = mount


class ContextNotMountedError(StirrupsError):

    def __init__(self):
        super().__init__(
            'Context is not mounted. Call context.mount() before proceeding.'
        )


class InjectionError(StirrupsError):

    def __init__(self, iface: Any, *, key: Union[str, None]):
        msg = f'Failed to inject: {str(iface)}'
        if key:
            msg = f'{msg} with key: {key}'
        super().__init__(f'{msg}.')
        self.iface = iface
        self.key = key


class DependencyInjectionError(StirrupsError):

    def __init__(self, key: str, iface: Any):
        super().__init__(
            'Failed to inject dependency: {}: {}.'.format(key, str(iface))
        )
        self.iface = iface


class BadSignature(StirrupsError):

    def __init__(self, arg: str):
        super().__init__(
            'Argument "{}" is not annotated. '
            'Can\'t inject dependency.'.format(arg)
        )


class ItemExists(StirrupsError):

    def __init__(self, key: str):
        super().__init__(
            'An item is already registered under that key: {}. '
            'Use force=true to override'.format(key)
        )
        self.key = key


class ItemNotFound(StirrupsError):

    def __init__(self, key: str):
        super().__init__('No item found at key: {}'.format(key))
        self.key = key


class WrapperDescriptorError(Exception):
    pass
