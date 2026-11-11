"""Recent-report discovery and single-report digest publication, without models."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from support import RunFixture, tejun

D = tejun.digest


class DigestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
        self.reports = self.root / "reports"
        self.reports.mkdir()

    def report(self, started, text="Earlier findings", suffix="md"):
        path = self.reports / f"digest-{started:%Y%m%dT%H%M%SZ}-0123456789ab.{suffix}"
        path.write_text(text)
        return path

    def text(self, context):
        return f"# Digest\n\nCoverage: {context['start']} to {context['end']}\n\nNo verified updates in this research window.\n"

    def test_first_run_uses_24_hours(self):
        context = D.inventory(self.root, self.now)
        self.assertEqual(datetime.fromisoformat(context["start"]), self.now - timedelta(hours=24))
        self.assertEqual(context["recent_reports"], [])
        self.assertFalse(context["lookback_capped"])
        D.validate(self.text(context), context)

    def test_latest_report_sets_start_independent_of_mtime(self):
        older = self.report(self.now - timedelta(days=2))
        newer = self.report(self.now - timedelta(hours=3))
        older.touch()
        context = D.inventory(self.root, self.now)
        self.assertEqual(context["start"], (self.now - timedelta(hours=3)).isoformat())
        self.assertEqual(context["recent_reports"][0]["path"], str(newer))
        self.assertFalse(context["lookback_capped"])

    def test_long_absence_is_capped_at_seven_days(self):
        self.report(self.now - timedelta(days=60))
        context = D.inventory(self.root, self.now)
        self.assertEqual(context["start"], (self.now - timedelta(days=7)).isoformat())
        self.assertTrue(context["lookback_capped"])

    def test_context_is_bounded_and_truncation_is_explicit(self):
        for days in range(1, 8):
            self.report(self.now - timedelta(days=days), "x" * (D.REPORT_CONTEXT_CHARS + 500))
        recent = D.inventory(self.root, self.now)["recent_reports"]
        self.assertEqual(len(recent), 3)
        self.assertTrue(all(r["truncated"] for r in recent))
        self.assertTrue(all(len(r["excerpt"]) == D.REPORT_CONTEXT_CHARS for r in recent))

    def test_partials_legacy_history_and_unrelated_files_are_ignored(self):
        self.report(self.now - timedelta(hours=1), suffix="partial.md")
        (self.reports / "digest-not-a-run.md").write_text("not finalized")
        history = self.root / "history"
        history.mkdir()
        (history / "digest-broken.json").write_text("invalid old history")
        self.assertEqual(D.inventory(self.root, self.now)["recent_reports"], [])
        # A finalized report no longer requires a matching JSON record.
        self.report(self.now - timedelta(hours=2))
        self.assertEqual(len(D.inventory(self.root, self.now)["recent_reports"]), 1)

    def test_symlinks_and_future_timestamps(self):
        path = self.report(self.now - timedelta(hours=1))
        path.unlink()
        path.symlink_to(self.root / "outside")
        self.assertEqual(D.inventory(self.root, self.now)["recent_reports"], [])
        self.report(self.now + timedelta(hours=1))
        with self.assertRaisesRegex(ValueError, "ahead"):
            D.inventory(self.root, self.now)
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "reports").symlink_to(self.reports, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                D.inventory(Path(temp), self.now)

    def test_nonempty_window_on_same_second_repeat(self):
        self.report(self.now)
        context = D.inventory(self.root, self.now)
        self.assertLess(datetime.fromisoformat(context["start"]), self.now)

    def test_report_checks_only_integrity_and_period(self):
        context = D.inventory(self.root, self.now)
        for text in ("", "\x00", "Missing the research period"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                D.validate(text, context)
        D.validate(self.text(context) + "Some searches failed.\n", context)

    def test_worker_publishes_without_history_files(self):
        context = D.inventory(self.root, self.now)
        fixture = RunFixture(self.root, self.text(context))
        fixture.request.update(result_check="digest", digest_context=context)
        fixture.save()
        self.assertEqual(fixture.work(), 0)
        self.assertTrue(fixture.output.is_file())
        self.assertFalse((self.root / "history").exists())
        self.assertNotIn("history_output", fixture.final())

    def test_publication_failure_preserves_partial(self):
        context = D.inventory(self.root, self.now)
        fixture = RunFixture(self.root, self.text(context))
        fixture.request.update(result_check="digest", digest_context=context)
        fixture.save()
        with patch.object(tejun, "publish_result", side_effect=OSError("disk error")):
            self.assertEqual(fixture.work(), 1)
        self.assertTrue(fixture.partial.is_file())
        self.assertFalse(fixture.output.exists())
        self.assertEqual(fixture.final()["state"], "incomplete")


if __name__ == "__main__":
    unittest.main()
