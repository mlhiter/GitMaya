import sys
from pathlib import Path
from types import SimpleNamespace
import unittest

SERVER_DIR = Path(__file__).resolve().parents[1] / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from utils.lark.user_display import get_lark_display_name


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class _FakeBot:
    host = "https://open.feishu.cn"

    def __init__(self, payload):
        self.payload = payload

    def get(self, url):
        return _FakeResponse(self.payload)


class TestLarkUserDisplay(unittest.TestCase):
    def test_resolves_placeholder_open_id_to_real_name(self):
        user = SimpleNamespace(
            name="ou_cad4b4878ff3ac966ae27099201ba83b",
            openid="ou_cad4b4878ff3ac966ae27099201ba83b",
            application_id="app-1",
            email=None,
        )
        bot = _FakeBot({"data": {"user": {"name": "刘冰玲"}}})

        result = get_lark_display_name(user, bot_factory=lambda _app_id: bot)

        self.assertEqual(result, "刘冰玲")

    def test_never_returns_raw_open_id_when_resolution_fails(self):
        user = {
            "name": "ou_cad4b4878ff3ac966ae27099201ba83b",
            "openid": "ou_cad4b4878ff3ac966ae27099201ba83b",
            "application_id": "app-1",
        }
        bot = _FakeBot({"code": 999, "msg": "forbidden"})

        result = get_lark_display_name(user, bot_factory=lambda _app_id: bot)

        self.assertEqual(result, "未同步飞书姓名")


if __name__ == "__main__":
    unittest.main()
