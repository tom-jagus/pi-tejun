"""Decision inputs, bounded report context, and Markdown-only content research."""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import content_research as research
from support import RunFixture, configuration, tejun


class ContentResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("pursue", "reject"):
            (self.root / f"{name}.json").write_text("[]\n")
        self.now = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
        self.context = research.inventory(self.root, "four-weeks", self.now)
        self.report = "# Content research\n\nA useful tool: https://example.org/tool\n"

    def test_windows_and_local_week(self):
        self.assertEqual(self.context["start"], "2026-10-11T12:00:00+00:00")
        self.assertEqual(self.context["week_start"], "2026-11-08")
        self.assertEqual(self.context["week_end"], "2026-11-14")
        saturday = datetime.fromisoformat("2026-11-14T23:59:00-08:00")
        self.assertEqual(research.inventory(self.root, "four-weeks", saturday)["week_start"], "2026-11-08")
        context = research.inventory(self.root, "three-months", datetime(2026, 5, 31, tzinfo=timezone.utc))
        self.assertTrue(context["start"].startswith("2026-02-28"))
        with self.assertRaises(ValueError):
            research.inventory(self.root, "unknown", self.now)

    def test_decision_inputs_are_required_valid_and_nonconflicting(self):
        path = self.root / "pursue.json"
        for raw in ('{}', 'invalid', '[{"id":"x"}]',
                    '[{"id":"x","subject":"X","sources":["not a URL"]}]'):
            path.write_text(raw)
            with self.assertRaises(ValueError):
                research.decisions(self.root)
        path.unlink()
        with self.assertRaises(ValueError):
            research.decisions(self.root)
        entry = {"id": "tool", "subject": "Example tool", "reason": "Interested"}
        path.write_text(json.dumps([entry]))
        self.assertEqual(research.decisions(self.root)["pursue"], [entry])
        (self.root / "reject.json").write_text(json.dumps([entry]))
        with self.assertRaisesRegex(ValueError, "conflicting"):
            research.decisions(self.root)

    def test_decision_changes_during_run_stop_publication(self):
        research.validate(self.report, self.context, self.root)
        (self.root / "reject.json").write_text('[{"id":"x","subject":"X"}]')
        with self.assertRaisesRegex(ValueError, "changed"):
            research.validate(self.report, self.context, self.root)

    def test_recent_reports_need_no_history_and_do_not_change_window(self):
        reports = self.root / "reports"
        reports.mkdir()
        prior = reports / "content-research-20261107T120000Z-0123456789ab.md"
        prior.write_text("A prior idea")
        history = self.root / "history"
        history.mkdir()
        (history / "content-research-broken.json").write_text("invalid legacy history")
        context = research.inventory(self.root, "four-weeks", self.now)
        self.assertEqual(context["start"], self.context["start"])
        self.assertEqual(context["recent_reports"][0]["excerpt"], "A prior idea")
        self.assertNotIn("previous", context)
        self.assertNotIn("decision_hashes", context)

    def test_empty_and_nul_reports_are_rejected(self):
        for text in ("", " \n", "bad\x00"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                research.validate(text, self.context, self.root)
        research.validate(self.report + "Some searches failed.\n", self.context, self.root)

    def test_preparation_and_worker_publish_only_report(self):
        item = tejun.definitions()["content-research"]
        config = configuration(self.root)
        config["paths"]["content_production"] = str(self.root)
        for name in ("subagent_extension", "search_extension"):
            path = self.root / (name + ".ts")
            path.write_text("fixture")
            config["pi"][name] = str(path)
        (self.root / "workflow-resources.js").write_text("fixture")
        with patch.object(tejun.shutil, "which", return_value="/bin/fixture"):
            prepared = tejun.prepare({**item, "skills": []}, config)
        self.assertTrue(prepared["research"])
        self.assertNotIn("brand_paths", prepared["research_context"])
        fixture = RunFixture(self.root, self.report)
        fixture.request.update(result_check="content-research", research=True,
                               workspace=str(self.root), research_context=self.context)
        fixture.save()
        (self.root / "children.json").write_text('{"ready":true,"children":{"child":"completed"}}')
        (self.root / "children.json.search.jsonl").write_text('{"search":"succeeded"}\n')
        self.assertEqual(fixture.work(), 0)
        self.assertEqual(fixture.output.read_text(), self.report)
        self.assertFalse((self.root / "history").exists())
        self.assertNotIn("history_output", fixture.final())
        self.assertEqual((self.root / "pursue.json").read_text(), "[]\n")

    def test_worker_retains_partial_when_decisions_change(self):
        fixture = RunFixture(self.root, self.report)
        fixture.request.update(result_check="content-research", workspace=str(self.root),
                               research_context=self.context)
        fixture.save()
        (self.root / "pursue.json").write_text('[{"id":"x","subject":"X"}]')
        self.assertEqual(fixture.work(), 1)
        self.assertFalse(fixture.output.exists())
        self.assertTrue(fixture.partial.exists())
        self.assertIn("changed", fixture.final()["reason"])


if __name__ == "__main__":
    unittest.main()
