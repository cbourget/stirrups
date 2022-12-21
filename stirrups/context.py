from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

from .injection import (
    Factory,
    Injectable,
    Injector,
    Instance,
    ItemType,
    Provider,
    injectable_factory,
)


ContextType = TypeVar('ContextType', bound='Context')


class Context:
    injector: Injector

    def __init__(self, *args: Any, **kwargs: Any):
        self.local_provider = Provider()
        self.local_provider.register(
            Instance(self),
            aslist=False,
            force=False,
            name=None,
            iface=self.__class__,
        )

    def mount(self, *, providers: Optional[List[Provider]] = None):
        providers = providers or []
        self.injector = Injector([self.local_provider, *providers], self)

    def register(
        self,
        injectable: Injectable[Any],
        *,
        aslist: bool = False,
        force: bool = False,
        name: Optional[str] = None,
        iface: Optional[Any] = None,
    ):
        provider = self.local_provider
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
        )

    def resolve(
        self,
        factory: Callable[..., ItemType],
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None
    ) -> ItemType:
        args = args or []
        kwargs = kwargs or {}
        return self.injector.resolve(
            injectable_factory(factory, cache=False),
            args=[*args],
            kwargs={**kwargs}
        )

    def get(
        self,
        iface: Type[ItemType],
        *,
        name: Optional[str] = None,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None
    ) -> ItemType:
        args = args or []
        kwargs = kwargs or {}
        return self.injector.get(
            iface,
            name=name,
            args=[*args],
            kwargs={**kwargs}
        )

    def get_list(
        self,
        iface: Type[ItemType],
        *,
        name: Optional[str] = None,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None
    ) -> List[ItemType]:
        args = args or []
        kwargs = kwargs or {}
        return self.injector.get_list(
            iface,
            name=name,
            args=[*args],
            kwargs={**kwargs}
        )
