"""Run the installed CLI and detached worker outside the repo with fake Herdr.

The fake never starts Pi, contacts a provider, or touches a real Herdr session.
"""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from test_tejun import ROOT


FAKE_HERDR = r'''
import json, os, pathlib, sys, time, uuid
root = pathlib.Path(os.environ["FAKE_HERDR_DIR"])
args = sys.argv[1:]
assert args[:2] == ["--session", "tejun"], args
args = args[2:]
command = args[:2]
result = {}
if command == ["workspace", "list"]:
    result = {"workspaces": [{"workspace_id": "w1"}]}
elif command == ["tab", "create"]:
    suffix = uuid.uuid4().hex[:8]
    result = {"root_pane": {"pane_id": "w1:p" + suffix}, "tab": {"tab_id": "w1:t" + suffix}}
elif command == ["agent", "start"]:
    assert "--no-session" in args
    name = args[2]
    pane = args[args.index("--pane") + 1]
    (root / (name + ".json")).write_text(json.dumps({"pane": pane, "active": True}))
elif command == ["agent", "prompt"]:
    import re
    name, prompt = args[2:4]
    paths = [json.loads(value) for value in re.findall(r'"(?:[^"\\]|\\.)*"', prompt)]
    output = pathlib.Path(next(value for value in paths if value.endswith('.partial.md')))
    (root / "prompt-ready").write_text("ready")
    deadline = time.monotonic() + 10
    while not (root / "finish").exists():
        if time.monotonic() >= deadline: raise SystemExit("fixture gate timed out")
        time.sleep(0.01)
    results = json.loads((root / 'results.json').read_text())
    workflow = next(name for name in results if output.name.startswith(name + '-'))
    output.write_bytes(results[workflow].encode('utf-8'))
elif command == ["agent", "get"]:
    result = {"agent": {"agent_status": "done"}}
elif command == ["agent", "send-keys"]:
    assert args[3] == "ctrl+d"
    path = root / (args[2] + ".json")
    record = json.loads(path.read_text())
    record["active"] = False
    path.write_text(json.dumps(record))
elif command == ["pane", "list"]:
    panes = []
    for path in root.glob("tejun-*.json"):
        record = json.loads(path.read_text())
        pane = {"pane_id": record["pane"], "tab_id": record["pane"].replace(":p", ":t")}
        if record["active"]: pane["agent"] = "pi"
        panes.append(pane)
    result = {"panes": panes}
elif command == ["tab", "close"]:
    (root / "tab-closed").write_text(args[2])
else:
    raise SystemExit("Unexpected fake Herdr request: " + repr(args))
print(json.dumps({"result": result}))
'''


class CliIntegrationTests(unittest.TestCase):
    @contextmanager
    def installed(self, checkout=ROOT):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bin_dir, agent, outside, fake = [root / name for name in ("bin", "agent", "outside", "fake")]
            for directory in (bin_dir, agent, outside, fake):
                directory.mkdir()
            (agent / "AGENTS.md").write_text("Fixture instructions\n")
            skill = agent / "skills/unslop/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("Fixture skill; no live Pi process loads this file.\n")
            # Keep personal commands out of PATH, including an installed Tejun
            # from another checkout when this suite tests a staged snapshot.
            (bin_dir / "python3").symlink_to(sys.executable)
            for name, body in (("herdr", FAKE_HERDR), ("pi", "raise SystemExit('Pi must not be invoked')\n")):
                binary = bin_dir / name
                binary.write_text(f"#!{sys.executable}\n" + body)
                binary.chmod(0o700)
            config = root / "config.toml"
            destination = root / "destination"
            destination.mkdir()
            verification = root / "verification"
            verification.mkdir()
            (verification / "input.md").write_text("Different input: zażółć.\n\n", encoding="utf-8")
            results = {
                "content-smoke-test": "# Content production smoke test\n\n"
                                      "Pi Tejun wrote this file through the shared workflow launcher.\n",
                "verify": "# Tejun verification\n\nDifferent input: zażółć.\n",
            }
            (fake / "results.json").write_text(json.dumps(results))
            config.write_text(
                'enabled = []\n[pi]\nprovider = "fixture"\nmodel = "exact"\nthinking = "off"\n'
                'extensions = []\ntimeout_seconds = 10\nagent_dir = ' + json.dumps(str(agent)) +
                '\n[paths]\ncontent_production = ' + json.dumps(str(destination)) +
                '\nverification = ' + json.dumps(str(verification)) + '\n')
            env = {**os.environ, "TEJUN_CONFIG": str(config), "TEJUN_STATE_DIR": str(root / "state"),
                   "HERDR_ENV": "1", "FAKE_HERDR_DIR": str(fake), "PYTHONDONTWRITEBYTECODE": "1",
                   "PATH": str(bin_dir)}
            setup = subprocess.run([sys.executable, str(checkout / "install.py"), "--bin-dir", str(bin_dir)],
                                   cwd=outside, env=env, capture_output=True, text=True, timeout=5)
            self.assertEqual(setup.returncode, 0, setup.stderr)
            fixture = {"root": root, "fake": fake, "config": config, "env": env,
                       "outside": outside, "command": str(bin_dir / "tejun"),
                       "results": results, "destinations": {
                           "content-smoke-test": destination, "verify": verification / "reports"}}
            try:
                yield fixture
            finally:
                (fake / "finish").write_text("finish")
                # Let detached workers finish before removing their temporary files.
                deadline = time.monotonic() + 12
                for record in (root / "state/runs").glob("*/status.json"):
                    while True:
                        status = json.loads(record.read_text())
                        if "finished_at" in status:
                            break
                        if time.monotonic() > deadline:
                            if status.get("worker_pid"):
                                try:
                                    os.kill(status["worker_pid"], signal.SIGTERM)
                                except ProcessLookupError:
                                    pass
                            self.fail(f"fixture worker did not finish: {status}")
                        time.sleep(0.01)

    def cli(self, fixture, *args):
        return subprocess.run([fixture["command"], *args], cwd=fixture["outside"],
                              env=fixture["env"], capture_output=True, text=True, timeout=5)

    def complete(self, fixture, record):
        (fixture["fake"] / "finish").write_text("finish")
        deadline = time.monotonic() + 5
        while True:
            status = json.loads(record.read_text())
            if "finished_at" in status:
                break
            if time.monotonic() > deadline:
                self.fail(f"detached worker did not finish: {status}")
            time.sleep(0.01)
        self.assertEqual(status["state"], "success", status)
        self.assertTrue(status["agent_exited"])
        self.assertTrue(status["tab_closed"])
        self.assertFalse(Path(status["partial"]).exists())
        self.assertEqual(Path(status["output"]).parent,
                         fixture["destinations"][status["workflow"]])
        self.assertEqual(Path(status["output"]).read_bytes(),
                         fixture["results"][status["workflow"]].encode("utf-8"))
        return status

    def test_both_workflows_share_installed_discovery_execution_and_repeat_policy(self):
        with self.installed() as fixture:
            listed = self.cli(fixture, "list")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            for name, destination in fixture["destinations"].items():
                self.assertIn(f"{name}\tdisabled", listed.stdout)
                self.assertIn(f"Output: {destination}", listed.stdout)
            self.assertFalse((fixture["root"] / "state/runs").exists())
            previous = set()
            statuses = []
            # Named runs work even when disabled; repeat both without reinstalling.
            for name in ("verify", "content-smoke-test", "verify", "content-smoke-test"):
                (fixture["fake"] / "finish").unlink(missing_ok=True)
                launched = self.cli(fixture, "run", name)
                self.assertEqual(launched.returncode, 0, launched.stderr)
                self.assertIn("completion is pending", launched.stdout)
                records = set((fixture["root"] / "state/runs").glob("*/status.json"))
                self.assertEqual(len(records - previous), 1)
                record = (records - previous).pop()
                pending = json.loads(record.read_text())
                self.assertIn(pending["state"], {"started", "working"})
                self.assertFalse(Path(pending["output"]).exists())
                self.assertTrue(Path(pending["partial"]).exists())
                status = self.complete(fixture, record)
                self.assertEqual(status["workflow"], name)
                request = json.loads((record.parent / "request.json").read_text())
                self.assertIn("--no-session", request["pi_args"])
                self.assertIn("--no-extensions", request["pi_args"])
                if name == "verify":
                    self.assertIn(json.dumps(request["input"]), request["prompt"])
                    self.assertIn("--skill", request["pi_args"])
                else:
                    self.assertIsNone(request["input"])
                statuses.append(status)
                previous = records
            for key in ("run", "output", "agent", "pane"):
                self.assertEqual(len({status[key] for status in statuses}), 4)
            for status in statuses:
                self.assertEqual(Path(status["output"]).read_bytes(),
                                 fixture["results"][status["workflow"]].encode("utf-8"))

    def test_both_workflows_reject_missing_configuration_before_launch(self):
        for name, key in (("verify", "verification"),
                          ("content-smoke-test", "content_production")):
            with self.subTest(workflow=name), self.installed() as fixture:
                original = fixture["config"].read_text()
                fixture["config"].write_text("\n".join(
                    line for line in original.splitlines() if not line.startswith(key + " =")))
                rejected = self.cli(fixture, "run", name)
                self.assertNotEqual(rejected.returncode, 0)
                self.assertIn(key, rejected.stderr)
                self.assertNotIn("Launched", rejected.stdout)
                self.assertFalse((fixture["root"] / "state/runs").exists())
                self.assertEqual(list(fixture["fake"].glob("tejun-*.json")), [])

    def test_enabled_workflows_launch_together_through_bare_run(self):
        with self.installed() as fixture:
            fixture["config"].write_text(fixture["config"].read_text().replace(
                'enabled = []', 'enabled = ["verify", "content-smoke-test"]'))
            launched = self.cli(fixture, "run")
            self.assertEqual(launched.returncode, 0, launched.stderr)
            self.assertEqual(launched.stdout.count("completion is pending"), 2)
            records = list((fixture["root"] / "state/runs").glob("*/status.json"))
            self.assertEqual(len(records), 2)
            statuses = [self.complete(fixture, record) for record in records]
            self.assertEqual({status["workflow"] for status in statuses},
                             {"verify", "content-smoke-test"})

    def test_both_workflows_retain_incorrect_results_as_incomplete(self):
        for name in ("verify", "content-smoke-test"):
            with self.subTest(workflow=name), self.installed() as fixture:
                (fixture["fake"] / "results.json").write_text(json.dumps({name: "Wrong result.\n"}))
                launched = self.cli(fixture, "run", name)
                self.assertEqual(launched.returncode, 0, launched.stderr)
                records = list((fixture["root"] / "state/runs").glob("*/status.json"))
                self.assertEqual(len(records), 1)
                (fixture["fake"] / "finish").write_text("finish")
                deadline = time.monotonic() + 5
                while True:
                    status = json.loads(records[0].read_text())
                    log = (records[0].parent / "worker.log").read_text()
                    if "finished_at" in status and "Incomplete:" in log:
                        break
                    if time.monotonic() > deadline:
                        self.fail(f"detached worker did not reject incorrect output: {status}")
                    time.sleep(0.01)
                self.assertEqual(status["state"], "incomplete")
                self.assertIn("Expected Markdown was not produced", status["reason"])
                self.assertEqual(Path(status["partial"]).read_text(), "Wrong result.\n")
                self.assertFalse(Path(status["output"]).exists())
                self.assertNotIn("agent_exited", status)
                self.assertNotIn("tab_closed", status)
                agent = json.loads((fixture["fake"] / (status["agent"] + ".json")).read_text())
                self.assertTrue(agent["active"])
                self.assertFalse((fixture["fake"] / "tab-closed").exists())

    def test_definition_added_after_install_needs_no_launcher_or_installer_change(self):
        with tempfile.TemporaryDirectory() as temp:
            checkout = Path(temp) / "checkout"
            checkout.mkdir()
            for name in ("tejun.py", "install.py", "config.example.toml"):
                shutil.copy2(ROOT / name, checkout / name)
            for name in ("workflows", "extensions"):
                shutil.copytree(ROOT / name, checkout / name)
            with self.installed(checkout) as fixture:
                initial = self.cli(fixture, "list")
                self.assertEqual(initial.returncode, 0, initial.stderr)
                self.assertNotIn("author-check", initial.stdout)
                self.assertEqual(Path(fixture["command"]).resolve(), checkout / "tejun.py")
                before = {name: (checkout / name).read_bytes()
                          for name in ("tejun.py", "install.py", "config.example.toml")}
                # Execute the guide's complete definition, not a parallel test-only example.
                guide = (ROOT / "docs/workflow-authoring.md").read_text()
                definition = re.search(r"```toml\n(.*?)\n```", guide, re.DOTALL)
                self.assertIsNotNone(definition)
                (checkout / "workflows/author-check.toml").write_text(definition.group(1) + "\n")
                fixture["config"].write_text(fixture["config"].read_text() +
                    '\nauthoring = ' + json.dumps(str(fixture["root"] / "destination")) + '\n')
                fixture["results"]["author-check"] = (
                    "# Author check\n\nThis workflow uses the existing Tejun command.\n")
                fixture["destinations"]["author-check"] = fixture["root"] / "destination/reports"
                (fixture["fake"] / "results.json").write_text(json.dumps(fixture["results"]))
                listed = self.cli(fixture, "list")
                self.assertEqual(listed.returncode, 0, listed.stderr)
                self.assertIn("author-check\tdisabled", listed.stdout)
                launched = self.cli(fixture, "run", "author-check")
                self.assertEqual(launched.returncode, 0, launched.stderr)
                records = list((fixture["root"] / "state/runs").glob("*/status.json"))
                self.assertEqual(len(records), 1)
                self.assertEqual(self.complete(fixture, records[0])["workflow"], "author-check")
                for name, content in before.items():
                    self.assertEqual((checkout / name).read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
