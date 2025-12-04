import inspect
import os
import ssl

import kombu.resource
import pytest
from kombu.utils.functional import lazy


@pytest.fixture
def rabbitmq_username():
    return "guest"


@pytest.fixture
def rabbitmq_password():
    return "guest"


@pytest.fixture
def rabbitmq_hostname():
    if hostname := os.getenv("PYTEST_RABBITMQ_HOST"):
        return hostname

    return "127.0.0.1"


@pytest.fixture
def rabbitmq_port():
    if port := os.getenv("PYTEST_RABBITMQ_PORT"):
        return int(port)

    return 5672


@pytest.fixture
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


@pytest.fixture
def connection(rabbitmq_dsn):
    import kombu_pyamqp_threadsafe

    connection = kombu_pyamqp_threadsafe.KombuConnection(rabbitmq_dsn, default_channel_pool_size=1)
    assert not connection.connected
    yield connection
    connection.close()


@pytest.fixture
def queue_name(request, rabbitmq_dsn):
    import kombu_pyamqp_threadsafe

    queue_name = request.node.name

    conn = kombu_pyamqp_threadsafe.KombuConnection(rabbitmq_dsn)
    kombu.Queue(queue_name, channel=conn).delete()

    yield queue_name

    kombu.Queue(queue_name, channel=conn).delete()
    conn.close()


def _sslerr_frame_writer(*args, **kwargs):
    frame = inspect.stack()[1].frame
    frame.f_locals["transport"].close()  # ensure TCPTransport really closed
    raise ssl.SSLEOFError("EOF occurred")


@pytest.fixture
def make_channel_raise_sslerror():
    def inner(channel):
        channel.connection.frame_writer = _sslerr_frame_writer

    return inner
