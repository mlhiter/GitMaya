import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SERVER_DIR = Path(__file__).resolve().parents[1] / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from tasks.lark import issue as issue_tasks


class TestIssueMentionMapping(unittest.TestCase):
    def test_unknown_mention_keeps_original_text(self):
        text = "@aimeritething 请帮忙看下"

        with patch(
            "tasks.lark.issue.get_openid_by_code_name", return_value=None
        ) as mock_lookup:
            result = issue_tasks.replace_code_name_to_im_name(text)

        self.assertEqual(result, text)
        mock_lookup.assert_called_once_with("aimeritething")

    def test_hyphen_github_name_can_be_converted_and_unknown_not_broken(self):
        text = "@felixqiu014-wq 看下，另外 @unknown-user 也关注下"

        def _lookup(name):
            if name == "felixqiu014-wq":
                return "ou_test_user"
            return None

        with patch("tasks.lark.issue.get_openid_by_code_name", side_effect=_lookup):
            result = issue_tasks.replace_code_name_to_im_name(text)

        self.assertIn('<at id="ou_test_user"></at>', result)
        self.assertIn("@unknown-user", result)
        self.assertNotIn('id="None"', result)

    def test_update_issue_card_passes_private_flag_to_card_builder(self):
        class _FakeQuery:
            def __init__(self, result):
                self._result = result

            def filter(self, *args, **kwargs):
                return self

            def first(self):
                return self._result

        class _FakeSession:
            def __init__(self, results):
                self._results = list(results)

            def query(self, *args, **kwargs):
                if not self._results:
                    raise AssertionError("Unexpected extra query call")
                return _FakeQuery(self._results.pop(0))

        class _FakeDB:
            def __init__(self, results):
                self.session = _FakeSession(results)

        issue = SimpleNamespace(id="issue-1", repo_id="repo-1", message_id="msg-1")
        repo = SimpleNamespace(
            id="repo-1",
            name="sealos-issues",
            chat_group_id="chat-1",
            extra={"private": True},
        )
        chat_group = SimpleNamespace(id="chat-1", im_application_id="im-app-1")
        team = SimpleNamespace(id="team-1", name="labring-sigs")
        application = SimpleNamespace(id="im-app-1", team_id="team-1")
        bot = SimpleNamespace(
            update=Mock(return_value=SimpleNamespace(json=Mock(return_value={"code": 0})))
        )

        with patch.object(
            issue_tasks, "db", _FakeDB([issue, repo, chat_group, team])
        ), patch.object(
            issue_tasks,
            "get_bot_by_application_id",
            return_value=(bot, application),
        ), patch.object(
            issue_tasks, "gen_issue_card_by_issue", return_value="card-content"
        ) as mock_gen_card:
            result = issue_tasks.update_issue_card.run("issue-1")

        self.assertEqual(result, {"code": 0})
        mock_gen_card.assert_called_once_with(
            bot,
            issue,
            "https://github.com/labring-sigs/sealos-issues",
            team,
            is_private=True,
        )
        bot.update.assert_called_once_with(
            message_id="msg-1",
            content="card-content",
        )


if __name__ == "__main__":
    unittest.main()
