import inspect

from typing import Any, Dict, Callable, Iterable, Optional, Type, Union

from .context import ContextType
from .exceptions import ItemNotFound, IncludeModuleError
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
    """
    An App instance is where the components of a project are registered.
    There is generally a single instance of App per project.
    """

    def __init__(
        self,
        mount='mount',
    ):
        self._mount = mount
        self._providers = Registry[Provider]()
        self._includes = []

    def register(
        self,
        injectable: Injectable[Any],
        *,
        aslist: bool = False,
        force: bool = False,
        key: Optional[str] = None,
        iface: Optional[Any] = None,
        scope: Optional[str] = None
    ):
        """Register an injectable component.

        Args:
            injectable (Injectable[Any]): An injectable
            aslist (bool, optional):
                Whether the injectable should be registered as a list.
                When true, multiple injectables may be registered on the
                same interface.
                Defaults to False.
            force (bool, optional):
                Force registration and override anything registered on the
                same interface.
                Defaults to False.
            key (Optional[str], optional):
                The registration key.
                If None is provided, a key is generated from the `iface`.
                Defaults to None.
            iface (Optional[Any], optional):
                An interface (or type) of the injectable.
                If provided, will be used to generate a registration key.
                If None is provided, a key is generated from the injectable.
                Defaults to None.
            scope (Optional[str], optional):
                The scope where the injectable is made available.
                Useful in conjunction with the `scopes` argument
                of the `create_context` method.
                Defaults to None.
        """
        provider = self._get_scope_provider(scope or ROOT)
        provider.register(
            injectable,
            key=key,
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
        key: Optional[str] = None,
        iface: Optional[Any] = None,
        scope: Optional[str] = None
    ):
        """Register an injectable instance.

        See `register` for more information regarding arguments.

        Args:
            item (Union[Any, Injectable[Any]]): Any object
        """

        if isinstance(item, Instance):
            injectable = item
        else:
            injectable = Instance(item)

        self.register(
            injectable,
            aslist=aslist,
            force=force,
            key=key,
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
        key: Optional[str] = None,
        iface: Optional[Any] = None,
        scope: Optional[str] = None
    ):
        """Register an injectable factory.

        See `register` for more information regarding arguments.

        Args:
            item (Union[Callable[..., Any], Factory[Any]]):
                A factory method, class or dataclass.
        """

        if isinstance(item, Injectable):
            injectable = item
        else:
            injectable = injectable_factory(
                item,
                cache=cache
            )
        self.register(
            injectable,
            aslist=aslist,
            force=force,
            key=key,
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
        """Create a context class.

        Registered components can be injected from a context with their
        own depedencies resolved.

        Args:
            context_cls (Type[ContextType]):
                The context class
            scopes (Optional[Iterable[str]], optional):
                If provided, only the components of those scopes will
                be available fore injection.
                Defaults to None.
            args (Optional[Iterable[Any]], optional):
                Arguments passed to the context class.
                Defaults to None.
            kwargs (Optional[Dict[str, Any]], optional):
                Keyword arguments passed to the context class.
                Defaults to None.

        Returns:
            ContextType: The context instance.
        """
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
        """Include a module and invoke the `mount` method
        of that module. Additional `*args` or `**kwargs` are passed
        along to the `mount` method.

        Args:
            path (str):
                The module's path. Can be absolute or relative.

        Raises:
            IncludeModuleError:
                Raised if the module doens't implement the `mount` method.
        """
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

    def _get_scope_provider(self, scope: str) -> Provider:
        """Get the provider for a named scope.

        Args:
            scope (str): The scope's name

        Returns:
            Provider: The provider instance.
        """
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
