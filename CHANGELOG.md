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
