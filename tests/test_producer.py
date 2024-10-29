import kombu


def test_publish__retry_ssl_error__channel_removed_from_pool(
    mocker,
    connection,
    queue_name,
    get_kombu_resource_all_objects,
    make_channel_raise_sslerror,
):
    """Test channel removed from pool when connection auto collected on producer retry"""

    def _on_revive(_channel):
        nonlocal actual_retries
        actual_retries += 1

    pool = connection.default_channel_pool

    actual_retries = 1
    max_retries = 2
    with pool.acquire() as channel:
        channel.queue_declare(queue=queue_name, durable=True, auto_delete=False)

        # now channel can not be used
        make_channel_raise_sslerror(channel)
        connection_collect_spy = mocker.spy(channel.connection, "collect")

        with kombu.Producer(channel) as producer:
            assert producer.channel is channel
            producer.publish(
                "test",
                routing_key=queue_name,
                retry=True,
                retry_policy={
                    "max_retries": 2,
                    "on_revive": _on_revive,
                },
                mandatory=True,
            )

        # producer call .collect() when error occured
        assert connection_collect_spy.called

        # broken channel closed and new one opened automatically
        assert not channel.is_open
        assert producer.channel is not channel

        # but, it's opened like shared `default channel`
        assert producer.channel is connection.default_channel
        # and a previous channel collected
        assert get_kombu_resource_all_objects(pool) == []

    assert actual_retries == max_retries

    with pool.acquire() as channel:
        # check we can acquire new channel again and no limit exceeded
        assert get_kombu_resource_all_objects(pool) == [channel]

        buff = connection.SimpleQueue(queue_name, channel=channel)
        msg = buff.get(timeout=0.001)
        assert msg.body == "test"


def test_publish__autorelease_producer__retry_retry_ssl_error__default_channel_not_changed(
    connection,
    queue_name,
    get_kombu_resource_all_objects,
    make_channel_raise_sslerror,
):
    """Test AutoChannelReleaseProducer do not close unbound channels.
    On SSLError Producer revived by Connection.default_channel, and we do not want to close it automatically.
    """
    pool = connection.default_channel_pool

    with pool.acquire() as channel:
        channel.queue_declare(queue=queue_name, durable=True, auto_delete=False)
        # now channel can not be used
        make_channel_raise_sslerror(channel)

        with connection.Producer(channel) as producer:
            assert producer.channel is channel
            producer.publish(
                "test",
                routing_key=queue_name,
                retry=True,
                retry_policy={
                    "max_retries": 2,
                },
                mandatory=True,
            )
            assert not channel.is_open
            assert producer.channel is not channel

            # preserve before release
            conn_default_channel = connection.default_channel

            # broken channel closed and new one opened automatically
            assert producer.channel is conn_default_channel

        assert conn_default_channel.is_usable()
        assert get_kombu_resource_all_objects(pool) == []
