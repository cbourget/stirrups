import inspect

from typing import Any, Dict, Callable, Iterable, Optional, Type, Union

from .context import Context, ContextType
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


class App:

    def __init__(
        self,
        mount='mount',
    ):
        self._mount = mount
        self._mounted = False
        self._providers = Registry()
        self._includes = []

    def register(
        self,
        injectable: Injectable[Any],
        *,
        aslist: bool = False,
        force: bool = False,
        name: Optional[str] = None,
        iface: Optional[Any] = None,
        context: Optional[Type['Context']] = None
    ):
        if self._mounted:
            raise AppMountedError()

        context = context or Context
        provider = self._get_context_provider(context)
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
        context: Optional[Type['Context']] = None
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
            context=context
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
        context: Optional[Type['Context']] = None
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
            context=context
        )

    def create_context(
        self,
        context_cls: Type[ContextType],
        *,
        ifaces: Optional[Iterable[Type['Context']]] = None,
        args: Optional[Iterable[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> ContextType:
        if not self._mounted:
            raise AppNotMountedError()

        context_ifaces = set([Context] + list(ifaces or [context_cls]))
        providers = [
            self._get_context_provider(iface) for iface in context_ifaces
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

    def _get_context_provider(self, ctx_iface: Type[Context]) -> Provider:
        ctx_iface = ctx_iface or Context
        key = self._generate_context_key(ctx_iface)
        try:
            provider = self._providers.get(key)
        except ItemNotFound:
            provider = Provider()
            self._providers.register(
                provider,
                key,
                aslist=False,
                force=False,
            )

        return provider

    def _generate_context_key(self, ctx_iface: Type[Context]) -> str:
        return str(ctx_iface).replace('.', ':').replace('\'', '')
