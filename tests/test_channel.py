import ssl

import pytest


def test_ssl_error__channel_collected(
    request,
    mocker,
    connection,
    get_kombu_resource_all_objects,
    make_channel_raise_sslerror,
):
    """Test connection and channel will be closed when SSLError occurred in channel send_method"""
    pool = connection.default_channel_pool

    with pool.acquire() as channel:
        channel_collect_spy = mocker.spy(channel, "collect")
        make_channel_raise_sslerror(channel)

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

    assert len(get_kombu_resource_all_objects(connection.default_channel_pool)) == 1


def test_default_channel__collect__open_new(connection):
    """Test Connection.default_channel will be reopened"""
    prev = connection.default_channel
    assert prev is not None

    connection.collect()
    assert not prev.is_open

    new = connection.default_channel
    assert new is not None
    assert prev is not new

    assert new.is_open
