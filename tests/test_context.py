import pytest

from stirrups.app import Context
from stirrups.exceptions import DependencyInjectionError


class TestRegistration:

    class _IClass:
        pass

    class _ClassA:
        pass

    def test_register_instance(self, context: Context):
        a = self._ClassA()
        context.instance(a, iface=self._IClass)
        assert context.get(self._IClass) == a


class TestInjection:

    class _DepsA:
        pass

    class _DepsB:
        pass

    class _IClass:
        pass

    class _ClassA:
        def __init__(self, v: int, deps_a: 'TestInjection._DepsA'):
            self.v = v
            self.deps_a = deps_a

    class _ClassB:
        def __init__(self, deps_b: 'TestInjection._DepsB'):
            self.deps_b = deps_b

    def test_inject_factory_function(self, context: Context):
        def deps_a_factory() -> TestInjection._DepsA:
            return self._DepsA()

        def a_factory(
            v: int,
            deps_a: TestInjection._DepsA,
        ) -> TestInjection._ClassA:
            return self._ClassA(v, deps_a)

        context.factory(deps_a_factory, iface=self._DepsA)
        context.factory(a_factory, iface=self._IClass)

        a = context.get(self._IClass, args=[1])
        deps_a = context.get(self._DepsA)
        assert isinstance(a, self._ClassA)
        assert a.v == 1
        assert a.deps_a == deps_a

    def test_inject_factory_class_with_local_dependency(
        self,
        context: Context
    ):
        context.factory(TestInjection._ClassB)

        # DepsB is a dependency of ClassB but DepsB is not
        # registered
        with pytest.raises(DependencyInjectionError):
            context.get(self._ClassB)

        # Here, DepsB is registered directly on the context before
        # getting ClassB
        context.factory(self._DepsB)
        b = context.get(self._ClassB)
        assert isinstance(b, self._ClassB)
