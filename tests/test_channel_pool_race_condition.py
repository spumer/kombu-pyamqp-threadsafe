"""Test race condition fix in ThreadSafeChannel.close() and collect()."""

import unittest.mock

import pytest


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


def test_channel_close__reentrant_via_pool_release__prevented(
    connection,
    mocker,
    get_kombu_resource_all_objects,
    get_kombu_resource_free_objects,
):
    """Test that close() guards against true re-entrant calls via pool.release().

    This simulates the original regression scenario where pool.release()
    (or callbacks it triggers) re-enters channel.close() while a release
    is already in progress. The _is_releasing flag should prevent a
    second release and avoid recursion.
    """
    pool = connection.default_channel_pool

    channel = pool.acquire()
    assert get_kombu_resource_all_objects(pool) == [channel]
    assert get_kombu_resource_free_objects(pool) == []

    original_release = pool.release
    release_call_count = {"count": 0}

    def release_with_reentrancy(resource):
        # Count how many times pool.release is actually invoked
        release_call_count["count"] += 1

        # On the first release call, simulate a re-entrant close()
        # happening from inside pool.release (or its callbacks).
        if release_call_count["count"] == 1:
            # This should be a no-op because _is_releasing is already True
            channel.close()

        # Delegate to the original implementation
        return original_release(resource)

    # Monkeypatch pool.release to simulate re-entrant scenario
    mocker.patch.object(pool, "release", side_effect=release_with_reentrancy)

    # Act: closing the channel should trigger exactly one pool.release call
    channel.close()

    # Assert: pool.release was only executed once (re-entrant call was blocked)
    assert release_call_count["count"] == 1

    # Assert: channel is detached
    assert channel.channel_pool is None

    # Assert: channel returned to pool exactly once (no duplicates)
    all_after = get_kombu_resource_all_objects(pool)
    free_after = get_kombu_resource_free_objects(pool)

    assert channel in free_after
    # Check no duplicates
    assert free_after.count(channel) == 1
    assert all_after.count(channel) == 1


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


def test_channel_close__pool_release_error__flag_reset(
    connection,
    mocker,
    get_kombu_resource_all_objects,
    get_kombu_resource_free_objects,
):
    """Ensure _is_releasing is reset even if pool.release raises.

    This validates the failure path of the try/finally in Channel.close().
    If pool.release() raises an exception, _is_releasing must still be
    reset to False so that subsequent close() calls work correctly.
    """

    class DummyReleaseError(Exception):
        """Custom exception raised by the patched pool.release."""

    pool = connection.default_channel_pool
    channel = pool.acquire()

    # Sanity check initial state
    assert channel._is_releasing is False
    assert get_kombu_resource_all_objects(pool) == [channel]

    # Patch pool.release to raise an exception
    def raising_release(resource):
        raise DummyReleaseError("boom")

    mocker.patch.object(pool, "release", side_effect=raising_release)

    # First close should hit the failure path in try/finally
    with pytest.raises(DummyReleaseError):
        channel.close()

    # _is_releasing must be reset so that later closes are not no-ops
    assert channel._is_releasing is False

    # Channel should be detached from pool despite the error
    assert channel.channel_pool is None

    # Restore original release for subsequent close
    mocker.stopall()

    # Second close should work normally (idempotent)
    channel.close()

    # Channel should still be detached
    assert channel.channel_pool is None
    assert channel._is_releasing is False


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
