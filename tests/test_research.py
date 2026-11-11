"""Credential-free opt-in and publication checks for S012."""
import json
import signal
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from support import RunFixture, configuration, prepared, tejun, workflow


class ResearchTests(unittest.TestCase):
    def test_opt_in_is_scoped_and_resources_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = configuration(root)
            with patch.object(tejun.shutil, "which", return_value="/fixture/bin/pi"):
                ordinary = tejun.prepare(workflow(), config)
                self.assertFalse(ordinary["research"])
                self.assertFalse(any("research.ts" in arg for arg in ordinary["pi_args"]))
                item = workflow(research=True, tools=["read", "write", "subagent", "web_search"])
                with self.assertRaisesRegex(tejun.TejunError, "subagent_extension"):
                    tejun.prepare(item, config)
                for key in ("subagent_extension", "search_extension"):
                    path = root / (key + ".ts")
                    path.write_text("fixture")
                    config["pi"][key] = str(path)
                (root / "workflow-resources.js").write_text("fixture")
                result = tejun.prepare(item, config)
                self.assertTrue(result["research"])
                self.assertIn(str(tejun.ROOT / "extensions/research.ts"), result["pi_args"])
                Path(config["pi"]["search_extension"]).unlink()
                with self.assertRaisesRegex(tejun.TejunError, "Missing Pi"):
                    tejun.prepare(item, config)

    def test_terminal_environment_is_scoped_to_research(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                request = prepared(root, research=enabled, search_extension="/fixture/search.ts",
                                   subagent_extension="/fixture/index.js")
                response = {"workspace": {"workspace_id": "w1"},
                            "root_pane": {"pane_id": "w1:p1"}, "tab": {"tab_id": "w1:t1"}}
                with patch.object(tejun, "STATE", root / "state"), \
                     patch.object(tejun, "ensure_session", return_value=[]), \
                     patch.object(tejun, "herdr", return_value=response) as herdr:
                    tejun.reserve_workflow_tab(workflow(), request, root, {})
                args = herdr.call_args.args
                self.assertEqual(f"TEJUN_CHILDREN_FILE={root / 'children.json'}" in args, enabled)
                self.assertEqual("TEJUN_SEARCH_EXTENSION=/fixture/search.ts" in args, enabled)

    def test_definition_requires_explicit_subagent_tool(self):
        for change in ({"research": "true"}, {"research": True}):
            with self.assertRaises(tejun.TejunError):
                tejun.validate_definition(workflow(**change), "fixture")

    def test_only_known_completed_children_allow_publication(self):
        for receipt in (None, {}, {"ready": True, "children": {}},
                        *({"ready": True, "children": {"child": state}}
                          for state in ("running", "rejected", "failed-or-unknown", "completed"))):
            with self.subTest(receipt=receipt), tempfile.TemporaryDirectory() as directory:
                fixture = RunFixture(Path(directory))
                fixture.request["research"] = True
                fixture.save()
                (fixture.root / "children.json.search.jsonl").write_text(
                    '{"ready":true,"tools":["read","web_search"]}\n{"search":"succeeded"}\n')
                if receipt is not None:
                    (fixture.root / "children.json").write_text(json.dumps(receipt))
                success = receipt == {"ready": True, "children": {"child": "completed"}}
                self.assertEqual(fixture.work(), 0 if success else 1)
                self.assertEqual(fixture.output.exists(), success)
                closed = any(call[:2] == ("agent", "send-keys") for call in fixture.calls)
                self.assertEqual(closed, success)
                self.assertEqual(fixture.partial.exists(), not success)

    def test_no_successful_search_cannot_publish(self):
        for evidence in (None, '', '{"search":"failed"}\n', 'invalid',
                         '{"ready":false}\n{"search":"succeeded"}\n',
                         '{"child_started":"orphan"}\n{"search":"succeeded"}\n'):
            with self.subTest(evidence=evidence), tempfile.TemporaryDirectory() as directory:
                fixture = RunFixture(Path(directory))
                fixture.request["research"] = True
                fixture.save()
                (fixture.root / "children.json").write_text(json.dumps(
                    {"ready": True, "children": {"child": "completed"}}))
                if evidence is not None:
                    (fixture.root / "children.json.search.jsonl").write_text(evidence)
                self.assertEqual(fixture.work(), 1)
                self.assertFalse(fixture.output.exists())

    def test_cancellation_retains_child_evidence_and_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = RunFixture(Path(directory))
            fixture.request["research"] = True
            fixture.save()
            evidence = fixture.root / "children.json"
            evidence.write_text('{"ready":true,"children":{"child":"running"}}')
            def interrupt(binary, *args, **kwargs):
                if args[:2] == ("agent", "prompt"):
                    raise tejun.RunInterrupted(signal.SIGTERM)
                return fixture.herdr(binary, *args, **kwargs)
            self.assertEqual(fixture.work(interrupt), 128 + signal.SIGTERM)
            self.assertIn("running", evidence.read_text())
            self.assertFalse(fixture.output.exists())
            self.assertFalse(any(call[:2] == ("agent", "send-keys") for call in fixture.calls))

    def test_parent_timeout_retains_child_evidence_and_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = RunFixture(Path(directory))
            fixture.request["research"] = True
            fixture.save()
            evidence = fixture.root / "children.json"
            evidence.write_text('{"ready":true,"children":{"child":"running"}}')
            def timeout(binary, *args, **kwargs):
                if args[:2] == ("agent", "prompt"):
                    raise tejun.TejunError("Timed out")
                return fixture.herdr(binary, *args, **kwargs)
            self.assertEqual(fixture.work(timeout), 1)
            self.assertIn("running", evidence.read_text())
            self.assertFalse(fixture.output.exists())
            self.assertFalse(any(call[:2] == ("agent", "send-keys") for call in fixture.calls))
