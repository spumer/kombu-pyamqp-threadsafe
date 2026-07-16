[![](https://img.shields.io/badge/benchmark-docs-purple)](https://spumer.github.io/kombu-pyamqp-threadsafe/) [![Open in Dev Containers](https://img.shields.io/static/v1?label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/spumer/kombu-pyamqp-threadsafe)


# kombu-pyamqp-threadsafe

Threadsafe implementation of pyamqp transport for kombu

## TL;DR

kombu (pyamqp) designed as "1 thread = 1 connection", no connection sharing between threads

This package make possible design "1 thread = 1 channel", **allow** connection sharing between threads

```python
import kombu
import kombu_pyamqp_threadsafe

# Use drop-in replacement thread-safe kombu.Connection variant: 
connection = kombu_pyamqp_threadsafe.KombuConnection(...)

# or construct from kombu.Connection
kombu_connection = kombu.Connection(...)
kombu_pyamqp_threadsafe.KombuConnection.from_kombu_connection(kombu_connection)
```

## Motivation

The best practice to work with RabbitMQ is use 2 connections: 1 for consuming and 1 for producer.

https://www.cloudamqp.com/blog/part1-rabbitmq-best-practice.html#connections-and-channels

But it's not possible with kombu (pyamqp) (https://github.com/celery/py-amqp/issues/420)

Without that we can't effectively consume many queues at same time

And when we publish messages in multithread application we need create connection for each publisher (producer) thread

## Other solutions

Connection pool.
- This is concept used by celery, now you do not create a lot of connections when publish messages but still need same connections count to consume

Use same channel to consume from all queues
- It's bad practice cause any exception in channel will close it and broke all consumers  

## Usage

**Q:** Ok, i install it, and now what?

**A:** You can use ConnectionHolder from this snippet: https://github.com/celery/py-amqp/issues/420#issuecomment-1858429922

**Q:** It's production ready? How you test it? 

**A:** Yes, it's production ready. We also make stress-test with 900 threads, when run 900 dramatiq actors which consume message and send new one to queue. Only 2 connections used.

**Q:** Dramatiq?

**A:** Yes, just use [dramatiq-kombu-broker](https://github.com/spumer/dramatiq-kombu-broker/)

### Rules

**Rule 1:** Do not share channel between threads
- Do not use `default_channel` from different threads,
 cause **responses is channel bound**, you can get error from other thread or produce error to different thread
- Use `default_channel_pool` and acquire channel for each thread

**Rule 2:** Channel bound to thread where his created.
- This required because dispatch frame can raise error which expected in caller thread (see **Rule 1**). E.g.: `queue_declare` method.
- If you declare queue in passive mode RabbitMQ will close channel
    and exception MAY raise in different thread when his drain events.
- To ensure all exceptions raised in expected context we bound channels to threads and dispatch received frames only in their own threads.


## Dedicated drainer thread (optional)

By default a connection reads frames off the socket lazily, inside whichever
application thread happens to call `drain_events()`. Set
`transport_options={"dedicated_drainer": True}` (default `False`) to give the
connection its own background thread that owns the socket read instead: it
polls the transport via `select`, pumps every available frame into the
connection's buffers, and takes the transport lock only for already-ready
frames. Publisher threads no longer queue up behind another thread's blocking
read. See `tests/benchmarks/test_drainer_benchmarks.py` for the publish-latency
benchmark — in a local run, p99 publish latency with a hanging consumer on the
same connection dropped from ~2s to low single-digit milliseconds.

**Lifecycle:** the drainer starts at the end of `connect()` and stops in
`close()`/`collect()`. A kombu reconnect builds a brand new connection, so the
connection factory explicitly stops the old drainer before handing off to the
new one.

**Heartbeat:** with the option enabled, the connection ticks its own
heartbeat at the negotiated interval as part of the same loop — you don't
need a separate `heartbeat_check`. Without the option, behavior is unchanged.

**Closing:** an intentional `close()`/`collect()` wakes any thread blocked in
`drain_events()` with `ConnectionClosedIntentionally` (a subclass of amqp's
`IrrecoverableConnectionError`). kombu's `ensure()`/`Consumer` do **not**
retry or reconnect on it, since the application closed the connection on
purpose. A real failure (dropped socket, missed heartbeat) still raises a
recoverable error and reconnects as usual.

**Things to keep in mind:**
- Always close connections (`close()`/`collect()`). An unclosed connection
  with the drainer enabled keeps 2 self-pipe file descriptors open for the
  life of the process.
- The drainer does not survive `os.fork()` — recreate the connection in the
  child process.
- During the close handshake, publishers can technically still send frames
  (frames are serialized per-call, so the stream itself never corrupts) —
  coordinating shutdown with in-flight publishers is the application's
  responsibility.
- Any non-connection exception from the drainer's read loop propagates to
  every thread waiting on `drain_events()` (fail-fast).

This doesn't change **Rule 1**/**Rule 2** above: the drainer only buffers
frames, dispatch still happens in the thread that owns each channel.

## Install

To add and install this package as a dependency of your project, run `uv add kombu-pyamqp-threadsafe` (or `pip install kombu-pyamqp-threadsafe`).


<details>
<summary>Developing</summary>

- This project follows the [Conventional Commits](https://www.conventionalcommits.org/) standard to automate [Semantic Versioning](https://semver.org/) and [Keep A Changelog](https://keepachangelog.com/) with [Commitizen](https://github.com/commitizen-tools/commitizen).
- Run `uv sync` to create the development environment (installs the package and the `dev` dependency group).
- Run `uv run poe` to print a list of [Poe the Poet](https://github.com/nat-n/poethepoet) tasks available to run on this project.
- Run `uv add {package}` to install a run time dependency and add it to `pyproject.toml` and `uv.lock`. Add `--group dev` or `--group docs` to install a development or docs dependency, respectively.
- Run `uv lock --upgrade && uv sync` to upgrade all dependencies to the latest versions allowed by `pyproject.toml`.
- Run `cz bump` to bump the package's version, update the `CHANGELOG.md`, and create a git tag.

</details>
