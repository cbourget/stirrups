import pytest

from dataclasses import dataclass

from stirrups.app import App
from stirrups.context import Context
from stirrups.exceptions import (
    DependencyInjectionError,
    ItemExists,
    InjectionError,
    IncludeModuleError
)


class TestCreateContext:

    class _Context(Context):
        pass

    def test_create_context(self, app: App):
        context = app.create_context(self._Context)
        assert isinstance(context, self._Context)


class TestRegistration:

    class _IClass:
        pass

    class _ClassA:
        pass

    class _ClassB:
        pass

    @dataclass
    class _DataClassA:
        pass

    def test_register_instance(self, app: App):
        a = self._ClassA()
        app.instance(a, iface=self._IClass)
        context = app.create_context(Context)
        assert context.get(self._IClass) == a

    def test_register_instance_with_key(self, app: App):
        key = 'a'
        a = self._ClassA()
        app.instance(a, iface=self._IClass, key=key)
        context = app.create_context(Context)
        assert context.get(self._IClass, key=key) == a

    def test_register_factory_function(self, app: App):
        def a_factory(context: Context) -> TestRegistration._ClassA:
            return self._ClassA()

        app.factory(a_factory, iface=self._IClass)
        context = app.create_context(Context)
        a = context.get(self._IClass)
        assert isinstance(a, self._ClassA)

    def test_register_factory_class(self, app: App):
        app.factory(self._ClassA, iface=self._IClass)
        context = app.create_context(Context)
        a = context.get(self._IClass)
        assert isinstance(a, self._ClassA)

    def test_register_factory_dataclass(self, app: App):
        app.factory(self._DataClassA, iface=self._IClass)
        context = app.create_context(Context)
        a = context.get(self._IClass)
        assert isinstance(a, self._DataClassA)

    def test_register_in_scope(self, app: App):
        scope = 'test'

        def a_factory() -> TestRegistration._ClassA:
            return self._ClassA()

        app.factory(
            a_factory,
            iface=self._IClass,
            scope=scope
        )
        _context = app.create_context(Context, scopes=[scope])
        a = _context.get(self._IClass)
        assert isinstance(a, self._ClassA)

        context = app.create_context(Context)
        with pytest.raises(InjectionError):
            context.get(self._IClass)

    def test_register_aslist(self, app: App):
        app.factory(self._ClassA, iface=self._IClass, aslist=True)
        app.factory(self._ClassB, iface=self._IClass, aslist=True)
        context = app.create_context(Context)
        values = context.get_list(self._IClass)
        assert len(values) == 2

    def test_register_no_iface(self, app: App):
        app.factory(self._ClassA)
        context = app.create_context(Context)
        a = context.get(self._ClassA)
        assert isinstance(a, self._ClassA)

    def test_register_force(self, app: App):
        app.factory(self._ClassA, iface=self._IClass)
        with pytest.raises(ItemExists):
            app.factory(self._ClassB, iface=self._IClass)

        app.factory(self._ClassB, iface=self._IClass, force=True)
        context = app.create_context(Context)
        b = context.get(self._IClass)
        assert isinstance(b, self._ClassB)


class TestInjection:

    class _DepsA:
        pass

    class _IClass:
        pass

    class _ClassA:
        def __init__(self, v: int, deps_a: 'TestInjection._DepsA'):
            self.v = v
            self.deps_a = deps_a

    class _ClassB:
        class_a: 'TestInjection._ClassA'

        def __init__(self, deps_a: 'TestInjection._DepsA'):
            self.deps_a = deps_a

    def test_inject_factory_function(self, app: App):
        def deps_a_factory() -> TestInjection._DepsA:
            return self._DepsA()

        def a_factory(
            v: int,
            deps_a: TestInjection._DepsA,
        ) -> TestInjection._ClassA:
            return self._ClassA(v, deps_a)

        app.factory(deps_a_factory, iface=self._DepsA)
        app.factory(a_factory, iface=self._IClass)

        context = app.create_context(Context)
        a = context.get(self._IClass, args=[1])
        deps_a = context.get(self._DepsA)
        assert isinstance(a, self._ClassA)
        assert a.v == 1
        assert a.deps_a == deps_a

    def test_inject_factory_function_without_annotation(self, app: App):
        def deps_a_factory() -> TestInjection._DepsA:
            return self._DepsA()

        def a_factory(context) -> TestInjection._ClassA:
            return self._ClassA(1, context.get(self._DepsA))

        app.factory(deps_a_factory, iface=self._DepsA)
        app.factory(a_factory, iface=self._IClass)

        context = app.create_context(Context)
        a = context.get(self._IClass)
        deps_a = context.get(self._DepsA)
        assert isinstance(a, self._ClassA)
        assert a.v == 1
        assert a.deps_a == deps_a

    def test_intect_factory_class(self, app: App):
        app.factory(TestInjection._DepsA, iface=self._DepsA)
        app.factory(TestInjection._ClassA)

        context = app.create_context(Context)
        a = context.get(self._ClassA, args=[1])
        deps_a = context.get(self._DepsA)
        assert isinstance(a, self._ClassA)
        assert a.v == 1
        assert a.deps_a == deps_a

    def test_inject_factory_class_with_annotations(self, app: App):
        app.factory(TestInjection._DepsA)
        app.factory(TestInjection._ClassA)
        app.factory(TestInjection._ClassB)

        context = app.create_context(Context)

        # ClassA is a dependency of ClassB but ClassA cannot be
        # injected without a value for its `v` param.
        with pytest.raises(DependencyInjectionError):
            context.get(self._ClassB)

        # Here, a is explicitely injected first then cached. This allows
        # b to be injected too. A different caching strategy could break this.
        a = context.get(self._ClassA, args=[1])
        b = context.get(self._ClassB)
        assert isinstance(b, self._ClassB)
        assert b.class_a == a


class TestInclude:

    def test_include_valid(self, app: App):
        app.include('stirrups')
        assert len(app._includes) == 1

    def test_include_invalid(self):
        app = App(mount='foo')
        with pytest.raises(IncludeModuleError):
            app.include('stirrups')
