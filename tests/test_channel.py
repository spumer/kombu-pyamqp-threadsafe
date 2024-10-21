import inspect
import ssl

import pytest

import kombu_pyamqp_threadsafe


@pytest.fixture()
def connection(rabbitmq_dsn):
    connection = kombu_pyamqp_threadsafe.KombuConnection(rabbitmq_dsn, default_channel_pool_size=1)
    assert not connection.connected
    yield connection
    connection.close()


def test_ssl_error__channel_collected(request, mocker, connection):
    """Test connection and channel will be closed when SSLError occurred in channel send_method"""

    def _sslerr_frame_writer(*args, **kwargs):
        frame = inspect.stack()[1].frame
        frame.f_locals["transport"].close()  # ensure TCPTransport really closed
        raise ssl.SSLEOFError("EOF occurred")

    pool = connection.default_channel_pool

    with connection.default_channel_pool.acquire() as channel:
        channel_collect_spy = mocker.spy(channel, "collect")
        channel.connection.frame_writer = _sslerr_frame_writer

        with pytest.raises(ssl.SSLEOFError):
            channel.queue_declare(queue=request.node.name, durable=False, auto_delete=True)

        assert not channel.is_open
        assert channel_collect_spy.called

    assert not connection.connected
    assert connection.default_channel_pool is pool

    # Test connection auto-restore
    with pool.acquire() as _:
        pass

    assert connection.connected

    # ChannelPool did not know about connection problems
    # but when try to acquire it's ensure connection
    assert connection.default_channel_pool is pool
