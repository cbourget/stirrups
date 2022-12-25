import abc
import dataclasses
import inspect

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_type_hints
)

from .exceptions import (
    BadSignature,
    DependencyInjectionError,
    InjectionError,
    ItemExists,
    ItemNotFound,
    WrapperDescriptorError
)
from .logging import logger
from .utils import param_is_positionnal, param_is_variable

if TYPE_CHECKING:
    from .context import Context


ItemType = TypeVar('ItemType')


def _get_param_value(
    param: inspect.Parameter,
    iface: Any,
    context: 'Context'
) -> Any:
    name = param.name
    if not iface:
        raise BadSignature(name)

    try:
        value = _get_value_from_context(iface, context)
    except InjectionError:
        raise DependencyInjectionError(name, iface)

    return value


def _get_value_from_context(iface: Any, context: 'Context') -> Any:
    from .context import Context
    if inspect.isclass(iface) \
            and issubclass(iface, Context) or iface == Context:
        value = context
    else:
        value = context.get(iface)

    return value


class Injectable(Generic[ItemType], metaclass=abc.ABCMeta):
    item: Any

    @abc.abstractmethod
    def __call__(
        self,
        context: 'Context',
        args: List,
        kwargs: Dict
    ) -> ItemType:
        pass

    def get_cache_key(
        self,
        args: List,
        kwargs: Dict
    ) -> Union[str, None]:
        return None


class Instance(Injectable[ItemType]):
    def __init__(self, instance: ItemType):
        self.item = instance

    def __call__(
        self,
        context: 'Context',
        args: List,
        kwargs: Dict
    ) -> ItemType:
        return self.item


class Factory(Injectable[ItemType]):

    def __init__(
        self,
        factory: Callable[..., ItemType],
        *,
        cache: bool
    ):
        self.item = factory
        self.cache = cache

    def get_cache_key(
        self,
        args: List,
        kwargs: Dict
    ) -> Union[str, None]:
        if not self.cache:
            return None
        return str(self.item).replace('.', ':').replace('\'', '')


class FunctionFactory(Factory[ItemType]):

    def __init__(
        self,
        factory: Callable[..., ItemType],
        *,
        cache: bool
    ):
        super().__init__(factory, cache=cache)
        self.params = self._compute_params()

    def __call__(
        self,
        context: 'Context',
        args: List,
        kwargs: Dict
    ) -> ItemType:
        func = self.item
        self._inject_func_params(args, kwargs, context)
        return func(*args, **kwargs)

    def _compute_params(self) -> List[Tuple[inspect.Parameter, Any]]:
        func = self.item
        try:
            hints = get_type_hints(func)
        except TypeError:
            func_name = func.__name__
            logger.warn(
                f'Failed to retrieve type hints from function {func_name}',
                exc_info=True
            )
            hints = {}

        signature = inspect.signature(func)
        params = list(signature.parameters.values())
        computed = []
        for param in params:
            try:
                iface = hints[param.name]
            except KeyError:
                iface = None
            computed.append((param, iface))
        return computed

    def _inject_func_params(
        self,
        args: List,
        kwargs: Dict,
        context: 'Context'
    ):
        params = self.params
        args_count = len(args)

        for index, (param, iface) in enumerate(params):
            if index < args_count:
                continue

            is_positional = param_is_positionnal(param)
            if not is_positional and param.name in kwargs:
                continue

            if iface is None and param_is_variable(param):
                continue

            try:
                value = _get_param_value(param, iface, context)
            except BadSignature as exc:
                if len(params) == 1 and not args:
                    value = context
                else:
                    raise exc
            except WrapperDescriptorError:
                continue

            if is_positional:
                args.append(value)
            else:
                kwargs[param.name] = value


class ClassFactory(Factory[ItemType]):

    def __init__(
        self,
        factory: Callable[..., ItemType],
        *,
        cache: bool
    ):
        super().__init__(factory, cache=cache)
        self.params = self._compute_params()
        self.hints = self._compute_class_hints()

    def __call__(
        self,
        context: 'Context',
        args: List,
        kwargs: Dict
    ) -> ItemType:
        cls = self.item
        self._inject_constructor_params(args, kwargs, context)

        instance = cls(*args, **kwargs)
        self._inject_class_hints(instance, context)

        post_init = getattr(instance, '__post_init__', None)
        if post_init:
            post_init()

        return instance

    def _compute_params(self) -> List[Tuple[inspect.Parameter, Any]]:
        cls = self.item
        mro = inspect.getmro(cls)
        constructor = mro[0].__init__
        signature = inspect.signature(constructor)
        try:
            hints = get_type_hints(constructor)
        except TypeError:
            class_name = cls.__name__
            logger.warn(
                f'Failed to retrieve type hints from class {class_name}',
                exc_info=True
            )
            hints = {}

        params = [
            param for param in signature.parameters.values()
            if param.name != 'self'
        ]
        computed = []
        for param in params:
            try:
                iface = hints[param.name]
            except KeyError:
                iface = None
            computed.append((param, iface))
        return computed

    def _compute_class_hints(self) -> Dict[str, Any]:
        # TODO: Should injectable params be defined as such?
        cls = self.item
        try:
            hints = get_type_hints(cls)
        except TypeError:
            class_name = cls.__name__
            logger.warn(
                f'Failed to retrieve type hints from class {class_name}',
                exc_info=True
            )
            hints = {}
        return hints

    def _inject_constructor_params(
        self,
        args: List,
        kwargs: Dict,
        context: 'Context'
    ):
        params = self.params
        args_count = len(args)

        for index, (param, iface) in enumerate(params):
            if index < args_count:
                continue

            is_positional = param_is_positionnal(param)
            if not is_positional and param.name in kwargs:
                continue

            if iface is None and param_is_variable(param):
                continue

            try:
                value = _get_param_value(
                    param,
                    iface,
                    context
                )
            except WrapperDescriptorError:
                continue

            if is_positional:
                args.append(value)
            else:
                kwargs[param.name] = value

    def _inject_class_hints(
        self,
        instance: object,
        context: 'Context'
    ):
        for key, iface in self.hints.items():
            if getattr(instance, key, None):
                continue

            try:
                value = _get_value_from_context(iface, context)
            except InjectionError:
                pass
            else:
                setattr(instance, key, value)


class DataclassFactory(Factory[ItemType]):

    def __init__(
        self,
        factory: Callable[..., ItemType],
        *,
        cache: bool
    ):
        super().__init__(factory, cache=cache)
        self.hints = self._compute_dataclass_hints()

    def __call__(
        self,
        context: 'Context',
        args: List,
        kwargs: Dict
    ) -> ItemType:
        datacls = self.item
        self._inject_dataclass_hints(kwargs, context)
        return datacls(**kwargs)

    def _compute_dataclass_hints(self) -> Dict[str, Any]:
        datacls = self.item
        fields = dataclasses.fields(datacls)
        return {field.name: field.type for field in fields}

    def _inject_dataclass_hints(
        self,
        kwargs: Dict,
        context: 'Context'
    ):
        for key, iface in self.hints.items():
            if key in kwargs:
                continue

            try:
                arg = context.get(iface)
            except InjectionError:
                pass
            else:
                kwargs[key] = arg


def injectable_factory(
    factory: Callable[..., Any],
    cache: bool,
) -> Factory:
    if dataclasses.is_dataclass(factory):
        injectable_cls = DataclassFactory
    elif inspect.isclass(factory):
        injectable_cls = ClassFactory
    else:
        injectable_cls = FunctionFactory
    return injectable_cls(factory, cache=cache)


class Registry(Generic[ItemType]):

    def __init__(self):
        self._items = {}

    def get(self, key: str) -> ItemType:
        try:
            return self._items[key]
        except KeyError:
            raise ItemNotFound(key)

    def get_list(self, key: str) -> List[ItemType]:
        try:
            items = self._items[key]
        except KeyError:
            raise ItemNotFound(key)

        assert isinstance(items, list)
        return items

    def get_all(self) -> List[ItemType]:
        return list(self._items.values())

    def register(
        self,
        item: ItemType,
        key: str,
        *,
        force: bool,
        aslist: bool,
    ) -> str:
        try:
            current_value = self._items[key]
        except KeyError:
            self._items[key] = item if not aslist else [item]
            return key

        if current_value and not force and not aslist:
            raise ItemExists(key)

        if aslist and isinstance(current_value, list):
            current_value.append(item)
        else:
            self._items[key] = item

        return key

    def unregister(self, key: str):
        try:
            del self._items[key]
        except KeyError:
            pass

    def inspect(self) -> Dict[str, ItemType]:
        return self._items


class Provider(Generic[ItemType]):

    def __init__(self):
        self._injectables = Registry[Injectable]()

    def get(
        self,
        iface: Type[ItemType],
        *,
        name: Union[str, None]
    ) -> Injectable[ItemType]:
        key = name or self._generate_key(iface)
        return self._injectables.get(key)

    def get_list(
        self,
        iface: Type[ItemType],
        *,
        name: Union[str, None]
    ) -> List[Injectable[ItemType]]:
        key = name or self._generate_key(iface)
        return self._injectables.get_list(key)

    def register(
        self,
        injectable: Injectable,
        *,
        aslist: bool,
        force: bool,
        name: Union[str, None],
        iface: Union[Any, None]
    ):
        iface = iface or injectable.item
        key = name or self._generate_key(iface)
        return self._injectables.register(
            injectable,
            key,
            force=force,
            aslist=aslist
        )

    def _generate_key(self, iface: Any) -> str:
        if inspect.isclass(iface):
            base = iface.__name__
        else:
            base = str(iface)
        return base.replace('.', ':').replace('\'', '')

    def inspect(self) -> Dict[str, Injectable]:
        return self._injectables.inspect()


class Injector(Generic[ItemType]):

    def __init__(self, providers: List[Provider], context: 'Context'):
        self._providers = providers
        self._context = context
        self._cached = Registry()

    def get(
        self,
        iface: Type[ItemType],
        *,
        name: Union[str, None],
        args: List[Any],
        kwargs: Dict[str, Any]
    ) -> ItemType:
        for provider in self._providers:
            try:
                return self._inject(
                    provider.get(iface, name=name),
                    args,
                    kwargs
                )
            except ItemNotFound:
                pass

        raise InjectionError(iface, name=name)

    def get_list(
        self,
        iface: Type[ItemType],
        *,
        name: Union[str, None],
        args: List[Any],
        kwargs: Dict[str, Any]
    ) -> List[ItemType]:
        for provider in self._providers:
            try:
                return [
                    self._inject(
                        injectable,
                        args,
                        kwargs
                    )
                    for injectable in provider.get_list(iface, name=name)
                ]
            except ItemNotFound:
                pass

        raise InjectionError(iface, name=name)

    def _cache(self, key: str, instance: ItemType):
        self._cached.register(
            Instance(instance),
            key,
            force=False,
            aslist=False
        )

    def _get_from_cache(
        self,
        key: str
    ) -> Injectable[ItemType]:
        return self._cached.get(key)

    def _inject(
        self,
        injectable: Injectable[ItemType],
        args: List[Any],
        kwargs: Dict[str, Any]
    ) -> ItemType:
        key = injectable.get_cache_key(args, kwargs)
        if key:
            try:
                return self.resolve(
                    self._get_from_cache(key),
                    args,
                    kwargs
                )
            except ItemNotFound:
                pass

        instance = self.resolve(injectable, args, kwargs)
        if key:
            self._cache(key, instance)

        return instance

    def resolve(
        self,
        injectable: Injectable[ItemType],
        args: List[Any],
        kwargs: Dict[str, Any]
    ) -> ItemType:
        return injectable(self._context, args, kwargs)

    def inspect(self) -> Dict[str, Injectable]:
        result = {}
        for provider in self._providers:
            result.update(provider.inspect())
        return result
