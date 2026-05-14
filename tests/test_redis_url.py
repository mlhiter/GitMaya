import importlib
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

SERVER_DIR = Path(__file__).resolve().parents[1] / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

redis_utils = importlib.import_module("utils.redis")


class TestRedisUrl(unittest.TestCase):
    def setUp(self):
        self.original_redis_url = redis_utils.app.config.pop("REDIS_URL", None)

    def tearDown(self):
        if self.original_redis_url is not None:
            redis_utils.app.config["REDIS_URL"] = self.original_redis_url
        else:
            redis_utils.app.config.pop("REDIS_URL", None)

    def test_builds_redis_url_from_separate_env_vars(self):
        with patch.dict(
            "os.environ",
            {
                "REDIS_HOST": "redis.service",
                "REDIS_PORT": "6380",
                "REDIS_USERNAME": "default",
                "REDIS_PASSWORD": "pa:ss@word",
            },
            clear=True,
        ):
            result = redis_utils._build_redis_url()

        self.assertEqual(result, "redis://default:pa%3Ass%40word@redis.service:6380/0")

    def test_prefers_explicit_redis_url(self):
        with patch.dict(
            "os.environ",
            {
                "REDIS_URL": "redis://custom:6379/3",
                "REDIS_HOST": "redis.service",
            },
            clear=True,
        ):
            result = redis_utils._build_redis_url()

        self.assertEqual(result, "redis://custom:6379/3")


if __name__ == "__main__":
    unittest.main()
