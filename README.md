[![Open in Dev Containers](https://img.shields.io/static/v1?label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/spumer/kombu-pyamqp-threadsafe)

# kombu-pyamqp-threadsafe

Threadsafe implementation of pyamqp transport for kombu

## TL;DR

kombu (pyamqp) designed as "1 thread = 1 connection", no connection sharing between threads

This package make possible design "1 thread = 1 channel", **allow** connection sharing between threads

```python
import kombu_pyamqp_threadsafe
# ... and then
kombu_pyamqp_threadsafe.monkeypatch_pyamqp_transport()  # patch exists transports: 'pyamqp://', 'amqp://', 'amqps://'
# ... or
kombu_pyamqp_threadsafe.add_shared_amqp_transport()  # explicit use 'shared+pyamqp://', 'shared+amqp://' or 'shared+amqps://' transports 

# Transport not enough and you need thread-safe kombu.Connection variant: 
connection = kombu_pyamqp_threadsafe.KombuConnection(...)
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
**A:** Yes, dramatiq-kombu-broker will be released soon :)

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

## Contributing

<details>
<summary>Prerequisites</summary>

<details>
<summary>1. Set up Git to use SSH</summary>

1. [Generate an SSH key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent#generating-a-new-ssh-key) and [add the SSH key to your GitHub account](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account).
1. Configure SSH to automatically load your SSH keys:
    ```sh
    cat << EOF >> ~/.ssh/config
    Host *
      AddKeysToAgent yes
      IgnoreUnknown UseKeychain
      UseKeychain yes
    EOF
    ```

</details>

<details>
<summary>2. Install Docker</summary>

1. [Install Docker Desktop](https://www.docker.com/get-started).
    - Enable _Use Docker Compose V2_ in Docker Desktop's preferences window.
    - _Linux only_:
        - Export your user's user id and group id so that [files created in the Dev Container are owned by your user](https://github.com/moby/moby/issues/3206):
            ```sh
            cat << EOF >> ~/.bashrc
            export UID=$(id --user)
            export GID=$(id --group)
            EOF
            ```

</details>

<details>
<summary>3. Install VS Code or PyCharm</summary>

1. [Install VS Code](https://code.visualstudio.com/) and [VS Code's Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers). Alternatively, install [PyCharm](https://www.jetbrains.com/pycharm/download/).
2. _Optional:_ install a [Nerd Font](https://www.nerdfonts.com/font-downloads) such as [FiraCode Nerd Font](https://github.com/ryanoasis/nerd-fonts/tree/master/patched-fonts/FiraCode) and [configure VS Code](https://github.com/tonsky/FiraCode/wiki/VS-Code-Instructions) or [configure PyCharm](https://github.com/tonsky/FiraCode/wiki/Intellij-products-instructions) to use it.

</details>

</details>

<details open>
<summary>Development environments</summary>

The following development environments are supported:

1. ⭐️ _GitHub Codespaces_: click on _Code_ and select _Create codespace_ to start a Dev Container with [GitHub Codespaces](https://github.com/features/codespaces).
1. ⭐️ _Dev Container (with container volume)_: click on [Open in Dev Containers](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/spumer/kombu-pyamqp-threadsafe) to clone this repository in a container volume and create a Dev Container with VS Code.
1. _Dev Container_: clone this repository, open it with VS Code, and run <kbd>Ctrl/⌘</kbd> + <kbd>⇧</kbd> + <kbd>P</kbd> → _Dev Containers: Reopen in Container_.
1. _PyCharm_: clone this repository, open it with PyCharm, and [configure Docker Compose as a remote interpreter](https://www.jetbrains.com/help/pycharm/using-docker-compose-as-a-remote-interpreter.html#docker-compose-remote) with the `dev` service.
1. _Terminal_: clone this repository, open it with your terminal, and run `docker compose up --detach dev` to start a Dev Container in the background, and then run `docker compose exec dev zsh` to open a shell prompt in the Dev Container.

</details>

<details>
<summary>Developing</summary>

- This project follows the [Conventional Commits](https://www.conventionalcommits.org/) standard to automate [Semantic Versioning](https://semver.org/) and [Keep A Changelog](https://keepachangelog.com/) with [Commitizen](https://github.com/commitizen-tools/commitizen).
- Run `poe` from within the development environment to print a list of [Poe the Poet](https://github.com/nat-n/poethepoet) tasks available to run on this project.
- Run `poetry add {package}` from within the development environment to install a run time dependency and add it to `pyproject.toml` and `poetry.lock`. Add `--group test` or `--group dev` to install a CI or development dependency, respectively.
- Run `poetry update` from within the development environment to upgrade all dependencies to the latest versions allowed by `pyproject.toml`.
- Run `cz bump` to bump the package's version, update the `CHANGELOG.md`, and create a git tag.

</details>
