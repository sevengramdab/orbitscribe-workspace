"""Tests for the SimplePod PeerClient."""
import base64
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from client import PeerClient

BASE_URL = "http://192.168.1.50:58091"


class TestPeerClientRequest:
    """Tests for the underlying _request method."""

    @patch("client.requests.get")
    def test_get_constructs_correct_url_and_headers(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response

        client = PeerClient(BASE_URL)
        result = client._request("GET", "/health")

        mock_get.assert_called_once_with(
            f"{BASE_URL}/health",
            headers={"X-Token": client._headers["X-Token"]},
            timeout=client.timeout,
        )
        assert result == {"status": "ok"}

    @patch("client.requests.post")
    def test_post_constructs_correct_url_headers_and_json(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "123"}
        mock_post.return_value = mock_response

        client = PeerClient(BASE_URL)
        result = client._request("POST", "/exec", {"command": "ls"})

        mock_post.assert_called_once_with(
            f"{BASE_URL}/exec",
            headers={"X-Token": client._headers["X-Token"]},
            json={"command": "ls"},
            timeout=client.timeout,
        )
        assert result == {"id": "123"}

    @patch("client.requests.get")
    def test_get_returns_json_response(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"cpu": 12.5}
        mock_get.return_value = mock_response

        client = PeerClient(BASE_URL)
        result = client._request("GET", "/health")
        assert result == {"cpu": 12.5}

    @patch("client.requests.post")
    def test_post_returns_json_response(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"output": "hello"}
        mock_post.return_value = mock_response

        client = PeerClient(BASE_URL)
        result = client._request("POST", "/ping")
        assert result == {"output": "hello"}

    @patch("client.time.sleep")
    @patch("client.requests.get")
    def test_retry_on_connection_error_then_succeed(self, mock_get, mock_sleep):
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_get.side_effect = [
            requests.exceptions.ConnectionError("refused"),
            requests.exceptions.ConnectionError("refused"),
            mock_response,
        ]

        client = PeerClient(BASE_URL)
        result = client._request("GET", "/health")

        assert mock_get.call_count == 3
        assert result == {"ok": True}
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)

    @patch("client.time.sleep")
    @patch("client.requests.get")
    def test_retry_exhausted_raises_connection_error(self, mock_get, mock_sleep):
        mock_get.side_effect = requests.exceptions.ConnectionError("refused")

        client = PeerClient(BASE_URL)
        with pytest.raises(requests.exceptions.ConnectionError, match="Peer unreachable after 3 attempts"):
            client._request("GET", "/health")

        assert mock_get.call_count == 3


class TestPeerClientMethods:
    """Tests for high-level PeerClient methods."""

    @patch("client.requests.post")
    def test_ping(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"pong": True}
        mock_post.return_value = mock_response

        client = PeerClient(BASE_URL)
        result = client.ping()

        mock_post.assert_called_once_with(
            f"{BASE_URL}/ping",
            headers={"X-Token": client._headers["X-Token"]},
            json=None,
            timeout=client.timeout,
        )
        assert result == {"pong": True}

    @patch("client.requests.post")
    def test_exec(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"output": "file.txt"}
        mock_post.return_value = mock_response

        client = PeerClient(BASE_URL)
        result = client.exec("ls -la", cwd="/tmp", timeout=60)

        mock_post.assert_called_once_with(
            f"{BASE_URL}/exec",
            headers={"X-Token": client._headers["X-Token"]},
            json={"command": "ls -la", "cwd": "/tmp", "timeout": 60},
            timeout=client.timeout + 60,
        )
        assert result == {"output": "file.txt"}

    @patch("client.requests.post")
    def test_status(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"cpu": 10}
        mock_post.return_value = mock_response

        client = PeerClient(BASE_URL)
        result = client.status()

        mock_post.assert_called_once_with(
            f"{BASE_URL}/status",
            headers={"X-Token": client._headers["X-Token"]},
            json=None,
            timeout=client.timeout,
        )
        assert result == {"cpu": 10}

    @patch("client.requests.post")
    def test_setup(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"done": True}
        mock_post.return_value = mock_response

        client = PeerClient(BASE_URL)
        result = client.setup("pip install foo", description="install deps")

        mock_post.assert_called_once_with(
            f"{BASE_URL}/setup",
            headers={"X-Token": client._headers["X-Token"]},
            json={"script": "pip install foo", "description": "install deps"},
            timeout=client.timeout + 90,
        )
        assert result == {"done": True}

    @patch("client.requests.post")
    def test_sync_file(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"synced": True}
        mock_post.return_value = mock_response

        client = PeerClient(BASE_URL)
        content = b"hello world"
        result = client.sync_file("test.txt", content)

        expected_json = {
            "filename": "test.txt",
            "content": base64.b64encode(content).decode(),
        }
        mock_post.assert_called_once_with(
            f"{BASE_URL}/sync",
            headers={"X-Token": client._headers["X-Token"]},
            json=expected_json,
            timeout=client.timeout,
        )
        assert result == {"synced": True}

    @patch("client.requests.post")
    def test_is_alive_true(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        client = PeerClient(BASE_URL)
        assert client.is_alive() is True

    @patch("client.requests.post")
    def test_is_alive_false(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("down")

        client = PeerClient(BASE_URL)
        assert client.is_alive() is False


class TestPeerClientNewMethods:
    """Tests for newer PeerClient methods (health, screenshot, files)."""

    @patch("client.requests.get")
    def test_health(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy"}
        mock_get.return_value = mock_response

        client = PeerClient(BASE_URL)
        result = client.health()

        mock_get.assert_called_once_with(
            f"{BASE_URL}/health",
            headers={"X-Token": client._headers["X-Token"]},
            timeout=client.timeout,
        )
        assert result["status"] == "healthy"
        assert "latency_ms" in result

    @patch("client.requests.post")
    def test_screenshot(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"path": "/tmp/screen.png"}
        mock_post.return_value = mock_response

        client = PeerClient(BASE_URL)
        result = client.screenshot()

        mock_post.assert_called_once_with(
            f"{BASE_URL}/screenshot",
            headers={"X-Token": client._headers["X-Token"]},
            json=None,
            timeout=client.timeout,
        )
        assert result == {"path": "/tmp/screen.png"}

    @patch("client.requests.post")
    def test_list_files(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"files": ["a.txt"]}
        mock_post.return_value = mock_response

        client = PeerClient(BASE_URL)
        result = client.list_files("/home/user")

        mock_post.assert_called_once_with(
            f"{BASE_URL}/files/list",
            headers={"X-Token": client._headers["X-Token"]},
            json={"path": "/home/user"},
            timeout=client.timeout,
        )
        assert result == {"files": ["a.txt"]}

    @patch("client.requests.post")
    def test_download_file(self, mock_post):
        content = b"file contents"
        b64_content = base64.b64encode(content).decode()
        mock_response = MagicMock()
        mock_response.json.return_value = {"content_b64": b64_content}
        mock_post.return_value = mock_response

        client = PeerClient(BASE_URL)
        result = client.download_file("/remote/file.txt")

        mock_post.assert_called_once_with(
            f"{BASE_URL}/files/download",
            headers={"X-Token": client._headers["X-Token"]},
            json={"path": "/remote/file.txt"},
            timeout=client.timeout,
        )
        assert result["content_bytes"] == content
        assert result["content_b64"] == b64_content

    @patch("client.requests.post")
    def test_delete_file(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"deleted": True}
        mock_post.return_value = mock_response

        client = PeerClient(BASE_URL)
        result = client.delete_file("/remote/file.txt")

        mock_post.assert_called_once_with(
            f"{BASE_URL}/files/delete",
            headers={"X-Token": client._headers["X-Token"]},
            json={"path": "/remote/file.txt"},
            timeout=client.timeout,
        )
        assert result == {"deleted": True}
