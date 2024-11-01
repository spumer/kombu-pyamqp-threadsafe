## v0.5.1 (2024-11-01)

### Fix

- **KombuConnection**: AssertError when make `connection.ensure(connection, ...)`

## v0.5.0 (2024-10-29)

### Feat

- now connection.Producer can be used with pooled channels and relase it automatically

### Fix

- race condition: now closed channel can't be acquired again
- channel leak in Connection.default_channel (regression e821b32cd7); Revert back default_channel creation method

## v0.4.2 (2024-10-21)

### Fix

- now connection can be restored after SSLError (details in full comment)

## v0.4.1 (2024-10-03)

### Fix

- **ChannelPool**: deadlock on ChannelPool.acquire(block=True) (regression at 41c7ac86eaad8b28b298900e5cc9619602552c7f)

## v0.4.0 (2024-09-18)

### Feat

- **ChannelPool**: more robust KombuConnection.default_channel_pool recreation
- **ChannelPool**: ThreadSafeChannel.close()  first try return channel to pool instead closing, .force_close() method added to close in any way;

## v0.3.1 (2024-09-12)

### Fix

- **ChannelPool**: ignore closed channel when release

## v0.3.0 (2024-06-06)

### Feat

- KombuConnection.default_channel now threadsafe
- new method KombuConnection.from_kombu_connection() to recreate thread-safe KombuConnection from already exists kombu.Connection
- add env KOMBU_PYAMQP_THREADSAFE_DEBUG to logging more details about locks; maybe in feature added some other info

### Fix

- now KombuConnection correctly check internal transport when replace it via thread-safe variant (previously it's always raise error)
- now KombuConnection.default_channel_pool allow return channel to pool back if it reusable; ensure connection is connected when create pool

## v0.2.0 (2024-05-13)

### Feat

- now KombuConnection by default use "shared" transport version (previously you should use `add_shared_amqp_transport` or `monkeypatch_pyamqp_transport` functions)

## v0.1.0 (2024-03-24)

### Feat

- initial

## v0.0.0 (2024-03-24)
