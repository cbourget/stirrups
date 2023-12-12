import pytest

from stirrups.app import App
from stirrups.context import Context


@pytest.fixture(scope='function')
def app():
    return App()


@pytest.fixture(scope='function')
def context():
    context = Context(providers=[])
    return context
