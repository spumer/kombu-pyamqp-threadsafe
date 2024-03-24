"""Test kombu-pyamqp-threadsafe."""

import kombu_pyamqp_threadsafe


def test_import() -> None:
    """Test that the package can be imported."""
    assert isinstance(kombu_pyamqp_threadsafe.__name__, str)
