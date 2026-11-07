"""Credential-free digest validation, coverage and publication checks."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_outcomes import RunFixture
from test_tejun import tejun

D = tejun.digest


class DigestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.context = D.inventory(self.root, datetime(2026, 11, 8, tzinfo=timezone.utc))
        self.record = {"version": 1, "start": self.context["start"], "end": self.context["end"],
                       "coverage": [{"subject": topic, "start": self.context["start"],
                                     "end": self.context["end"], "status": "checked", "reason": ""}
                                    for topic in D.TOPICS], "findings": []}
        self.report = ("# Digest - 2026-11-08\n\nCoverage: " + self.context["start"] +
                       " to " + self.context["end"] + "\n\nNo verified updates since the last check.\n")

    def test_first_window_and_empty_success(self):
        self.assertEqual(self.context["start"], "2026-11-07T00:00:00+00:00")
        self.assertIn("sha256", D.validate(self.report, self.record, self.context))

    def test_missing_topic_watchlist_and_failure_disclosure(self):
        bad = deepcopy(self.record)
        bad["coverage"].pop()
        with self.assertRaisesRegex(ValueError, "missing"):
            D.validate(self.report, bad, self.context)
        self.context["watchlist"] = ["case"]
        with self.assertRaisesRegex(ValueError, "missing"):
            D.validate(self.report, self.record, self.context)
        self.context.pop("watchlist")
        bad = deepcopy(self.record)
        bad["coverage"][0].update(status="failed", reason="search unavailable")
        with self.assertRaisesRegex(ValueError, "visible"):
            D.validate(self.report, bad, self.context)
        qualified = self.report + ("\nSome checks remain incomplete because sources were inaccessible. "
                                   "These checks will be retried.\n")
        D.validate(qualified, bad, self.context)
        with self.assertRaisesRegex(ValueError, "does not match"):
            D.validate(qualified, self.record, self.context)
        with self.assertRaisesRegex(ValueError, "coverage history"):
            D.validate(qualified + "\n## Research failures\n\nAI: timeout.\n", bad, self.context)

    def test_retained_sources_and_changed_period_are_checked(self):
        bad = deepcopy(self.record)
        bad["end"] = "2026-11-09T00:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "reserved"):
            D.validate(self.report, bad, self.context)
        bad = deepcopy(self.record)
        bad["findings"] = [{"subject": "tool", "summary": "Useful release", "date": "2026-11-08",
                            "change": "new", "sources": ["https://example.org/release"]}]
        with self.assertRaises(ValueError):
            D.validate(self.report, bad, self.context)
        report = self.report.replace("No verified updates since the last check.",
                                    "## Findings\n\n### Tool\nUseful release.\nhttps://example.org/release")
        D.validate(report, bad, self.context)

    def test_repeated_sources_require_material_change(self):
        finding = dict(subject="tool", summary="Release", date="2026-11-08", change="new",
                       sources=["https://example.org/release"])
        self.record["findings"] = [finding]
        self.context["previous"] = [deepcopy(self.record)]
        report = self.report.replace("No verified updates since the last check.",
                                    "## Findings\n\n### Tool\nhttps://example.org/release")
        with self.assertRaisesRegex(ValueError, "material change"):
            D.validate(report, self.record, self.context)
        finding["change"] = "Maintainers added a security correction."
        D.validate(report, self.record, self.context)

    def test_old_gap_requires_retry_until_resolved(self):
        previous = deepcopy(self.record)
        previous["coverage"][0].update(subject="old", status="failed", reason="timeout")
        self.context["previous"] = [previous]
        with self.assertRaisesRegex(ValueError, "gap retry"):
            D.validate(self.report, self.record, self.context)
        retry = dict(previous["coverage"][0], status="checked", reason="")
        self.record["coverage"].append(retry)
        D.validate(self.report, self.record, self.context)

    def fixture(self):
        (self.root / "reports").mkdir()
        (self.root / "history").mkdir()
        fixture = RunFixture(self.root, self.report)
        fixture.output = self.root / "reports/digest-run.md"
        fixture.status.update(output=str(fixture.output),
                              history_partial=str(self.root / "history/digest-run.partial.json"),
                              history_output=str(self.root / "history/digest-run.json"))
        fixture.request.update(result_check="digest", digest_context=self.context)
        Path(fixture.status["history_partial"]).write_text(json.dumps(self.record))
        fixture.save()
        return fixture

    def test_worker_publishes_pair_and_next_run_advances(self):
        fixture = self.fixture()
        self.assertEqual(fixture.work(), 0)
        context = D.inventory(self.root, datetime(2026, 11, 9, tzinfo=timezone.utc))
        self.assertEqual(context["start"], self.context["end"])
        self.assertEqual(len(context["previous"]), 1)
        self.assertTrue(fixture.final()["agent_exited"])

    def test_interrupted_pair_blocks_next_run_without_advancing(self):
        fixture = self.fixture()
        publish = tejun.publish_result
        def fail_history(partial, output):
            if output.suffix == ".json":
                raise OSError("simulated history publication failure")
            publish(partial, output)
        with patch.object(tejun, "publish_result", side_effect=fail_history):
            self.assertEqual(fixture.work(), 1)
        self.assertTrue(fixture.output.exists())
        self.assertEqual(fixture.final()["state"], "incomplete")
        with self.assertRaisesRegex(ValueError, "without history"):
            D.inventory(self.root)

    def test_tampering_symlinks_and_missing_reports_block_history(self):
        fixture = self.fixture()
        self.assertEqual(fixture.work(), 0)
        fixture.output.write_text("changed\n")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            D.inventory(self.root)
        fixture.output.unlink()
        with self.assertRaisesRegex(ValueError, "without report"):
            D.inventory(self.root)

    def test_invalid_history_and_symlink_directories_fail_closed(self):
        (self.root / "history").mkdir()
        path = self.root / "history/digest-bad.json"
        path.write_text("not json")
        with self.assertRaises(ValueError):
            D.inventory(self.root)
        path.unlink()
        (self.root / "history").rmdir()
        (self.root / "elsewhere").mkdir()
        (self.root / "history").symlink_to(self.root / "elsewhere", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            D.inventory(self.root)

    def test_invalid_partial_history_never_publishes_report(self):
        fixture = self.fixture()
        Path(fixture.status["history_partial"]).write_text("{}")
        self.assertEqual(fixture.work(), 1)
        self.assertFalse(fixture.output.exists())
        self.assertFalse(any(call[:2] == ("agent", "send-keys") for call in fixture.calls))

    def test_resolved_gap_does_not_require_another_retry(self):
        failed = deepcopy(self.record)
        failed["coverage"].append(dict(subject="old", start=failed["start"], end=failed["end"],
                                       status="failed", reason="timeout"))
        resolved = deepcopy(failed)
        resolved["end"] = "2026-11-08T01:00:00+00:00"
        resolved["coverage"][-1].update(status="checked", reason="")
        self.context["previous"] = [failed, resolved]
        D.validate(self.report, self.record, self.context)

    def test_removed_watchlist_case_does_not_retry_forever(self):
        previous = deepcopy(self.record)
        previous["coverage"].append(dict(subject="watch:removed", start=previous["start"],
                                         end=previous["end"], status="failed", reason="timeout"))
        self.context["previous"] = [previous]
        D.validate(self.report, self.record, self.context)

    def test_second_result_cannot_overwrite_existing_history(self):
        fixture = self.fixture()
        path = Path(fixture.status["history_output"])
        path.write_text("earlier data\n")
        self.assertEqual(fixture.work(), 1)
        self.assertEqual(path.read_text(), "earlier data\n")
        self.assertTrue(fixture.output.exists())
        with self.assertRaises(ValueError):
            D.inventory(self.root)

    def test_search_extension_and_workspace_preparation(self):
        agent = self.root / "agent"
        (agent / "skills/unslop").mkdir(parents=True)
        (agent / "AGENTS.md").write_text("fixture")
        (agent / "skills/unslop/SKILL.md").write_text("fixture")
        extension = self.root / "search.ts"
        extension.write_text("fixture")
        (self.root / "watchlist.md").write_text("# Watchlist\n\n- Case to follow\n")
        config = {"paths": {"digest_briefs": str(self.root)}, "pi": {
            "agent_dir": str(agent), "extensions": [], "search_extension": str(extension),
            "provider": "fixture", "model": "exact", "thinking": "off"}}
        workflow = tejun.definitions()["digest"]
        with patch.object(tejun.shutil, "which", side_effect=lambda name: "/bin/" + name):
            result = tejun.prepare(workflow, config)
        self.assertIn(str(extension), result["pi_args"])
        self.assertEqual(result["digest_context"]["watchlist"], ["Case to follow"])
        self.assertEqual(result["timeout"], 900)
        self.assertEqual(result["output_dir"], str(self.root / "reports"))


if __name__ == "__main__":
    unittest.main()
