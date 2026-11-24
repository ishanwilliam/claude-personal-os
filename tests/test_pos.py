import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import pos  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "session.jsonl"


def run(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        pos.main(list(argv))
    return buf.getvalue()


class PosTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        projects = self.tmp / "projects" / "-home-user-app"
        projects.mkdir(parents=True)
        (projects / "abc12345-session.jsonl").write_text(FIXTURE.read_text())
        pos.PROJECTS_DIR = self.tmp / "projects"
        pos.HISTORY_FILE = self.tmp / "history.jsonl"
        pos.STATE_DIR = self.tmp / "state"
        pos.STATE_FILE = pos.STATE_DIR / "state.json"
        pos.SKILL_DIR = self.tmp / "skill"

    def prompts(self, since=None):
        return [p[2] for p in pos.read_session(next(pos.iter_sessions()), since)]

    def test_keeps_only_human_prompts(self):
        self.assertEqual(self.prompts(), [
            "always run the tests first",
            "/review fix the login",
            "legacy prompt without origin",
            "look at this\n[pasted]\n" + "x" * pos.PASTE_LIMIT + "\n[/pasted]",
        ])

    def test_previous_reply_is_context(self):
        rows = list(pos.read_session(next(pos.iter_sessions())))
        self.assertEqual(rows[1][3], "Done, tests pass.")

    def test_since_filters_prompts(self):
        since = pos.parse_ts("2026-01-02T00:00:00Z")
        self.assertEqual(self.prompts(since), self.prompts()[2:])

    def test_extract_writes_chunks(self):
        out = json.loads(run("extract", "--all", "--out", str(self.tmp / "work")))
        self.assertEqual((out["sessions"], out["prompts"], out["chunks"]), (1, 4, 1))
        body = (self.tmp / "work" / "chunk-001.md").read_text()
        self.assertIn("USER [2026-01-01T10:00]: always run the tests first", body)
        self.assertNotIn("system-reminder", body)

    def test_extract_clears_last_runs_observations_and_draft(self):
        work = self.tmp / "work"
        (work / "draft").mkdir(parents=True)
        (work / "obs-004.md").write_text("stale")
        run("extract", "--all", "--out", str(work))
        self.assertEqual(sorted(p.name for p in work.iterdir()), ["chunk-001.md", "index.md"])

    def test_strips_unknown_injected_tags_but_keeps_pasted_html(self):
        raw = "<ide_opened_file>a</ide_opened_file><browser_instruction>b\n</browser_instruction>fix the bug"
        self.assertEqual(pos.clean_prompt(raw), "fix the bug")
        self.assertEqual(pos.clean_prompt("<p>repair this</p>"), "<p>repair this</p>")
        self.assertIsNone(pos.clean_prompt("<task-notification>done</task-notification>"))

    def test_history_fills_expired_sessions_only(self):
        def row(sid, text, day):
            ts = datetime(2026, 1, day, tzinfo=timezone.utc).timestamp() * 1000
            return json.dumps({"display": text, "timestamp": ts, "project": "/home/user/old", "sessionId": sid,
                               "pastedContents": {"1": {"content": "log"}}})
        pos.HISTORY_FILE.write_text("\n".join([row("gone0001", "old prompt", 1), row("abc12345-session", "dup", 1)]))
        sessions = pos.select_sessions()
        self.assertEqual([s["source"] for s in sessions], ["history", "transcript"])
        self.assertEqual(sessions[0]["rows"][0][2], "old prompt\n[pasted]\nlog\n[/pasted]")
        out = json.loads(run("extract", "--all", "--out", str(self.tmp / "work")))
        self.assertEqual((out["sessions"], out["from_history"]), (2, 1))
        self.assertIn("/home/user/old | 1 | 1", (self.tmp / "work" / "index.md").read_text())

    def test_excluded_projects_are_skipped_in_both_sources(self):
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000
        pos.HISTORY_FILE.write_text(json.dumps({"display": "x", "timestamp": ts, "project": "/home/user/app-old",
                                                "sessionId": "gone0001"}))
        pos.save_state({"exclude_projects": ["/home/user/app"]})
        self.assertEqual(pos.select_sessions(), [])

    def test_skips_the_running_session(self):
        with mock.patch.dict(os.environ, {"CLAUDE_CODE_SESSION_ID": "abc12345-session"}):
            self.assertEqual(pos.select_sessions(), [])

    def test_nudge_when_never_built_then_once_a_day(self):
        self.assertIn("/claude-personal-os:build", run("nudge"))
        self.assertEqual(run("nudge"), "")

    def test_mark_then_nudge_only_past_threshold(self):
        run("mark", "--kind", "build", "--through", "2026-01-03T00:00:00+00:00")
        pos.SKILL_DIR.mkdir()
        (pos.SKILL_DIR / "SKILL.md").write_text("x")
        self.assertEqual(run("nudge"), "")
        state = pos.load_state()
        state["nudge_after_sessions"] = 1
        state["last_extracted_through"] = "2025-12-01T00:00:00+00:00"
        pos.save_state(state)
        self.assertIn("/claude-personal-os:update", run("nudge"))

    def test_days_threshold_needs_new_sessions(self):
        old = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        self.assertIsNone(pos.due({**pos.DEFAULTS, "last_extracted_through": old}, 0))
        self.assertIn("days", pos.due({**pos.DEFAULTS, "last_extracted_through": old}, 1))


if __name__ == "__main__":
    unittest.main()
