import kombu.exceptions
import pytest

import kombu_pyamqp_threadsafe


@pytest.fixture()
def connection(rabbitmq_dsn):
    connection = kombu_pyamqp_threadsafe.KombuConnection(rabbitmq_dsn, default_channel_pool_size=1)
    assert not connection.connected
    yield connection
    connection.close()


def test__empty_pool__release__not_close(
    connection,
    get_kombu_resource_all_objects,
    get_kombu_resource_acquired_objects,
    get_kombu_resource_free_objects,
):
    """Test channel will be reused instead reopen (closing)"""
    assert not connection.connected

    pool_size = len(get_kombu_resource_all_objects(connection.default_channel_pool))
    assert pool_size == 0

    with connection.default_channel_pool.acquire() as channel:
        assert channel.is_open
        pool_free_size = len(get_kombu_resource_free_objects(connection.default_channel_pool))
        assert pool_free_size == 0

        assert get_kombu_resource_acquired_objects(
            connection.default_channel_pool
        ) == get_kombu_resource_all_objects(connection.default_channel_pool)

    assert connection.connected

    # still opened
    assert channel.is_open

    # channel returned to pool
    # and ready to use
    assert (
        get_kombu_resource_free_objects(connection.default_channel_pool)
        == get_kombu_resource_all_objects(connection.default_channel_pool)
        == [channel]
    )
    pool_size = len(get_kombu_resource_all_objects(connection.default_channel_pool))
    assert pool_size == 1


def test_channel_closed__release__drop(
    connection,
    get_kombu_resource_all_objects,
):
    """Test closed channel will be dropped when released to pool"""
    assert not connection.connected

    pool_size = len(get_kombu_resource_all_objects(connection.default_channel_pool))
    assert pool_size == 0

    with connection.default_channel_pool.acquire() as channel:
        assert channel.is_open
        channel.close()

    assert not channel.is_open
    assert connection.connected

    # pool empty again
    pool_size = len(get_kombu_resource_all_objects(connection.default_channel_pool))
    assert pool_size == 0

    # check we can open new channel
    with connection.default_channel_pool.acquire() as new_channel:
        assert new_channel.is_open


def test_channel_limit_exceed__error(
    connection,
    get_kombu_resource_all_objects,
    get_kombu_resource_acquired_objects,
    get_kombu_resource_free_objects,
):
    """Test ChannelPool can be limited and raise exception when limit exceeded (by default)"""
    with connection.default_channel_pool.acquire() as channel1:
        assert channel1.is_open

        with pytest.raises(kombu.exceptions.ChannelLimitExceeded, match="1"):
            with connection.default_channel_pool.acquire() as channel2:
                pass

        assert get_kombu_resource_all_objects(connection.default_channel_pool) == [channel1]
        assert get_kombu_resource_acquired_objects(connection.default_channel_pool) == [channel1]
        assert get_kombu_resource_free_objects(connection.default_channel_pool) == []

    assert get_kombu_resource_all_objects(connection.default_channel_pool) == [channel1]
    assert get_kombu_resource_acquired_objects(connection.default_channel_pool) == []
    assert get_kombu_resource_free_objects(connection.default_channel_pool) == [channel1]


def test_ctx_manager__exception__release(
    connection,
    get_kombu_resource_all_objects,
    get_kombu_resource_acquired_objects,
    get_kombu_resource_free_objects,
):
    """Test channel will be returned to pool when ctx-manager exit"""
    assert get_kombu_resource_all_objects(connection.default_channel_pool) == []

    with pytest.raises(RuntimeError, match="test"):
        with connection.default_channel_pool.acquire() as channel:
            raise RuntimeError("test")

    assert get_kombu_resource_all_objects(connection.default_channel_pool) == [channel]
    assert get_kombu_resource_acquired_objects(connection.default_channel_pool) == []
    assert get_kombu_resource_free_objects(connection.default_channel_pool) == [channel]
