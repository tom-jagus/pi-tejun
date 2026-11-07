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
    result = {"workspaces": [json.loads(path.read_text())["workspace"]
                             for path in root.glob("workspace-*.json")]}
elif command in (["workspace", "create"], ["tab", "create"]):
    assert "--no-focus" in args
    assert "--env" in args
    suffix = uuid.uuid4().hex[:8]
    if command[0] == "workspace":
        workspace = {"workspace_id": "w" + suffix, "label": args[args.index("--label") + 1]}
        assert not workspace["label"].startswith("tejun-")
    else:
        assert "--label" not in args
        workspace_id = args[args.index("--workspace") + 1]
        workspace = json.loads((root / ("workspace-" + workspace_id + ".json")).read_text())["workspace"]
    wid = workspace["workspace_id"]
    result = {"workspace": workspace, "root_pane": {"pane_id": wid + ":p" + suffix},
              "tab": {"tab_id": wid + ":t" + suffix, "workspace_id": wid, "label": "1"}}
    (root / ("workspace-" + wid + ".json")).write_text(json.dumps(result))
elif command == ["tab", "list"]:
    workspace_id = args[args.index("--workspace") + 1]
    path = root / ("workspace-" + workspace_id + ".json")
    result = {"tabs": [json.loads(path.read_text())["tab"]] if path.exists() else []}
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
    for path in root.glob("workspace-*.json"):
        if json.loads(path.read_text())["tab"]["tab_id"] == args[2]:
            path.unlink()  # Herdr removes the workspace when its last tab closes.
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

    def test_same_workflow_rejects_overlap_then_recreates_workspace_after_success(self):
        with self.installed() as fixture:
            launched = self.cli(fixture, "run", "content-smoke-test")
            self.assertEqual(launched.returncode, 0, launched.stderr)
            records = set((fixture["root"] / "state/runs").glob("*/status.json"))
            self.assertEqual(len(records), 1)
            original = next(iter(records))
            status = json.loads(original.read_text())
            workspace = fixture["fake"] / ("workspace-" + status["workspace_id"] + ".json")
            layout = json.loads(workspace.read_text())
            self.assertEqual(layout["workspace"]["label"], "content-smoke-test")
            self.assertEqual(layout["tab"]["label"], "1")
            rejected = self.cli(fixture, "run", "content-smoke-test")
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("still has tabs", rejected.stderr)
            self.assertEqual(len(list(fixture["fake"].glob("workspace-*.json"))), 1)
            self.assertTrue(json.loads((fixture["fake"] / (status["agent"] + ".json")).read_text())["active"])
            self.complete(fixture, original)
            self.assertFalse(workspace.exists())
            previous = set((fixture["root"] / "state/runs").glob("*/status.json"))
            (fixture["fake"] / "finish").unlink()
            repeated = self.cli(fixture, "run", "content-smoke-test")
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            fresh = set((fixture["root"] / "state/runs").glob("*/status.json")) - previous
            self.assertEqual(len(fresh), 1)
            completed = self.complete(fixture, fresh.pop())
            self.assertNotEqual(status["workspace_id"], completed["workspace_id"])
            self.assertEqual(list(fixture["fake"].glob("workspace-*.json")), [])

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
            layouts = [json.loads(path.read_text()) for path in fixture["fake"].glob("workspace-*.json")]
            self.assertEqual({item["workspace"]["label"] for item in layouts},
                             {"verify", "content-smoke-test"})
            self.assertEqual(len({item["workspace"]["workspace_id"] for item in layouts}), 2)
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

    def configure_review(self, fixture):
        roots = {key: fixture["root"] / key for key in (
            "client_projects", "personal_projects", "personal_repositories")}
        for path in roots.values():
            path.mkdir()
        projects = [roots["client_projects"] / "acme", roots["personal_projects"] / "alpha",
                    roots["personal_repositories"] / "tools"]
        for project in projects:
            records = project / "docs/project/work"
            records.mkdir(parents=True)
            (records.parent / "work.md").write_text("Fixture work index.\n")
            (records / "B001-example.md").write_text("---\nid: B001\nstatus: To do\n---\n")
        fixture["config"].write_text(fixture["config"].read_text() +
            '\nproject_directions = ' + json.dumps(str(fixture["root"] / "destination")) + '\n' +
            '\n'.join(key + ' = ' + json.dumps(str(path)) for key, path in roots.items()) + '\n')
        client, personal, repository = projects
        report = ("# Project review - Saturday November 7, 2026\n\n"
                  f"## Client projects\n\n### Blocked or awaiting input\n\n#### {client}\n\n"
                  "last modified: 2026-11-01\n\n- B001 needs a decision.\n- Resolve the recorded question.\n\n"
                  f"## Personal projects\n\n### Blocked or awaiting input\n\n#### {personal}\n\n"
                  "last modified: 2026-10-01\n\n- B001 awaits review.\n- Review the documented result.\n\n"
                  f"### Quick wins\n\n#### {repository}\n\nlast modified: 2026-09-01\n\n"
                  "- B001 has a bounded documentation action.\n- Draft the small guide in one focused session.\n\n"
                  "## Summary\n\nResolve the client decision, then review alpha.\n")
        fixture["results"]["project-review"] = report
        fixture["destinations"]["project-review"] = fixture["root"] / "destination"
        (fixture["fake"] / "results.json").write_text(json.dumps(fixture["results"]))
        return roots

    def test_generated_review_uses_installed_command_and_preserves_repeated_results(self):
        with self.installed() as fixture:
            roots = self.configure_review(fixture)
            before = {path: (path.read_bytes(), path.stat().st_mtime_ns)
                      for root in roots.values() for path in root.rglob("*.md")}
            listed = self.cli(fixture, "list")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertIn("project-review\tdisabled", listed.stdout)
            previous = set()
            completed = []
            for number in range(2):
                (fixture["fake"] / "finish").unlink(missing_ok=True)
                launched = self.cli(fixture, "run", "project-review")
                self.assertEqual(launched.returncode, 0, launched.stderr)
                self.assertIn("completion is pending", launched.stdout)
                records = set((fixture["root"] / "state/runs").glob("*/status.json"))
                self.assertEqual(len(records - previous), 1)
                record = (records - previous).pop()
                request = json.loads((record.parent / "request.json").read_text())
                self.assertEqual(request["result_check"], "project-review")
                self.assertIsNone(request["expected"])
                self.assertEqual(request["context_paths"], {key: str(path) for key, path in roots.items()})
                for path in roots.values():
                    self.assertIn(json.dumps(str(path)), request["prompt"])
                self.assertIn("read,write,bash", request["pi_args"])
                self.assertIn("Do not inspect source", request["prompt"])
                self.assertIn("Do not create a decisions file", request["prompt"])
                status = self.complete(fixture, record)
                completed.append((status, Path(status["output"]).read_bytes()))
                previous = records
                if number == 0:
                    fixture["results"]["project-review"] = fixture["results"]["project-review"].replace(
                        "Resolve the client decision, then review alpha.",
                        "Review the client question, then consider the documentation task.")
                    (fixture["fake"] / "results.json").write_text(json.dumps(fixture["results"]))
            self.assertNotEqual(completed[0][0]["run"], completed[1][0]["run"])
            self.assertNotEqual(completed[0][1], completed[1][1])
            for status, content in completed:
                self.assertEqual(Path(status["output"]).read_bytes(), content)
            self.assertEqual(before, {path: (path.read_bytes(), path.stat().st_mtime_ns)
                                      for root in roots.values() for path in root.rglob("*.md")})

    def test_generated_review_missing_root_rejects_before_startup(self):
        with self.installed() as fixture:
            roots = self.configure_review(fixture)
            fixture["config"].write_text(fixture["config"].read_text().replace(
                json.dumps(str(roots["client_projects"])),
                json.dumps(str(fixture["root"] / "missing-clients"))))
            rejected = self.cli(fixture, "run", "project-review")
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("Missing project-review root", rejected.stderr)
            self.assertNotIn("Launched", rejected.stdout)
            self.assertFalse((fixture["root"] / "state/runs").exists())
            self.assertFalse(list(fixture["fake"].glob("tejun-*.json")))

    def test_generated_review_invalid_result_remains_incomplete(self):
        with self.installed() as fixture:
            self.configure_review(fixture)
            invalid = fixture["results"]["project-review"].replace("### Quick wins", "## Quick wins")
            (fixture["fake"] / "results.json").write_text(json.dumps({"project-review": invalid}))
            launched = self.cli(fixture, "run", "project-review")
            self.assertEqual(launched.returncode, 0, launched.stderr)
            records = list((fixture["root"] / "state/runs").glob("*/status.json"))
            self.assertEqual(len(records), 1)
            (fixture["fake"] / "finish").write_text("finish")
            deadline = time.monotonic() + 5
            while True:
                status = json.loads(records[0].read_text())
                if "finished_at" in status:
                    break
                if time.monotonic() > deadline:
                    self.fail(f"review worker did not finish: {status}")
                time.sleep(0.01)
            self.assertEqual(status["state"], "incomplete")
            self.assertIn("Invalid project review", status["reason"])
            self.assertFalse(Path(status["output"]).exists())
            self.assertEqual(Path(status["partial"]).read_text(), invalid)
            self.assertNotIn("agent_exited", status)
            self.assertNotIn("tab_closed", status)
            agent = json.loads((fixture["fake"] / (status["agent"] + ".json")).read_text())
            self.assertTrue(agent["active"])
            self.assertFalse((fixture["fake"] / "tab-closed").exists())
            workspace = fixture["fake"] / ("workspace-" + status["workspace_id"] + ".json")
            self.assertTrue(workspace.exists())
            rejected = self.cli(fixture, "run", "project-review")
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("still has tabs", rejected.stderr)
            # Simulate the user closing the retained tab after inspection.
            closed = subprocess.run([str(fixture["root"] / "bin/herdr"), "--session", "tejun",
                                     "tab", "close", status["tab"]], env=fixture["env"],
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(closed.returncode, 0, closed.stderr)
            self.assertFalse(workspace.exists())
            (fixture["fake"] / "results.json").write_text(json.dumps(fixture["results"]))
            previous = set((fixture["root"] / "state/runs").glob("*/status.json"))
            retried = self.cli(fixture, "run", "project-review")
            self.assertEqual(retried.returncode, 0, retried.stderr)
            fresh = set((fixture["root"] / "state/runs").glob("*/status.json")) - previous
            self.assertEqual(len(fresh), 1)
            self.complete(fixture, fresh.pop())
            self.assertEqual(Path(status["partial"]).read_text(), invalid)

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
