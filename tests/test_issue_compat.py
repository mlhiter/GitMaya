import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SERVER_DIR = Path(__file__).resolve().parents[1] / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from tasks.github import issue as issue_tasks


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


class TestIssueCompat(unittest.TestCase):
    def test_on_issue_updated_backfills_missing_issue_and_sends_card(self):
        event = SimpleNamespace(
            repository=SimpleNamespace(id=1001),
            issue=SimpleNamespace(number=9),
        )
        repo = SimpleNamespace(id="repo-1")
        issue = SimpleNamespace(id="issue-1", issue_number=9)

        with patch.object(issue_tasks, "IssueEvent", return_value=event), patch.object(
            issue_tasks, "db", _FakeDB([repo])
        ), patch.object(
            issue_tasks, "_upsert_issue_from_event", return_value=(issue, True)
        ) as mock_upsert, patch.object(
            issue_tasks.send_issue_card,
            "delay",
            return_value=SimpleNamespace(id="task-card"),
        ) as mock_send_card, patch.object(
            issue_tasks.update_issue_card, "delay"
        ) as mock_update_card:
            result = issue_tasks.on_issue_updated.run({"ignored": True})

        self.assertEqual(result, ["task-card"])
        mock_upsert.assert_called_once_with(repo, event.issue)
        mock_send_card.assert_called_once_with(issue_id="issue-1")
        mock_update_card.assert_not_called()

    def test_on_issue_comment_created_backfills_missing_issue_then_chains_comment_sync(self):
        event = SimpleNamespace(
            repository=SimpleNamespace(id=1001),
            issue=SimpleNamespace(number=9, pull_request=None),
            comment=SimpleNamespace(body="hello", performed_via_github_app=None),
            sender=SimpleNamespace(login="alice"),
        )
        repo = SimpleNamespace(id="repo-1")
        issue = SimpleNamespace(id="issue-1", issue_number=9)

        workflow = SimpleNamespace(delay=Mock(return_value=SimpleNamespace(id="task-chain")))

        with patch.object(issue_tasks, "IssueCommentEvent", return_value=event), patch.object(
            issue_tasks, "db", _FakeDB([repo, None])
        ), patch.object(
            issue_tasks, "_upsert_issue_from_event", return_value=(issue, True)
        ) as mock_upsert, patch.object(
            issue_tasks.send_issue_card, "si", return_value="card-sig"
        ) as mock_card_si, patch.object(
            issue_tasks.send_issue_comment, "si", return_value="comment-sig"
        ) as mock_comment_si, patch.object(
            issue_tasks, "chain", return_value=workflow
        ) as mock_chain, patch.object(
            issue_tasks.send_issue_comment, "delay"
        ) as mock_send_comment_delay:
            result = issue_tasks.on_issue_comment_created.run({"ignored": True})

        self.assertEqual(result, ["task-chain"])
        mock_upsert.assert_called_once_with(repo, event.issue)
        mock_card_si.assert_called_once_with("issue-1")
        mock_comment_si.assert_called_once_with("issue-1", "hello", "alice")
        mock_chain.assert_called_once_with("card-sig", "comment-sig")
        workflow.delay.assert_called_once()
        mock_send_comment_delay.assert_not_called()


if __name__ == "__main__":
    unittest.main()
