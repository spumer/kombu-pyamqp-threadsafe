import threading
import unittest.mock

import kombu

from testing import PropagatingThread


def test_drain_events_after_connected_check_does_not_hang(connection, queue_name, mocker):
    """Checks that `drain_events(timeout=None)` does not hang after checking `connected`.

    Reproduces an edge-case:
    1. Send a message to the queue
    2. Check `connection.connected` (reads frames from the socket with _nodispatch=True)
    3. Call `SimpleQueue.get(timeout=None)` which internally calls drain_events
    4. If the fix works: drain_events finds the read frames and dispatches them
    5. If the fix does not work: drain_events hangs forever (frames are lost)

    SIDE-EFFECT (PART 1): connection.connected calls drain_events(timeout=0, _nodispatch=True)
    EDGE-CASE (PART 2): SimpleQueue.get() waits for an event that has already been read but not dispatched
    """
    pool = connection.default_channel_pool
    transport_drain_events_spy = mocker.spy(connection._connection, "drain_events")

    with pool.acquire() as channel:
        kombu.Queue(queue_name, channel=channel).declare()

        with kombu.Producer(channel) as producer:
            producer.publish(
                "test message",
                routing_key=queue_name,
            )

        # EDGE-CASE: SimpleQueue.get() should retrieve a message without blocking
        # Internally, drain_events(timeout=None) is called, which should find
        # already read frames and dispatch them
        thread_started = threading.Event()

        message_body = None

        def consume():
            # SIDE-EFFECT: Checking connected reads frames from the socket without dispatching
            nonlocal message_body

            thread_started.set()
            transport_drain_events_spy.reset_mock()
            assert not transport_drain_events_spy.called

            buff = connection.SimpleQueue(queue_name, channel=channel)
            msg = buff.get(timeout=None)  # It can hang here if the fix doesn't work
            message_body = msg.payload

        # Start another thread to due we need timeout=None,
        # but we do not want hang our test
        consumer_thread = PropagatingThread(target=consume)
        consumer_thread.start()

        thread_started.wait(timeout=1.0)
        consumer_thread.join(timeout=1.0)

        assert message_body == "test message"

        # Check we are going into an edge-case
        assert transport_drain_events_spy.call_args_list[-2:] == [
            unittest.mock.call(timeout=0, _nodispatch=True),
            unittest.mock.call(timeout=None),
        ]
