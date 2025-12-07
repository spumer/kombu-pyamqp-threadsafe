"""Fixtures for benchmarks.

Provides specialized fixtures for performance benchmarking:
- Multi-channel connections with configurable pool sizes
- Metrics collection and reporting
- Connection kill utilities for failure simulation
"""

import os
import socket
import time

import pytest

import kombu_pyamqp_threadsafe

# ====================
# Skip Conditions
# ====================


def _check_service_available(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a TCP service is available."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def _rabbitmq_available() -> bool:
    """Check if RabbitMQ is available."""
    host = os.getenv("PYTEST_RABBITMQ_HOST", "127.0.0.1")
    port = int(os.getenv("PYTEST_RABBITMQ_PORT", "5672"))
    return _check_service_available(host, port)


rabbitmq_available = pytest.mark.skipif(not _rabbitmq_available(), reason="RabbitMQ not available")


# ====================
# Fixtures: Connections
# ====================


@pytest.fixture
def benchmark_connection(rabbitmq_dsn):
    """Connection optimized for benchmarking with large pool."""
    connection = kombu_pyamqp_threadsafe.KombuConnection(
        rabbitmq_dsn,
        default_channel_pool_size=1000,  # Large pool for stress tests
    )
    yield connection
    connection.close()


@pytest.fixture
def connection_factory(rabbitmq_dsn):
    """Factory for creating benchmark connections."""
    connections = []

    def create(pool_size: int = 100):
        conn = kombu_pyamqp_threadsafe.KombuConnection(
            rabbitmq_dsn, default_channel_pool_size=pool_size
        )
        connections.append(conn)
        return conn

    yield create

    for conn in connections:
        try:
            conn.close()
        except Exception:
            pass


# ====================
# Fixtures: Connection Manipulation
# ====================


@pytest.fixture
def kill_connection():
    """Utility to forcefully close connection transport."""

    def _kill(connection: kombu_pyamqp_threadsafe.KombuConnection) -> float:
        """Kill connection and return timestamp.

        Returns:
            Timestamp when connection was killed
        """
        kill_time = time.monotonic()
        if connection._connection and connection._connection._transport:
            connection._connection._transport.close()
        return kill_time

    return _kill


@pytest.fixture
def reset_connection():
    """Utility to reset connection state for next iteration."""

    def _reset(connection: kombu_pyamqp_threadsafe.KombuConnection) -> None:
        """Reset connection for clean state."""
        try:
            connection.close()
        except Exception:
            pass
        # Force new connection on next access
        connection._connection = None
        connection._default_channel = None
        if connection._default_channel_pool:
            try:
                connection._default_channel_pool.force_close_all()
            except Exception:
                pass
            connection._default_channel_pool = None

    return _reset


# ====================
# Fixtures: Queue Management
# ====================


@pytest.fixture
def benchmark_queue_name(request):
    """Generate unique queue name for benchmark."""
    return f"bench_{request.node.name}_{int(time.time())}"


@pytest.fixture
def cleanup_queues(rabbitmq_dsn):
    """Cleanup utility for benchmark queues."""
    queues_to_delete = []

    def register(queue_name: str):
        queues_to_delete.append(queue_name)

    yield register

    # Cleanup
    try:
        conn = kombu_pyamqp_threadsafe.KombuConnection(rabbitmq_dsn)
        for qname in queues_to_delete:
            try:
                kombu_pyamqp_threadsafe.kombu.Queue(qname, channel=conn).delete()
            except Exception:
                pass
        conn.close()
    except Exception:
        pass
