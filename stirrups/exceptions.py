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


class AppMountedError(StirrupsError):

    def __init__(self):
        super().__init__(
            'App is already mounted and closed for registration.'
        )


class AppNotMountedError(StirrupsError):

    def __init__(self):
        super().__init__(
            'App is not mounted. Call app.mount() before proceeding.'
        )


class InjectionError(StirrupsError):

    def __init__(self, iface: Any, *, name: Union[str, None]):
        msg = f'Failed to inject: {str(iface)}'
        if name:
            msg = f'{msg} with name: {name}'
        super().__init__(f'{msg}.')
        self.iface = iface
        self.name = name


class DependencyInjectionError(StirrupsError):

    def __init__(self, name: str, iface: Any):
        super().__init__(
            'Failed to inject dependency: {}: {}.'.format(name, str(iface))
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
