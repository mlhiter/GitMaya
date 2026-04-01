import importlib
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

SERVER_DIR = Path(__file__).resolve().parents[1] / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

lark_base = importlib.import_module("tasks.lark.base")
from utils.constant import GitHubPermissionError


def _raw_message(open_id: str):
    return {
        "event": {
            "sender": {"sender_id": {"open_id": open_id}},
            "message": {"chat_type": "group"},
        }
    }


class TestLarkAuthTip(unittest.TestCase):
    def test_github_permission_error_mentions_operator_with_bind_link(self):
        @lark_base.with_authenticated_github()
        def create_issue_comment(app_id, message_id, content, raw_message):
            raise GitHubPermissionError("401")

        with patch.dict("os.environ", {"DOMAIN": "https://example.com"}, clear=False), patch(
            "tasks.lark.manage.send_manage_fail_message"
        ) as mock_send_fail:
            result = create_issue_comment(
                "cli_test",
                "om_test",
                {"text": "hello"},
                _raw_message("ou_test"),
            )

        self.assertIsNone(result)
        mock_send_fail.assert_called_once()
        content = mock_send_fail.call_args[0][0]
        self.assertIn("<at id=ou_test></at>", content)
        self.assertIn("评论失败", content)
        self.assertIn(
            "https://example.com/api/github/oauth?app_id=cli_test&open_id=ou_test", content
        )

    def test_missing_access_token_also_sends_bind_tip(self):
        @lark_base.with_authenticated_github()
        def create_issue_comment(app_id, message_id, content, raw_message):
            raise Exception("Failed to get access token.")

        with patch.dict("os.environ", {"DOMAIN": "https://example.com"}, clear=False), patch(
            "tasks.lark.manage.send_manage_fail_message"
        ) as mock_send_fail:
            result = create_issue_comment(
                "cli_test",
                "om_test",
                {"text": "hello"},
                _raw_message("ou_test"),
            )

        self.assertIsNone(result)
        mock_send_fail.assert_called_once()
        content = mock_send_fail.call_args[0][0]
        self.assertIn("评论失败", content)
        self.assertIn("请点击绑定 GitHub 账号后重试", content)

    def test_unrelated_exception_is_still_raised(self):
        @lark_base.with_authenticated_github()
        def create_issue_comment(app_id, message_id, content, raw_message):
            raise RuntimeError("boom")

        with patch("tasks.lark.manage.send_manage_fail_message") as mock_send_fail:
            with self.assertRaises(RuntimeError):
                create_issue_comment(
                    "cli_test",
                    "om_test",
                    {"text": "hello"},
                    _raw_message("ou_test"),
                )
        mock_send_fail.assert_not_called()


if __name__ == "__main__":
    unittest.main()
