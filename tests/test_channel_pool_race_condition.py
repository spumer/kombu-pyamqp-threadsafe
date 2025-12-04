"""Test race condition fix in ThreadSafeChannel.close() and collect()."""

import unittest.mock


def test_channel_close__reentrant_calls__prevented(
    connection,
    mocker,
    get_kombu_resource_all_objects,
    get_kombu_resource_free_objects,
):
    """Test that re-entrant close() calls are prevented.

    This test verifies the fix for the race condition where:
    1. close() calls pool.release(self)
    2. pool.release() may trigger close_resource() which calls super().close()
    3. super().close() may trigger events that call close() again
    4. Without protection, this creates infinite recursion or double-release
    """
    pool = connection.default_channel_pool

    with pool.acquire() as channel:
        assert get_kombu_resource_all_objects(pool) == [channel]
        assert get_kombu_resource_free_objects(pool) == []

        # Spy on pool.release to track calls
        release_spy = mocker.spy(pool, "release")

        # Simulate re-entrant close by calling it multiple times
        channel.close()
        channel.close()  # Should be no-op due to _is_releasing flag
        channel.close()  # Should be no-op due to _is_releasing flag

        # pool.release should be called only once due to protection
        assert release_spy.call_count == 1
        assert release_spy.call_args_list == [unittest.mock.call(channel)]

        # Channel should be detached from pool after first close()
        assert channel.channel_pool is None

    # Channel should be in pool exactly once (not duplicated)
    assert get_kombu_resource_all_objects(pool) == [channel]
    assert get_kombu_resource_free_objects(pool) == [channel]


def test_channel_collect__double_release__prevented(
    connection,
    mocker,
    get_kombu_resource_all_objects,
    get_kombu_resource_free_objects,
):
    """Test that collect() doesn't cause double-release with close().

    This test verifies the fix for:
    1. close() detaches channel from pool before calling pool.release()
    2. collect() also detaches before calling super().collect()
    3. This prevents pool.release() being called twice
    """
    pool = connection.default_channel_pool

    channel = pool.acquire()
    assert get_kombu_resource_all_objects(pool) == [channel]
    assert get_kombu_resource_free_objects(pool) == []

    # Spy on pool.release to track calls
    release_spy = mocker.spy(pool, "release")

    # Manually call collect (simulating what super().close() might do)
    channel.collect()

    # pool.release should be called once from collect()
    assert release_spy.call_count == 1
    assert release_spy.call_args_list == [unittest.mock.call(channel)]

    # After collect(), channel is not usable, so it's dropped from pool
    assert not channel.is_usable()
    assert get_kombu_resource_all_objects(pool) == []
    assert get_kombu_resource_free_objects(pool) == []

    # Channel should be detached from pool after collect
    assert channel.channel_pool is None

    # Subsequent close() should not try to add unusable channel to pool again
    channel.close()

    # Still only one call to pool.release (no duplicate)
    assert release_spy.call_count == 1

    # Pool should remain empty (channel not duplicated)
    assert get_kombu_resource_all_objects(pool) == []
    assert get_kombu_resource_free_objects(pool) == []


def test_channel_close__pool_detachment__atomic(
    connection,
    mocker,
    get_kombu_resource_all_objects,
    get_kombu_resource_free_objects,
):
    """Test that channel is atomically detached from pool during close().

    This ensures that once close() starts, the channel cannot be
    released to pool again, even from re-entrant calls.
    """
    pool = connection.default_channel_pool

    channel = pool.acquire()
    original_pool = channel.channel_pool
    assert original_pool is not None
    assert get_kombu_resource_all_objects(pool) == [channel]

    # Spy on pool.release to track calls
    release_spy = mocker.spy(pool, "release")

    # Call close which should detach from pool
    channel.close()

    # pool.release should be called exactly once
    assert release_spy.call_count == 1
    assert release_spy.call_args_list == [unittest.mock.call(channel)]

    # Channel should be detached
    assert channel.channel_pool is None

    # Verify channel was returned to pool successfully
    assert get_kombu_resource_all_objects(pool) == [channel]
    assert get_kombu_resource_free_objects(pool) == [channel]


def test_force_close__collect_called__pool_released(
    connection,
    mocker,
    get_kombu_resource_all_objects,
    get_kombu_resource_free_objects,
):
    """Test that force_close() closes channel and triggers collect().

    force_close() calls super().close() which triggers collect(),
    but since channel becomes closed (not usable), it's dropped from pool.
    """
    pool = connection.default_channel_pool

    channel = pool.acquire()
    assert get_kombu_resource_all_objects(pool) == [channel]
    assert get_kombu_resource_free_objects(pool) == []

    # Spy on pool.release to track calls
    release_spy = mocker.spy(pool, "release")

    # force_close calls super().close() which calls collect()
    # Channel becomes closed and is dropped from pool
    channel.force_close()

    # pool.release should be called once through collect()
    assert release_spy.call_count == 1
    assert release_spy.call_args_list == [unittest.mock.call(channel)]

    # Channel is not usable after force_close, so dropped from pool
    assert not channel.is_usable()
    assert get_kombu_resource_all_objects(pool) == []
    assert get_kombu_resource_free_objects(pool) == []

    # Channel should be detached from pool after collect()
    assert channel.channel_pool is None
