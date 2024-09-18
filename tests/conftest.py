import os

import kombu.resource
import pytest
from kombu.utils.functional import lazy


@pytest.fixture()
def rabbitmq_username():
    return "guest"


@pytest.fixture()
def rabbitmq_password():
    return "guest"


@pytest.fixture()
def rabbitmq_hostname():
    if hostname := os.getenv("PYTEST_RABBITMQ_HOST"):
        return hostname

    return "127.0.0.1"


@pytest.fixture()
def rabbitmq_port():
    if port := os.getenv("PYTEST_RABBITMQ_PORT"):
        return int(port)

    return 5672


@pytest.fixture()
def rabbitmq_dsn(rabbitmq_username, rabbitmq_password, rabbitmq_hostname, rabbitmq_port):
    return f"amqp://{rabbitmq_username}:{rabbitmq_password}@{rabbitmq_hostname}:{rabbitmq_port}/"


@pytest.fixture(scope="session")
def get_kombu_resource_acquired_objects():
    def _inner(resource: kombu.resource.Resource) -> list:
        return list(resource._dirty)

    return _inner


@pytest.fixture(scope="session")
def get_kombu_resource_free_objects():
    def _inner(resource: kombu.resource.Resource) -> list:
        return [r for r in resource._resource.queue if not isinstance(r, lazy)]

    return _inner


@pytest.fixture(scope="session")
def get_kombu_resource_all_objects(
    get_kombu_resource_acquired_objects, get_kombu_resource_free_objects
):
    def _inner(resource: kombu.resource.Resource) -> list:
        return get_kombu_resource_acquired_objects(resource) + get_kombu_resource_free_objects(
            resource
        )

    return _inner
