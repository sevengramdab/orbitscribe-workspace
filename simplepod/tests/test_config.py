"""Tests for simplepod configuration defaults and environment overrides."""
import importlib
import os
import socket
import sys
from unittest.mock import patch

import pytest

# Ensure simplepod is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config


class TestConfigDefaults:
    """Verify default configuration values."""

    def test_discovery_port_default(self):
        assert config.DISCOVERY_PORT == 58090

    def test_discovery_interval_default(self):
        assert config.DISCOVERY_INTERVAL == 3.0

    def test_discovery_timeout_default(self):
        assert config.DISCOVERY_TIMEOUT == 10.0

    def test_api_port_default(self):
        assert config.API_PORT == 58091

    def test_api_token_default(self):
        assert config.API_TOKEN == "simplepod-default-token"

    def test_node_role_default(self):
        assert config.NODE_ROLE == "shadow"

    def test_node_id_defaults_to_hostname(self):
        assert config.NODE_ID == socket.gethostname()

    def test_node_name_defaults_to_node_id(self):
        assert config.NODE_NAME == config.NODE_ID


class TestConfigEnvOverrides:
    """Verify environment variables override defaults."""

    @patch.dict(
        os.environ,
        {
            "SIMPLEPOD_DISCOVERY_PORT": "9999",
            "SIMPLEPOD_API_PORT": "8888",
            "SIMPLEPOD_TOKEN": "super-secret",
            "SIMPLEPOD_NODE_ID": "node-42",
            "SIMPLEPOD_NODE_NAME": "Test Node",
            "SIMPLEPOD_ROLE": "local",
        },
        clear=False,
    )
    def test_env_overrides(self):
        # Reload config module with patched environment
        importlib.reload(config)
        assert config.DISCOVERY_PORT == 9999
        assert config.API_PORT == 8888
        assert config.API_TOKEN == "super-secret"
        assert config.NODE_ID == "node-42"
        assert config.NODE_NAME == "Test Node"
        assert config.NODE_ROLE == "local"

    @patch.dict(
        os.environ,
        {
            "SIMPLEPOD_DISCOVERY_PORT": "12345",
        },
        clear=False,
    )
    def test_partial_env_override(self):
        importlib.reload(config)
        assert config.DISCOVERY_PORT == 12345
        # Other values fall back to defaults
        assert config.API_PORT == 58091
        assert config.API_TOKEN == "simplepod-default-token"
