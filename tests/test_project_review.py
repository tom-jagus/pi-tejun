"""Generated report structure and launcher integration, without model calls.

These checks do not establish Pi's coverage or recommendation quality.
"""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from support import RunFixture, tejun


TITLE = "# Project review - Saturday November 7, 2026\n\n"


class ProjectReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.roots = {name: str(self.root / name) for name in (
            "client_projects", "personal_projects", "personal_repositories")}
        for value in self.roots.values():
            Path(value).mkdir()
        self.request = {"result_check": "project-review", "context_paths": self.roots,
                        "excluded_paths": []}
        self.client = Path(self.roots["client_projects"])
        self.personal = Path(self.roots["personal_projects"])
        self.repo = Path(self.roots["personal_repositories"])

    def entry(self, path, modified="2026-10-01", reason="S001 awaits a user decision.",
              action="Resolve the recorded question before implementation."):
        return f"#### {path}\n\nlast modified: {modified}\n\n- {reason}\n- {action}\n\n"

    def report(self, entries=None):
        return (TITLE + "## Client projects\n\nNo client projects found.\n\n"
                "## Personal projects\n\n### Blocked or awaiting input\n\n" +
                (entries if entries is not None else self.entry(self.personal / "one")) +
                "## Summary\n\nResolve the oldest pending decision first.\n")

    def check(self, text, request=None):
        return tejun.validate_project_report(text, request or self.request)

    def test_valid_report_and_empty_groups(self):
        self.check(self.report())
        empty = TITLE + "## Client projects\n\nNo client projects found.\n\n## Personal projects\n\nNo personal projects found.\n"
        self.check(empty)
        self.check(self.report().split("## Summary")[0])
        self.check(self.report().replace("before implementation.", "before\n  implementation."))

    def test_title_date_requires_canonical_format_and_correct_weekday(self):
        for title in ("# Project review Saturday 2026-11-07",
                      "# Project review - Saturday 2026-11-07",
                      "# Project review - Sunday November 7, 2026",
                      "# Project review - Saturday November 07, 2026",
                      "# Project review - Saturday February 30, 2026",
                      "# Project review - Sat Nov 7, 2026",
                      "# Project review - Saturday November 7, 2026 "):
            with self.subTest(title=title), self.assertRaises(tejun.TejunError):
                self.check(self.report().replace(TITLE, title + "\n\n"))
        self.check(self.report().replace(TITLE, "# Project review - Sunday November 8, 2026\n\n"))

    def test_legacy_layout_is_rejected(self):
        with self.assertRaises(tejun.TejunError):
            self.check("# Client project\n\nNo client projects found.\n\n"
                       "# Personal projects\n\nNo personal projects found.\n")

    def test_client_first_category_order_and_visible_recency(self):
        text = (TITLE + "## Client projects\n\n### Blocked or awaiting input\n\n" +
                self.entry(self.client / "decision", "2026-11-01") +
                "### Quick wins\n\n" + self.entry(self.client / "quick", "2026-08-01") +
                "### Other unfinished work\n\n" + self.entry(self.client / "other", "2026-07-01") +
                "## Personal projects\n\n### Blocked or awaiting input\n\n" +
                self.entry(self.personal / "old", "2026-01-01") +
                self.entry(self.personal / "new", "2026-10-01") +
                self.entry(self.personal / "unknown-a", "unavailable") +
                self.entry(self.personal / "unknown-b", "unavailable") +
                "### Quick wins\n\n" + self.entry(self.repo / "quick", "2026-01-01"))
        self.check(text)
        # A date-only report cannot establish the order of timestamps within a day.
        self.check(self.report(self.entry(self.personal / "z") + self.entry(self.personal / "a")))
        invalid = [
            self.report(self.entry(self.personal / "new", "2026-11-01") +
                        self.entry(self.personal / "old", "2026-01-01")),
            self.report(self.entry(self.personal / "unknown", "unavailable") +
                        self.entry(self.personal / "known")),
            self.report(self.entry(self.personal / "z", "unavailable") +
                        self.entry(self.personal / "a", "unavailable")),
            self.report().replace("Blocked or awaiting input", "Quick wins").replace(
                "## Summary", "### Blocked or awaiting input\n\n" +
                self.entry(self.personal / "other") + "## Summary"),
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(tejun.TejunError):
                self.check(value)

    def test_unknown_dates_need_attention_not_quick_win(self):
        with self.assertRaisesRegex(tejun.TejunError, "unavailable date"):
            self.check(self.report(self.entry(self.personal / "one", "unavailable")).replace(
                "Blocked or awaiting input", "Quick wins"))

    def test_rejects_wrong_paths_exclusions_duplicates_and_symlink_aliases(self):
        excluded = self.personal / "output"
        self.request["excluded_paths"] = [str(excluded)]
        (self.personal / "alias").symlink_to(self.root, target_is_directory=True)
        invalid = [self.report(self.entry(self.client / "wrong-group")),
                   self.report(self.entry(self.root / "outside")),
                   self.report(self.entry(self.personal / "nested/project")),
                   self.report(self.entry(self.personal / "alias/outside")),
                   self.report(self.entry(excluded)),
                   self.report(self.entry(self.personal / "one") * 2),
                   self.report().replace(str(self.personal / "one"), "relative/project")]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(tejun.TejunError):
                self.check(value)

    def test_unresolvable_path_is_an_actionable_validation_error(self):
        with patch.object(Path, "resolve", side_effect=RuntimeError("symlink loop")):
            with self.assertRaisesRegex(tejun.TejunError, "cannot resolve project path"):
                self.check(self.report())

    def test_rejects_expanded_malformed_or_non_concise_reports(self):
        valid = self.report()
        invalid = [
            "# Review\n\n" + valid,
            valid.replace("## Client projects", "## Clients"),
            valid.replace("## Personal projects", "## Extra\n\n## Personal projects"),
            valid.replace("## Client projects", "## Clients projects"),
            valid.replace("### Blocked or awaiting input", "## Blocked or awaiting input"),
            valid.replace("#### ", "### "),
            valid.replace("## Client projects", "A preamble.\n\n## Client projects"),
            valid.replace("2026-10-01", "2026-02-30"),
            valid.replace("2026-10-01", "2026-1-1"),
            valid.replace("last modified:", "Work records last modified:"),
            valid.replace("- S001", "- [S001](docs/project/work/S001.md)"),
            valid.replace("before implementation.", "before implementation.\n  - Nested evidence."),
            valid.replace("before implementation.", "before implementation.\n  ### Nested heading"),
            valid.replace("- S001", "- Reason: S001"),
            valid.replace("- Resolve", "- Suggested next action: Resolve"),
            valid.replace("- S001 awaits a user decision.", "- " + "word " * 41),
            valid.replace("## Summary", "- A third bullet.\n\n## Summary"),
            valid.replace("## Summary", "An additional outcome paragraph.\n\n## Summary"),
            valid + "# Methodology\n\nA long explanation.\n",
            valid.replace("Resolve the oldest pending decision first.", "word " * 71),
            valid.replace("Resolve the oldest pending decision first.", "- A summary list."),
            valid.replace("Resolve the oldest pending decision first.", ""),
            valid.replace("### Blocked or awaiting input", "### Unexpected category"),
            valid + "```\n",
            valid + "\x00\n",
            valid.rstrip("\n"),
        ]
        for number, value in enumerate(invalid):
            with self.subTest(case=number), self.assertRaises(tejun.TejunError):
                self.check(value)

    def test_structure_does_not_claim_to_validate_discovery_or_judgment(self):
        project = self.personal / "not-listed/docs/project/work"
        project.mkdir(parents=True)
        (project / "B001-open.md").write_text("---\nid: B001\nstatus: To do\n---\n")
        # An independent inventory/assessment is deliberately not inside this validator.
        self.check(TITLE + "## Client projects\n\nNo client projects found.\n\n"
                   "## Personal projects\n\nNo personal projects found.\n")
        self.check(self.report().replace("S001 awaits a user decision.",
                                         "A well-formed but unsupported statement."))

    def configuration(self):
        agent = self.root / "agent"
        (agent / "skills/unslop").mkdir(parents=True, exist_ok=True)
        (agent / "AGENTS.md").write_text("Fixture instructions.\n")
        (agent / "skills/unslop/SKILL.md").write_text("Fixture skill.\n")
        workspace = self.root / "reports"
        workspace.mkdir(exist_ok=True)
        return {"paths": {**self.roots, "project_directions": str(workspace),
                          "content_production": str(self.personal / "content-production")},
                "pi": {"agent_dir": str(agent), "extensions": [], "provider": "fixture",
                       "model": "exact", "thinking": "off"}}

    def test_definition_and_prompt_agree_with_report_layout(self):
        definition = tejun.definitions()["project-review"]
        self.assertEqual(definition["heading"], "# Project review - ")
        prompt = definition["prompt"]
        self.assertIn("Run the predefined project-review workflow.", prompt)
        self.assertIn(TITLE.strip(), prompt)
        for heading in ("## Client projects", "## Personal projects", "## Summary",
                        "### Blocked or awaiting input", "### Quick wins",
                        "### Other unfinished work", "Each project heading is ####"):
            self.assertIn(heading, prompt)

    def test_preparation_passes_only_configured_roots_and_uses_saved_defaults(self):
        config = self.configuration()
        definition = tejun.definitions()["project-review"]
        with patch.object(tejun.shutil, "which", side_effect=lambda name: f"/bin/{name}"), \
             patch.object(tejun, "herdr") as herdr:
            result = tejun.prepare(definition, config)
        self.assertIsNone(result["expected"])
        self.assertIsNone(result["input"])
        self.assertEqual(result["context_paths"], self.roots)
        self.assertEqual(result["result_check"], "project-review")
        self.assertEqual(result["provider"], "fixture")
        self.assertEqual(result["model"], "exact")
        self.assertIn("read,write,bash", result["pi_args"])
        self.assertEqual(result["output_dir"], config["paths"]["project_directions"])
        self.assertIn(config["paths"]["project_directions"], result["excluded_paths"])
        self.assertIn(config["paths"]["content_production"], result["excluded_paths"])
        self.assertEqual(list(Path(result["output_dir"]).iterdir()), [])
        herdr.assert_not_called()

    def test_missing_or_unreadable_root_fails_before_launch(self):
        config = self.configuration()
        definition = tejun.definitions()["project-review"]
        invalid = deepcopy(config)
        invalid["paths"].pop("client_projects")
        with patch.object(tejun, "herdr") as herdr:
            with self.assertRaisesRegex(tejun.TejunError, "client_projects"):
                tejun.prepare(definition, invalid)
            invalid["paths"]["client_projects"] = str(self.root / "absent")
            with self.assertRaisesRegex(tejun.TejunError, "Missing project-review root"):
                tejun.prepare(definition, invalid)
            with patch.object(tejun.os, "scandir", side_effect=PermissionError("denied")):
                with self.assertRaisesRegex(tejun.TejunError, "Cannot list project-review root"):
                    tejun.prepare(definition, config)
            config["paths"]["personal_projects"] = config["paths"]["client_projects"]
            with self.assertRaisesRegex(tejun.TejunError, "distinct"):
                tejun.prepare(definition, config)
            herdr.assert_not_called()

    def test_definition_rejects_mixed_modes_unknown_checks_and_missing_tools(self):
        definition = tejun.definitions()["project-review"]
        for changes in ({"input": "input.md"}, {"result_text": "Body"},
                        {"result_check": "anything"}, {"result_check": []},
                        {"tools": ["read", "write"]},
                        {"context_paths": []}, {"excluded_paths": "wrong"}):
            with self.subTest(changes=changes), self.assertRaises(tejun.TejunError):
                tejun.validate_definition({**definition, **changes}, "fixture")

    def test_worker_requires_valid_structure_and_uses_existing_publication(self):
        for valid in (True, False):
            with self.subTest(valid=valid), tempfile.TemporaryDirectory() as temp:
                result = self.report() if valid else self.report().replace("Saturday", "Sunday")
                fixture = RunFixture(Path(temp), result)
                fixture.request.update(self.request)
                fixture.request.pop("expected")
                fixture.save()
                self.assertEqual(fixture.work(), 0 if valid else 1)
                status = fixture.final()
                self.assertEqual(status["state"], "success" if valid else "incomplete")
                self.assertEqual(fixture.output.exists(), valid)
                self.assertEqual(fixture.partial.exists(), not valid)
                if valid:
                    self.assertTrue(status["agent_exited"])
                    self.assertTrue(status["tab_closed"])
                    self.assertEqual(fixture.output.read_text(), self.report())
                else:
                    self.assertIn("Invalid project review", status["reason"])
                    self.assertNotIn("agent_exited", status)
                    self.assertNotIn("tab_closed", status)
                    self.assertFalse(any(call[:2] == ("agent", "send-keys")
                                         for call in fixture.calls))

    def test_generated_result_symlink_cannot_publish(self):
        fixture = RunFixture(self.root, None)
        earlier = self.root / "earlier.md"
        earlier.write_text(self.report())
        fixture.partial.symlink_to(earlier)
        fixture.request.update(self.request)
        fixture.save()
        self.assertEqual(fixture.work(), 1)
        self.assertFalse(fixture.output.exists())
        self.assertTrue(fixture.partial.is_symlink())


if __name__ == "__main__":
    unittest.main()
