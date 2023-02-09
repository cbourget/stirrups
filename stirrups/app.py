import inspect

from typing import Any, Dict, Callable, Iterable, Optional, Type, Union

from .context import ContextType
from .exceptions import (
    AppMountedError,
    AppNotMountedError,
    ItemNotFound,
    IncludeModuleError,
)
from .injection import (
    Factory,
    Injectable,
    Instance,
    Provider,
    Registry,
    injectable_factory
)


ROOT = '__root'


class App:

    def __init__(
        self,
        mount='mount',
    ):
        self._mount = mount
        self._mounted = False
        self._providers = Registry[Provider]()
        self._includes = []

    def register(
        self,
        injectable: Injectable[Any],
        *,
        aslist: bool = False,
        force: bool = False,
        name: Optional[str] = None,
        iface: Optional[Any] = None,
        scope: Optional[str] = None
    ):
        if self._mounted:
            raise AppMountedError()

        provider = self._get_scope_provider(scope or ROOT)
        provider.register(
            injectable,
            name=name,
            iface=iface,
            force=force,
            aslist=aslist
        )

    def instance(
        self,
        item: Union[Any, Injectable[Any]],
        *,
        aslist: bool = False,
        force: bool = False,
        name: Optional[str] = None,
        iface: Optional[Any] = None,
        scope: Optional[str] = None
    ):
        if isinstance(item, Instance):
            injectable = item
        else:
            injectable = Instance(item)

        self.register(
            injectable,
            aslist=aslist,
            force=force,
            name=name,
            iface=iface,
            scope=scope
        )

    def factory(
        self,
        item: Union[Callable[..., Any], Factory[Any]],
        *,
        aslist: bool = False,
        force: bool = False,
        cache: bool = True,
        name: Optional[str] = None,
        iface: Optional[Any] = None,
        scope: Optional[str] = None
    ):
        if isinstance(item, Injectable):
            injectable = item
        else:
            injectable = injectable_factory(
                item,
                cache=cache
            )
        return self.register(
            injectable,
            aslist=aslist,
            force=force,
            name=name,
            iface=iface,
            scope=scope
        )

    def create_context(
        self,
        context_cls: Type[ContextType],
        *,
        scopes: Optional[Iterable[str]] = None,
        args: Optional[Iterable[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> ContextType:
        if not self._mounted:
            raise AppNotMountedError()

        scopes = set([ROOT] + list(scopes or []))
        providers = [
            self._get_scope_provider(scope) for scope in scopes
        ]

        args = list(args) if args else []
        kwargs = dict(kwargs) if kwargs else {}
        context = context_cls(*args, **kwargs)
        context.mount(providers=providers)

        return context

    def include(self, path: str, *args: Any, **kwargs: Any):
        if self._mounted:
            raise AppMountedError()

        if path.startswith('.'):
            origin = inspect.stack()[1]
            here = inspect.getmodule(origin[0])
            assert here is not None
            path = '{}{}'.format(here.__name__, path)

        mount_name = self._mount
        module = __import__(path, globals(), locals(), [mount_name], 0)
        try:
            mount = getattr(module, mount_name)
        except AttributeError:
            raise IncludeModuleError(module, mount_name)

        mount(self, *args, **kwargs)
        self._includes.append(path)

    def mount(self):
        self._mounted = True

    def _get_scope_provider(self, scope: str) -> Provider:
        try:
            provider = self._providers.get(scope)
        except ItemNotFound:
            provider = Provider(scope)
            self._providers.register(
                provider,
                scope,
                aslist=False,
                force=False,
            )

        return provider
