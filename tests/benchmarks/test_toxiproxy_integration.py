"""Integration tests for Toxiproxy client.

Verifies that Toxiproxy client works correctly and can simulate network failures.
"""

import time
from contextlib import contextmanager

import pytest

import kombu_pyamqp_threadsafe
from toxiproxy_client import Proxy, ToxiproxyClient, ToxiproxyConnectionError

# ====================
# Skip if no Toxiproxy
# ====================


def _toxiproxy_available() -> bool:
    """Check if Toxiproxy is running."""
    try:
        client = ToxiproxyClient()
        client.version()
        return True
    except ToxiproxyConnectionError:
        return False


pytestmark = pytest.mark.skipif(
    not _toxiproxy_available(),
    reason="Toxiproxy not available (run: docker compose -f docker-compose.test.yml up -d)",
)


# ====================
# Fixtures
# ====================


@pytest.fixture
def toxiproxy():
    """Toxiproxy client."""
    return ToxiproxyClient()


# rabbitmq_proxy fixture is defined in conftest.py (session-scoped)


# ====================
# Tests: Client API
# ====================


class TestToxiproxyClient:
    """Tests for Toxiproxy client basic operations."""

    def test_version(self, toxiproxy) -> None:
        """Verify server version can be retrieved."""
        version = toxiproxy.version()
        assert "version" in version
        assert version["version"].startswith("2.")

    def test_create_and_destroy_proxy(self, toxiproxy) -> None:
        """Verify proxy can be created and destroyed."""
        proxy = toxiproxy.create_proxy(
            name="test_proxy",
            listen="0.0.0.0:25673",
            upstream="rabbitmq:5672",
        )
        assert proxy.name == "test_proxy"
        assert proxy.enabled is True

        # Verify it's in the list
        proxies = toxiproxy.list_proxies()
        assert "test_proxy" in proxies

        # Destroy
        proxy.destroy()
        proxies = toxiproxy.list_proxies()
        assert "test_proxy" not in proxies

    def test_add_and_remove_toxic(self, rabbitmq_proxy) -> None:
        """Verify toxic can be added and removed."""
        toxic = rabbitmq_proxy.add_toxic(
            name="test_latency",
            toxic_type="latency",
            attributes={"latency": 100, "jitter": 10},
        )
        assert toxic.name == "test_latency"
        assert toxic.type == "latency"
        assert toxic.attributes["latency"] == 100

        # Remove
        toxic.remove()
        assert len(rabbitmq_proxy.toxics) == 0

    def test_disable_enable_proxy(self, rabbitmq_proxy: Proxy) -> None:
        """Verify proxy can be disabled and enabled."""
        assert rabbitmq_proxy.enabled is True

        rabbitmq_proxy.disable()
        assert not rabbitmq_proxy.enabled

        rabbitmq_proxy.enable()  # type: ignore[unreachable]
        assert rabbitmq_proxy.enabled is True


# ====================
# Tests: Network Failures
# ====================


class TestNetworkFailures:
    """Tests for simulating network failures."""

    @pytest.fixture
    def connection(self, rabbitmq_proxy):
        """Connection through toxiproxy."""
        # Use the proxy port
        conn = kombu_pyamqp_threadsafe.KombuConnection(
            "amqp://guest:guest@127.0.0.1:25672//",
            default_channel_pool_size=10,
        )
        yield conn
        try:
            conn.close()
        except Exception:
            pass

    def test_connection_through_proxy(self, connection) -> None:
        """Verify connection works through toxiproxy."""
        channel = connection.default_channel
        assert connection.connected
        assert channel.is_usable()

    def test_latency_toxic_adds_delay(self, rabbitmq_proxy, connection) -> None:
        """Verify latency toxic adds measurable delay."""
        # Warm up connection
        _ = connection.default_channel

        # Measure without latency
        start = time.monotonic()
        connection.default_channel.exchange_declare(exchange="test_no_latency", type="direct")
        no_latency = time.monotonic() - start

        # Add latency
        toxic = rabbitmq_proxy.add_toxic(
            name="latency",
            toxic_type="latency",
            attributes={"latency": 200},  # 200ms
        )

        try:
            start = time.monotonic()
            connection.default_channel.exchange_declare(exchange="test_with_latency", type="direct")
            with_latency = time.monotonic() - start

            # With latency should be significantly slower
            assert with_latency > no_latency + 0.15  # At least 150ms more
            print(f"\nNo latency: {no_latency * 1000:.0f}ms")
            print(f"With 200ms latency: {with_latency * 1000:.0f}ms")
        finally:
            toxic.remove()

    def test_timeout_toxic_blocks_connection(self, rabbitmq_proxy) -> None:
        """Verify timeout toxic blocks new connections."""
        # Add timeout toxic (blocks all data)
        toxic = rabbitmq_proxy.add_toxic(
            name="timeout",
            toxic_type="timeout",
            attributes={"timeout": 0},  # Block indefinitely
        )

        try:
            # New connection should timeout
            with pytest.raises(Exception):  # OSError or similar
                conn = kombu_pyamqp_threadsafe.KombuConnection(
                    "amqp://guest:guest@127.0.0.1:25672//",
                    transport_options={"connect_timeout": 1},
                )
                _ = conn.default_channel
        finally:
            toxic.remove()

    def test_reset_peer_closes_connection(self, rabbitmq_proxy, connection) -> None:
        """Verify reset_peer toxic closes existing connections."""
        # Establish connection
        _ = connection.default_channel
        assert connection.connected

        # Add reset_peer toxic
        toxic = rabbitmq_proxy.add_toxic(
            name="reset",
            toxic_type="reset_peer",
            attributes={"timeout": 0},  # Immediate reset
        )

        try:
            # Next operation should fail
            with pytest.raises(Exception):
                # Force a new operation
                connection._connection.drain_events(timeout=0.1)
        finally:
            toxic.remove()


# ====================
# Tests: Benchmark Fixtures
# ====================


class TestBenchmarkFixtures:
    """Tests for benchmark-specific fixtures."""

    def test_network_failure_fixture(self, rabbitmq_proxy, add_toxic_latency) -> None:
        """Verify network_failure fixture works."""

        # Test the pattern used in conftest
        @contextmanager
        def latency_context(ms: int):
            toxic = add_toxic_latency(ms)
            try:
                yield
            finally:
                toxic.remove()

        with latency_context(100):
            # Verify toxic is active
            assert len(rabbitmq_proxy.toxics) == 1
            assert rabbitmq_proxy.toxics[0].type == "latency"

        # Verify toxic is removed
        assert len(rabbitmq_proxy.toxics) == 0
