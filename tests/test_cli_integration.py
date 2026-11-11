"""Installed command and detached worker, using disposable fake Herdr only."""

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

from support import ROOT


class CliIntegrationTests(unittest.TestCase):
    @contextmanager
    def installed(self, checkout=ROOT):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("bin", "agent", "outside", "fake", "reports", "digest",
                         "client_projects", "personal_projects", "personal_repositories"):
                (root / name).mkdir()
            agent = root / "agent"
            (agent / "AGENTS.md").write_text("Fixture instructions\n")
            skill = agent / "skills/unslop/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("Fixture skill\n")
            search = agent / "search.ts"
            search.write_text("Fixture search extension; Pi is never started.\n")
            (root / "digest/watchlist.md").write_text("# Watchlist\n")
            project = root / "client_projects/acme/docs/project/work"
            project.mkdir(parents=True)
            (project / "B001-example.md").write_text("---\nid: B001\nstatus: To do\n---\n")
            (project.parent / "work.md").write_text("Fixture work index\n")
            report = ("# Project review - Saturday, November 7, 2026\n\n## Client projects\n\n"
                      "### Blocked or awaiting input\n\n#### " + str(root / "client_projects/acme") +
                      "\n\nlast modified: 2026-11-01\n\n- B001 needs a decision.\n"
                      "- Resolve the recorded question.\n\n## Personal projects\n\nNo personal projects found.\n")
            results = {"project-review": report}
            (root / "fake/results.json").write_text(json.dumps(results))
            config = root / "config.toml"
            paths = {key: str(root / value) for key, value in (
                ("digest_briefs", "digest"), ("project_directions", "reports"),
                ("client_projects", "client_projects"), ("personal_projects", "personal_projects"),
                ("personal_repositories", "personal_repositories"), ("content_production", "excluded"))}
            config.write_text('enabled = []\n[pi]\nprovider = "fixture"\nmodel = "exact"\n'
                'thinking = "off"\nextensions = []\ntimeout_seconds = 10\nagent_dir = ' + json.dumps(str(agent)) +
                '\nsearch_extension = ' + json.dumps(str(search)) + '\n[paths]\n' +
                '\n'.join(key + ' = ' + json.dumps(value) for key, value in paths.items()) + '\n')
            (root / "bin/python3").symlink_to(sys.executable)
            for name, body in (("herdr", (ROOT / "tests/fake_herdr.py").read_text()),
                               ("pi", "raise SystemExit('Pi must never be invoked')\n")):
                binary = root / "bin" / name
                binary.write_text(f"#!{sys.executable}\n" + body)
                binary.chmod(0o700)
            env = {**os.environ, "TEJUN_CONFIG": str(config), "TEJUN_STATE_DIR": str(root / "state"),
                   "HERDR_ENV": "1", "FAKE_HERDR_DIR": str(root / "fake"),
                   "PYTHONDONTWRITEBYTECODE": "1", "PATH": str(root / "bin")}
            setup = subprocess.run([sys.executable, str(checkout / "install.py"), "--bin-dir", str(root / "bin")],
                                   cwd=root / "outside", env=env, capture_output=True, text=True, timeout=5)
            self.assertEqual(setup.returncode, 0, setup.stderr)
            fixture = dict(root=root, config=config, env=env, results=results, command=str(root / "bin/tejun"))
            try:
                yield fixture
            finally:
                (root / "fake/finish").write_text("finish")
                for record in self.records(fixture):
                    try:
                        self.finished(record, timeout=12)
                    except AssertionError:
                        status = json.loads(record.read_text())
                        if status.get("worker_pid"):
                            try:
                                os.kill(status["worker_pid"], signal.SIGTERM)
                            except ProcessLookupError:
                                pass
                        raise

    def cli(self, fixture, *args):
        return subprocess.run([fixture["command"], *args], cwd=fixture["root"] / "outside",
                              env=fixture["env"], capture_output=True, text=True, timeout=5)

    def records(self, fixture):
        return set((fixture["root"] / "state/runs").glob("*/status.json"))

    def launch(self, fixture, name):
        before = self.records(fixture)
        result = self.cli(fixture, "run", name)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("completion is pending", result.stdout)
        fresh = self.records(fixture) - before
        self.assertEqual(len(fresh), 1)
        return fresh.pop()

    def finished(self, record, timeout=5):
        deadline = time.monotonic() + timeout
        while True:
            status = json.loads(record.read_text())
            if "finished_at" in status:
                return status
            if time.monotonic() > deadline:
                self.fail(f"worker did not finish: {status}")
            time.sleep(.01)

    def complete(self, fixture, record):
        (fixture["root"] / "fake/finish").write_text("finish")
        status = self.finished(record)
        self.assertEqual(status["state"], "success", status)
        self.assertTrue(status["agent_exited"])
        self.assertTrue(status["tab_closed"])
        self.assertFalse(Path(status["partial"]).exists())
        self.assertTrue(Path(status["output"]).is_file())
        self.assertNotIn("history_output", status)
        if status["workflow"] != "digest":
            self.assertEqual(Path(status["output"]).read_text(), fixture["results"][status["workflow"]])
        return status

    def test_both_workflows_discovery_bare_run_overlap_and_repetition(self):
        with self.installed() as f:
            listed = self.cli(f, "list")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            for name in ("digest", "project-review"):
                self.assertIn(name + "\tdisabled", listed.stdout)
            self.assertNotIn("verify\t", listed.stdout)
            before_docs = {p: (p.read_bytes(), p.stat().st_mtime_ns)
                           for p in (f["root"] / "client_projects").rglob("*.md")}
            f["config"].write_text(f["config"].read_text().replace(
                "enabled = []", 'enabled = ["digest", "project-review"]'))
            result = self.cli(f, "run")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.count("completion is pending"), 2)
            records = self.records(f)
            layouts = [json.loads(p.read_text()) for p in (f["root"] / "fake").glob("workspace-*.json")]
            self.assertEqual({item["workspace"]["label"] for item in layouts}, {"digest", "project-review"})
            self.assertEqual(len({item["workspace"]["workspace_id"] for item in layouts}), 2)
            self.assertTrue(all(item["tab"]["label"] == "1" for item in layouts))
            rejected = self.cli(f, "run", "digest")
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("still has tabs", rejected.stderr)
            completed = [self.complete(f, record) for record in records]
            snapshots = {Path(s["output"]): Path(s["output"]).read_bytes() for s in completed}
            self.assertFalse(list((f["root"] / "fake").glob("workspace-*.json")))
            for name in ("digest", "project-review"):
                (f["root"] / "fake/finish").unlink(missing_ok=True)
                record = self.launch(f, name)
                request = json.loads((record.parent / "request.json").read_text())
                self.assertIn("--no-session", request["pi_args"])
                self.assertIn("--no-extensions", request["pi_args"])
                if name == "digest":
                    recent = request["digest_context"]["recent_reports"]
                    self.assertEqual(len(recent), 1)
                    self.assertEqual(request["digest_context"]["start"], recent[0]["started_at"])
                    self.assertFalse((f["root"] / "digest/history").exists())
                    self.assertIn("web_search", request["pi_args"][request["pi_args"].index("--tools") + 1])
                self.complete(f, record)
            self.assertEqual(snapshots, {p: p.read_bytes() for p in snapshots})
            self.assertEqual(before_docs, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before_docs})

    def test_preflight_rejects_missing_configuration_before_any_enabled_launch(self):
        for name, key in (("digest", "digest_briefs"), ("project-review", "project_directions")):
            with self.subTest(workflow=name), self.installed() as f:
                f["config"].write_text('\n'.join(line for line in f["config"].read_text().splitlines()
                                                if not line.startswith(key + " =")))
                result = self.cli(f, "run", name)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(key, result.stderr)
                # Bare run must not start the first workflow before validating the second.
                f["config"].write_text(f["config"].read_text().replace(
                    "enabled = []", 'enabled = ["digest", "project-review"]'))
                self.assertNotEqual(self.cli(f, "run").returncode, 0)
                self.assertFalse(self.records(f))
                self.assertFalse(list((f["root"] / "fake").glob("tejun-*.json")))

    def test_invalid_generated_results_retain_agent_then_retry_after_cleanup(self):
        for name in ("digest", "project-review"):
            with self.subTest(workflow=name), self.installed() as f:
                (f["root"] / "fake/results.json").write_text(json.dumps({name: "\n"}))
                record = self.launch(f, name)
                (f["root"] / "fake/finish").write_text("finish")
                status = self.finished(record)
                self.assertEqual(status["state"], "incomplete")
                self.assertFalse(Path(status["output"]).exists())
                self.assertEqual(Path(status["partial"]).read_text(), "\n")
                self.assertNotIn("agent_exited", status)
                agent = json.loads((f["root"] / "fake" / (status["agent"] + ".json")).read_text())
                self.assertTrue(agent["active"])
                self.assertIn("still has tabs", self.cli(f, "run", name).stderr)
                # Simulate operator inspection and tab closure before retrying.
                closed = subprocess.run([str(f["root"] / "bin/herdr"), "--session", "tejun", "tab", "close",
                                         status["tab"]], env=f["env"], capture_output=True, timeout=5)
                self.assertEqual(closed.returncode, 0, closed.stderr)
                (f["root"] / "fake/results.json").write_text(json.dumps(f["results"]))
                self.complete(f, self.launch(f, name))
                self.assertEqual(Path(status["partial"]).read_text(), "\n")

    def test_definition_added_after_install_runs_without_launcher_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            checkout = Path(temp) / "checkout"
            checkout.mkdir()
            for name in ("tejun.py", "digest.py", "content_research.py", "install.py", "config.example.toml"):
                shutil.copy2(ROOT / name, checkout / name)
            for name in ("workflows", "extensions"):
                shutil.copytree(ROOT / name, checkout / name)
            with self.installed(checkout) as f:
                self.assertNotIn("author-check", self.cli(f, "list").stdout)
                snapshots = {name: (checkout / name).read_bytes() for name in ("tejun.py", "install.py", "config.example.toml")}
                guide = (ROOT / "docs/workflow-authoring.md").read_text()
                definition = re.search(r"```toml\n(.*?)\n```", guide, re.DOTALL)
                self.assertIsNotNone(definition)
                (checkout / "workflows/author-check.toml").write_text(definition.group(1) + "\n")
                f["config"].write_text(f["config"].read_text() + '\nauthoring = ' + json.dumps(str(f["root"])) + '\n')
                f["results"]["author-check"] = "# Author check\n\nThis workflow uses the existing Tejun command.\n"
                (f["root"] / "fake/results.json").write_text(json.dumps(f["results"]))
                self.assertIn("author-check\tdisabled", self.cli(f, "list").stdout)
                self.complete(f, self.launch(f, "author-check"))
                self.assertEqual(snapshots, {name: (checkout / name).read_bytes() for name in snapshots})


if __name__ == "__main__":
    unittest.main()
