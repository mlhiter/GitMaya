import sys
from pathlib import Path
import unittest

SERVER_DIR = Path(__file__).resolve().parents[1] / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from utils.lark.parser import GitMayaLarkParser


class TestLarkParserNormalize(unittest.TestCase):
    def setUp(self):
        self.parser = GitMayaLarkParser()

    def test_issue_without_space_should_auto_insert(self):
        normalized = self.parser._normalize_command("@Gitmaya /issue这个消息")
        self.assertEqual(normalized, "/issue 这个消息")

    def test_match_without_space_should_auto_insert(self):
        normalized = self.parser._normalize_command(
            "@Gitmaya /matchhttps://github.com/labring/GitMaya"
        )
        self.assertEqual(normalized, "/match https://github.com/labring/GitMaya")

    def test_normal_command_should_keep(self):
        normalized = self.parser._normalize_command("@Gitmaya /issue 这个消息")
        self.assertEqual(normalized, "/issue 这个消息")


if __name__ == "__main__":
    unittest.main()
