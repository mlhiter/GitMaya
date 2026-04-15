import importlib
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

SERVER_DIR = Path(__file__).resolve().parents[1] / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

oauth_state = importlib.import_module("utils.oauth_state")


class _FakeRedis:
    def __init__(self):
        self.data = {}

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.data:
            return False
        self.data[key] = value
        return True

    def delete(self, key):
        if key in self.data:
            del self.data[key]
            return 1
        return 0


class TestOAuthState(unittest.TestCase):
    def test_signed_state_can_only_be_consumed_once(self):
        fake_redis = _FakeRedis()
        with patch.dict("os.environ", {"SECRET_KEY": "test-secret"}, clear=False), patch(
            "utils.oauth_state._get_redis_client", return_value=fake_redis
        ):
            state = oauth_state.issue_signed_oauth_state(
                {
                    "app_id": "app_x",
                    "open_id": "ou_xxx",
                    "team_id": "team_x",
                },
                ttl_seconds=300,
            )
            self.assertTrue(state and state.startswith("gmv2."))

            payload, error = oauth_state.decode_signed_oauth_state(state, consume=True)
            self.assertIsNone(error)
            self.assertEqual(payload.get("app_id"), "app_x")
            self.assertEqual(payload.get("open_id"), "ou_xxx")
            self.assertEqual(payload.get("team_id"), "team_x")

            payload2, error2 = oauth_state.decode_signed_oauth_state(state, consume=True)
            self.assertIsNone(payload2)
            self.assertEqual(error2, "state_used")

    def test_signed_state_expires_by_exp_timestamp(self):
        fake_redis = _FakeRedis()
        with patch.dict("os.environ", {"SECRET_KEY": "test-secret"}, clear=False), patch(
            "utils.oauth_state._get_redis_client", return_value=fake_redis
        ), patch("utils.oauth_state.time.time", return_value=1000):
            state = oauth_state.issue_signed_oauth_state(
                {"app_id": "app_x", "open_id": "ou_xxx"},
                ttl_seconds=60,
            )

        with patch.dict("os.environ", {"SECRET_KEY": "test-secret"}, clear=False), patch(
            "utils.oauth_state._get_redis_client", return_value=fake_redis
        ), patch("utils.oauth_state.time.time", return_value=2000):
            payload, error = oauth_state.decode_signed_oauth_state(state, consume=False)
            self.assertIsNone(payload)
            self.assertEqual(error, "state_expired")

if __name__ == "__main__":
    unittest.main()
