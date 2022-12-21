import pytest

from stirrups.app import App
from stirrups.context import Context


@pytest.fixture(scope='function')
def app():
    return App()


@pytest.fixture(scope='function')
def context():
    context = Context()
    context.mount()
    return context
