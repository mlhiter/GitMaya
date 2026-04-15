import importlib
import sys
from pathlib import Path
import unittest

SERVER_DIR = Path(__file__).resolve().parents[1] / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

lark_manage = importlib.import_module("tasks.lark.manage")


class TestMatchRepoIdentity(unittest.TestCase):
    def test_parse_full_github_url(self):
        org, repo = lark_manage._parse_repo_identity(
            "https://github.com/labring/GitMaya"
        )
        self.assertEqual(org, "labring")
        self.assertEqual(repo, "GitMaya")

    def test_parse_git_suffix(self):
        org, repo = lark_manage._parse_repo_identity(
            "https://github.com/labring/GitMaya.git"
        )
        self.assertEqual(org, "labring")
        self.assertEqual(repo, "GitMaya")

    def test_parse_repo_without_scheme(self):
        org, repo = lark_manage._parse_repo_identity("github.com/labring/GitMaya")
        self.assertEqual(org, "labring")
        self.assertEqual(repo, "GitMaya")


if __name__ == "__main__":
    unittest.main()
