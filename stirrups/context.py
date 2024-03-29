from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    TypedDict,
    TypeVar,
    Union,
)

from .injection import (
    Factory,
    Injectable,
    InjectableMeta,
    Injector,
    Instance,
    ItemType,
    Provider,
    generate_iface_key,
    injectable_factory,
)


ContextType = TypeVar('ContextType', bound='Context')

InspectContextDictItemDep = TypedDict(
    'InspectContextDictItemDep',
    key=str,
    param=str,
)

InspectContextDictItem = TypedDict(
    'InspectContextDictItem',
    key=str,
    item=Union[str, List[str]],
    deps=List[InspectContextDictItemDep]
)


class InspectContextResult:

    def __init__(self, injectables: Dict[str, InjectableMeta]):
        self.injectables = injectables

    def to_dict(self) -> Dict[str, InspectContextDictItem]:
        dic = {}
        for key, injectable_meta in self.injectables.items():
            item = injectable_meta['item']
            if isinstance(item, list):
                dic[key] = [
                    self._item_to_dict(key, i)
                    for i in item
                ]
                item = [str(i) for i in item]
            else:
                dic[key] = self._item_to_dict(key, item)
        return dic

    def _item_to_dict(
        self,
        key: str,
        item: Injectable
    ) -> InspectContextDictItem:
        return {
            'key': key,
            'item': str(item),
            'deps': [
                {
                    'param': param,
                    'key': generate_iface_key(iface)
                }
                for param, iface in item.dependencies
                if iface is not None
            ]
        }


class Context:
    injector: Injector

    def __init__(
        self,
        *,
        providers: Optional[List[Provider]] = None,
        **kwargs: Any
    ):
        providers = providers or []
        self.local_provider = Provider('local')
        self.local_provider.register(
            Instance(self),
            aslist=False,
            force=False,
            key=None,
            iface=self.__class__,
        )
        self.injector = Injector([self.local_provider, *providers], self)

    def register(
        self,
        injectable: Injectable[Any],
        *,
        aslist: bool = False,
        force: bool = False,
        key: Optional[str] = None,
        iface: Optional[Any] = None,
    ):
        provider = self.local_provider
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
    ):
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
            key=key,
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
        key: Optional[str] = None,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None
    ) -> ItemType:
        args = args or []
        kwargs = kwargs or {}
        return self.injector.get(
            iface,
            key=key,
            args=[*args],
            kwargs={**kwargs}
        )

    def get_list(
        self,
        iface: Type[ItemType],
        *,
        key: Optional[str] = None,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None
    ) -> List[ItemType]:
        args = args or []
        kwargs = kwargs or {}
        return self.injector.get_list(
            iface,
            key=key,
            args=[*args],
            kwargs={**kwargs}
        )

    def inspect(self) -> InspectContextResult:
        providers = self.injector._providers
        unique_injectables = {}
        for provider in reversed(providers):
            injectables = provider.describe_injectables()
            for injectable_meta in injectables:
                unique_injectables[injectable_meta['key']] = injectable_meta
        return InspectContextResult(unique_injectables)
