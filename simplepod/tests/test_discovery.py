"""Tests for SimplePod peer discovery."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from discovery import Peer


class TestPeer:
    """Tests for the Peer dataclass."""

    def test_api_url_format(self):
        peer = Peer(
            node_id="node-1",
            name="Test Node",
            role="shadow",
            ip="192.168.1.10",
            api_port=58091,
        )
        assert peer.api_url() == "http://192.168.1.10:58091"

    def test_api_url_with_different_port(self):
        peer = Peer(
            node_id="node-2",
            name="Another Node",
            role="local",
            ip="10.0.0.5",
            api_port=8080,
        )
        assert peer.api_url() == "http://10.0.0.5:8080"
