"""S003 failure checks. All files and processes are disposable fixtures."""

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from test_tejun import ROOT, tejun


class RunFixture:
    def __init__(self, root, content="# Expected\n"):
        self.root = root
        self.partial = root / "result.partial.md"
        self.output = root / "result.md"
        if content is not None:
            self.partial.write_text(content)
        self.status = {"workflow": "fixture", "run": root.name, "state": "started",
                       "pane": "w1:p9", "tab": "w1:t9", "partial": str(self.partial),
                       "output": str(self.output)}
        self.request = {"herdr": "fixture", "name": "tejun-fixture", "prompt": "fixture",
                        "timeout": 1, "expected": "# Expected\n"}
        self.calls = []
        self.save()

    def save(self):
        (self.root / "status.json").write_text(json.dumps(self.status))
        (self.root / "request.json").write_text(json.dumps(self.request))

    def final(self):
        return json.loads((self.root / "status.json").read_text())

    def herdr(self, binary, *args, **kwargs):
        self.calls.append(args)
        if args[:2] == ("agent", "get"):
            return {"agent": {"agent_status": "done"}}
        if args[:2] == ("pane", "list"):
            return {"panes": [{"pane_id": "w1:p9", "tab_id": "w1:t9"}]}
        return {}

    def work(self, herdr=None):
        with patch.object(tejun, "herdr", side_effect=herdr or self.herdr), redirect_stdout(io.StringIO()):
            return tejun.worker(self.root)


class OutcomeTests(unittest.TestCase):
    def test_missing_empty_wrong_and_old_results_cannot_establish_success(self):
        for content in (None, "", "incorrect\n"):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as temp:
                fixture = RunFixture(Path(temp), content)
                fixture.output.write_text("Earlier accepted result\n")
                self.assertEqual(fixture.work(), 1)
                final = fixture.final()
                self.assertEqual(final["state"], "incomplete")
                self.assertIn("Expected Markdown", final["reason"])
                self.assertEqual(fixture.output.read_text(), "Earlier accepted result\n")
                self.assertFalse(any(c[:2] == ("agent", "send-keys") for c in fixture.calls))
                self.assertIn("finished_at", final)
                self.assertEqual(final["partial"], str(fixture.partial))

    def test_symlink_to_older_exact_result_is_not_current_work(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = RunFixture(Path(temp), None)
            fixture.output.write_text(fixture.request["expected"])
            fixture.partial.symlink_to(fixture.output)
            self.assertEqual(fixture.work(), 1)
            self.assertEqual(fixture.final()["state"], "incomplete")

    def test_execution_timeout_and_cancellation_retain_partial_and_reason(self):
        for error, expected_code in ((tejun.TejunError("Herdr wait timed out"), 1),
                                     (tejun.TejunError("agent disappeared"), 1),
                                     (tejun.RunInterrupted(signal.SIGTERM), 143),
                                     (tejun.RunInterrupted(signal.SIGINT), 130)):
            with self.subTest(error=error), tempfile.TemporaryDirectory() as temp:
                fixture = RunFixture(Path(temp))
                def fail(binary, *args, **kwargs):
                    raise error
                self.assertEqual(fixture.work(fail), expected_code)
                final = fixture.final()
                self.assertEqual(final["state"], "incomplete")
                self.assertIn(str(error), final["reason"])
                self.assertTrue(fixture.partial.exists())
                self.assertFalse(fixture.output.exists())

    def test_unsettled_agents_are_not_closed_even_with_exact_output(self):
        for state in ("blocked", "unknown", "working"):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as temp:
                fixture = RunFixture(Path(temp))
                def unsettled(binary, *args, **kwargs):
                    if args[:2] == ("agent", "get"):
                        return {"agent": {"agent_status": state}}
                    return fixture.herdr(binary, *args, **kwargs)
                self.assertEqual(fixture.work(unsettled), 1)
                self.assertIn(state, fixture.final()["reason"])
                self.assertFalse(any(c[:2] == ("agent", "send-keys") for c in fixture.calls))
                self.assertFalse(fixture.output.exists())

    def test_invalid_request_is_recorded_as_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = RunFixture(Path(temp))
            (fixture.root / "request.json").write_text("not JSON")
            self.assertEqual(fixture.work(), 1)
            self.assertIn("Invalid run record", fixture.final()["reason"])
            self.assertEqual(fixture.calls, [])

    def test_pi_must_exit_before_result_is_published(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = RunFixture(Path(temp))
            def busy(binary, *args, **kwargs):
                if args[:2] == ("pane", "list"):
                    return {"panes": [{"pane_id": "w1:p9", "agent": "pi"}]}
                return fixture.herdr(binary, *args, **kwargs)
            with patch.object(tejun.time, "monotonic", side_effect=[0, 11]):
                self.assertEqual(fixture.work(busy), 1)
            self.assertIn("Pi did not exit", fixture.final()["reason"])
            self.assertTrue(fixture.partial.exists())
            self.assertFalse(fixture.output.exists())

    def test_subprocess_timeout_has_actionable_diagnostic(self):
        with patch.object(tejun.subprocess, "run", side_effect=subprocess.TimeoutExpired("fixture", 1)):
            with self.assertRaisesRegex(tejun.TejunError, "fixture failed.*timed out"):
                tejun.command(["fixture"], timeout=1)

    def test_invalid_configuration_and_definitions_fail_before_herdr(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            agent = root / "agent"
            agent.mkdir()
            (agent / "AGENTS.md").write_text("Fixture instructions\n")
            workflow = tejun.definitions()["content-smoke-test"]
            config = {"pi": {"agent_dir": str(agent), "extensions": [],
                             "provider": "fixture", "model": "exact", "thinking": "off"},
                      "paths": {"content_production": str(root)}}
            cases = [({}, "pi must be a table"),
                     ({"pi": {}}, "paths must be a table"),
                     ({**config, "paths": {}}, "paths.content_production"),
                     ({**config, "pi": {**config["pi"], "extensions": "wrong"}}, "pi.extensions"),
                     ({**config, "pi": {**config["pi"], "timeout_seconds": True}}, "timeout_seconds")]
            with patch.object(tejun, "herdr") as herdr:
                for invalid, reason in cases:
                    with self.subTest(reason=reason), self.assertRaisesRegex(tejun.TejunError, reason):
                        tejun.prepare(workflow, invalid)
                for changes, reason in (({"prompt": "{unknown}"}, "Invalid prompt"),
                                        ({"skills": "unslop"}, "skills"),
                                        ({"input": "input.md"}, "exactly one")):
                    with self.subTest(changes=changes), self.assertRaisesRegex(tejun.TejunError, reason):
                        tejun.prepare({**workflow, **changes}, config)
                herdr.assert_not_called()

    def test_all_enabled_workflows_are_validated_before_any_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            agent = root / "agent"
            (agent / "skills/unslop").mkdir(parents=True)
            (agent / "AGENTS.md").write_text("Fixture instructions\n")
            (agent / "skills/unslop/SKILL.md").write_text("Fixture skill\n")
            (root / "input.md").write_text("Input\n")
            config = {"enabled": ["verify", "content-smoke-test"],
                      "pi": {"agent_dir": str(agent), "extensions": [],
                             "provider": "fixture", "model": "exact", "thinking": "off"},
                      "paths": {"verification": str(root)}}
            original = tejun.load_toml
            config_path = root / "config.toml"
            config_path.touch()
            def load(path):
                return config if path == config_path else original(path)
            with patch.object(tejun, "CONFIG", config_path), \
                 patch.object(tejun, "load_toml", side_effect=load), \
                 patch.object(tejun.shutil, "which", side_effect=lambda name: f"/bin/{name}"), \
                 patch.object(tejun, "ensure_session") as session, \
                 patch.object(tejun, "launch") as launch, \
                 patch("sys.argv", ["tejun", "run"]):
                with self.assertRaisesRegex(tejun.TejunError, "paths.content_production"):
                    tejun.main()
                session.assert_not_called()
                launch.assert_not_called()

    def test_empty_unreadable_and_missing_resources_are_preflight_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            agent = root / "agent"
            agent.mkdir()
            contract = agent / "AGENTS.md"
            contract.write_text("Fixture instructions\n")
            source = root / "input.md"
            definition = {**tejun.definitions()["verify"], "skills": []}
            config = {"paths": {"verification": str(root)}, "pi": {
                "agent_dir": str(agent), "extensions": [], "provider": "fixture", "model": "exact",
                "thinking": "off"}}
            with patch.object(tejun, "herdr") as herdr:
                source.write_text("\n \n")
                with self.assertRaisesRegex(tejun.TejunError, "empty"):
                    tejun.prepare(definition, config)
                source.write_bytes(b"\xff")
                with self.assertRaisesRegex(tejun.TejunError, "Cannot read workflow input"):
                    tejun.prepare(definition, config)
                source.write_text("Input\n")
                contract.unlink()
                with self.assertRaisesRegex(tejun.TejunError, "Missing Pi/Kijun resource"):
                    tejun.prepare(definition, config)
                herdr.assert_not_called()

    @unittest.skipUnless(hasattr(signal, "SIGTERM"), "requires POSIX signals")
    def test_real_worker_sigterm_persists_incomplete_status(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture = RunFixture(root)
            ready = root / "ready"
            fake = root / "herdr"
            fake.write_text(f"#!{sys.executable}\nimport pathlib,time\n"
                            f"pathlib.Path({str(ready)!r}).write_text('ready')\ntime.sleep(30)\n")
            fake.chmod(0o700)
            fixture.request["herdr"] = str(fake)
            fixture.save()
            env = {**os.environ, "HERDR_ENV": "1", "PYTHONDONTWRITEBYTECODE": "1"}
            # Exercise the actual detached-handoff signal mask inherited by workers.
            with tejun.defer_interrupts():
                process = subprocess.Popen([sys.executable, str(ROOT / "tejun.py"), "_work", str(root)],
                                           env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                deadline = time.monotonic() + 5
                while not ready.exists():
                    if process.poll() is not None or time.monotonic() > deadline:
                        self.fail("worker did not reach the fake Herdr command")
                    time.sleep(0.01)
                process.terminate()
                stdout, stderr = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 143, (stdout, stderr))
                final = fixture.final()
                self.assertEqual(final["state"], "incomplete")
                self.assertIn("SIGTERM", final["reason"])
                self.assertTrue(fixture.partial.exists())
                self.assertFalse(fixture.output.exists())
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()
