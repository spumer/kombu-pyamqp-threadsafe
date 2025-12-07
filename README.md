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


## Install

To add and install this package as a dependency of your project, run `poetry add kombu-pyamqp-threadsafe`.


<details>
<summary>Developing</summary>

- This project follows the [Conventional Commits](https://www.conventionalcommits.org/) standard to automate [Semantic Versioning](https://semver.org/) and [Keep A Changelog](https://keepachangelog.com/) with [Commitizen](https://github.com/commitizen-tools/commitizen).
- Run `poe` from within the development environment to print a list of [Poe the Poet](https://github.com/nat-n/poethepoet) tasks available to run on this project.
- Run `poetry add {package}` from within the development environment to install a run time dependency and add it to `pyproject.toml` and `poetry.lock`. Add `--group test` or `--group dev` to install a CI or development dependency, respectively.
- Run `poetry update` from within the development environment to upgrade all dependencies to the latest versions allowed by `pyproject.toml`.
- Run `cz bump` to bump the package's version, update the `CHANGELOG.md`, and create a git tag.

</details>
