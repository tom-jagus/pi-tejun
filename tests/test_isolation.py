"""S004 checks for explicit context, no-clobber publication, and shared files."""

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
from test_outcomes import RunFixture


def prepared(root, **changes):
    return {"workspace": str(root), "input": None, "output_dir": str(root / "reports"),
            "agent_dir": str(root / "agent"), "path": "/fixture/bin", "herdr": "fixture",
            "provider": "fixture", "model": "exact", "pi_args": ["--no-session"],
            "expected": "# Expected\n\nBody\n", "timeout": 1,
            "history_inputs": [], "exclusive_paths": [], **changes}


def workflow():
    return {"name": "fixture", "heading": "# Expected", "result_text": "Body",
            "prompt": "Write {output_path} with {heading} followed by {result_text}."}


class IsolationTests(unittest.TestCase):
    def test_publication_refuses_existing_regular_file_and_symlink(self):
        for symlink in (False, True):
            with self.subTest(symlink=symlink), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                fixture = RunFixture(root)
                old = root / "older.md"
                old.write_text("Earlier result\n")
                if symlink:
                    fixture.output.symlink_to(old)
                else:
                    fixture.output.write_text("Earlier result\n")
                self.assertEqual(fixture.work(), 1)
                self.assertIn("Refusing to replace", fixture.final()["reason"])
                self.assertEqual(fixture.output.read_text(), "Earlier result\n")
                self.assertEqual(old.read_text(), "Earlier result\n")
                self.assertTrue(fixture.partial.exists())

    def test_overlapping_unique_output_runs_have_fresh_panes_and_preserve_results(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            reports = root / "reports"
            reports.mkdir()
            old = reports / "earlier.md"
            old.write_text("Keep this\n")
            tabs = []
            def herdr(binary, *args, **kwargs):
                if args[:2] == ("tab", "create"):
                    n = len(tabs) + 1
                    tabs.append(n)
                    return {"root_pane": {"pane_id": f"w1:p{n}"}, "tab": {"tab_id": f"w1:t{n}"}}
                return {}
            with patch.object(tejun, "STATE", root / "state"), \
                 patch.object(tejun, "ensure_session", return_value="w1"), \
                 patch.object(tejun, "herdr", side_effect=herdr) as calls, \
                 patch.object(tejun.subprocess, "Popen"), redirect_stdout(io.StringIO()):
                tejun.launch(workflow(), prepared(root))
                tejun.launch(workflow(), prepared(root))
            runs = sorted((root / "state/runs").iterdir())
            statuses = [json.loads((run / "status.json").read_text()) for run in runs]
            requests = [json.loads((run / "request.json").read_text()) for run in runs]
            self.assertEqual(len(runs), 2)
            self.assertEqual(len({s["output"] for s in statuses}), 2)
            self.assertEqual(len({s["pane"] for s in statuses}), 2)
            self.assertEqual(len({r["name"] for r in requests}), 2)
            self.assertTrue(all(s["state"] == "started" for s in statuses))
            self.assertTrue(all("--no-session" in r["pi_args"] for r in requests))
            self.assertTrue(all(r["history_inputs"] == [] for r in requests))
            self.assertTrue(all("do not resume sessions" in r["prompt"] for r in requests))
            starts = [c for c in calls.call_args_list if c.args[1:3] == ("agent", "start")]
            self.assertEqual(len(starts), 2)
            for run, status, request in zip(runs, statuses, requests):
                Path(status["partial"]).write_text(request["expected"])
                def finished(binary, *args, **kwargs):
                    if args[:2] == ("agent", "get"):
                        return {"agent": {"agent_status": "done"}}
                    if args[:2] == ("pane", "list"):
                        return {"panes": [{"pane_id": status["pane"], "tab_id": status["tab"]}]}
                    return {}
                with patch.object(tejun, "herdr", side_effect=finished), redirect_stdout(io.StringIO()):
                    self.assertEqual(tejun.worker(run), 0)
                self.assertEqual(Path(status["output"]).read_text(), request["expected"])
            self.assertEqual(old.read_text(), "Keep this\n")

    def test_run_id_and_preexisting_partial_collisions_do_not_replace_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            reports = root / "reports"
            reports.mkdir()
            partial = reports / "fixture-fixed.partial.md"
            partial.write_text("Earlier partial\n")
            with patch.object(tejun, "STATE", root / "state"), \
                 patch.object(tejun, "new_run_id", return_value="fixed"), \
                 patch.object(tejun, "ensure_session") as session:
                with self.assertRaisesRegex(tejun.TejunError, "existing partial"):
                    tejun.launch(workflow(), prepared(root))
                status = root / "state/runs/fixed/status.json"
                previous = status.read_bytes()
                with self.assertRaisesRegex(tejun.TejunError, "Run ID collision"):
                    tejun.launch(workflow(), prepared(root))
                self.assertEqual(status.read_bytes(), previous)
                self.assertEqual(partial.read_text(), "Earlier partial\n")
                session.assert_not_called()

    def test_only_declared_history_is_supplied_and_no_ambient_resources_load(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            agent = root / "agent"
            agent.mkdir()
            (agent / "AGENTS.md").write_text("Fixture instructions\n")
            (root / "coverage.md").write_text("Declared history\n")
            (root / "unrelated.md").write_text("Do not load this\n")
            definition = {**tejun.definitions()["content-smoke-test"], "history_inputs": ["coverage.md"],
                          "exclusive_paths": ["coverage.md"]}
            config = {"paths": {"content_production": str(root)}, "pi": {
                "agent_dir": str(agent), "extensions": [], "provider": "fixture", "model": "exact",
                "thinking": "off"}}
            with patch.object(tejun.shutil, "which", side_effect=lambda name: f"/bin/{name}"), \
                 patch.object(tejun, "herdr") as herdr:
                request = tejun.prepare(definition, config)
                herdr.assert_not_called()
                self.assertEqual(request["history_inputs"], [str(root / "coverage.md")])
                self.assertEqual(request["exclusive_paths"], [str(root / "coverage.md")])
                for flag in ("--no-session", "--no-extensions", "--no-skills", "--no-mcp",
                             "--no-prompt-templates", "--no-themes"):
                    self.assertIn(flag, request["pi_args"])
                self.assertNotIn("--resume", request["pi_args"])
                self.assertNotIn("--continue", request["pi_args"])
                self.assertNotIn("unrelated.md", json.dumps(request))
                tab = {"root_pane": {"pane_id": "w1:p9"}, "tab": {"tab_id": "w1:t9"}}
                with patch.object(tejun, "STATE", root / "state"), \
                     patch.object(tejun, "ensure_session", return_value="w1"), \
                     patch.object(tejun, "herdr", return_value=tab), \
                     patch.object(tejun.subprocess, "Popen"), redirect_stdout(io.StringIO()):
                    tejun.launch(definition, request)
                saved = json.loads(next((root / "state/runs").glob("*/request.json")).read_text())
                self.assertIn(json.dumps([str(root / "coverage.md")]), saved["prompt"])
                self.assertNotIn("unrelated.md", saved["prompt"])
                (root / "coverage.md").unlink()
                with self.assertRaisesRegex(tejun.TejunError, "declared history input"):
                    tejun.prepare(definition, config)
                with self.assertRaisesRegex(tejun.TejunError, "inside"):
                    tejun.prepare({**definition, "history_inputs": ["../outside.md"]}, config)

    def test_shared_file_conflicts_are_rejected_across_processes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = root / "state"
            resource = str(root / "coverage.md")
            script = root / "contender.py"
            script.write_text(
                "import importlib.util,json,pathlib,sys,time\n"
                f"s=importlib.util.spec_from_file_location('tejun', {str(ROOT / 'tejun.py')!r})\n"
                "t=importlib.util.module_from_spec(s);s.loader.exec_module(t)\n"
                f"t.STATE=pathlib.Path({str(state)!r})\n"
                "run=pathlib.Path(sys.argv[1]);run.mkdir();status={'run':run.name,'locks':[]}\n"
                "try:\n"
                f" t.acquire_resources(run,status,[{resource!r}]);answer='acquired'\n"
                "except t.TejunError as e: answer=str(e)\n"
                "(run/'answer.json').write_text(json.dumps(answer))\n")
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            children = [subprocess.Popen([sys.executable, str(script), str(root / name)], env=env,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        for name in ("one", "two")]
            try:
                for child in children:
                    out, err = child.communicate(timeout=5)
                    self.assertEqual(child.returncode, 0, (out, err))
            finally:
                for child in children:
                    if child.poll() is None:
                        child.kill()
                        child.communicate(timeout=5)
            answers = [json.loads((root / name / "answer.json").read_text()) for name in ("one", "two")]
            self.assertEqual(answers.count("acquired"), 1)
            self.assertTrue(any("reserved" in answer for answer in answers))
            self.assertEqual(len(list((state / "locks").glob("*.json"))), 1)

    def test_reservations_release_after_success_but_not_uncertain_execution(self):
        for error in (None, tejun.RunInterrupted(signal.SIGTERM), tejun.TejunError("agent blocked")):
            with self.subTest(error=error), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                fixture = RunFixture(root)
                fixture.status["locks"] = []
                with patch.object(tejun, "STATE", root / "state"):
                    tejun.acquire_resources(root, fixture.status, [str(root / "coverage.md")])
                fixture.save()
                lock = Path(fixture.status["locks"][0]["path"])
                def fail(binary, *args, **kwargs):
                    raise error
                code = fixture.work(fail if error else None)
                self.assertEqual(code == 0, error is None)
                self.assertEqual(lock.exists(), error is not None)
                if error:
                    with patch.object(tejun, "STATE", root / "state"):
                        contender = {"run": "another", "locks": []}
                        with self.assertRaisesRegex(tejun.TejunError, "unconfirmed run"):
                            tejun.acquire_resources(root, contender, [str(root / "coverage.md")])

    def test_prelaunch_failure_releases_only_its_own_reservations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            own = str(root / "a.md")
            occupied = str(root / "z.md")
            with patch.object(tejun, "STATE", root / "state"), \
                 patch.object(tejun, "ensure_session") as session:
                owner = {"run": "original", "locks": []}
                tejun.acquire_resources(root, owner, [occupied])
                with self.assertRaisesRegex(tejun.TejunError, "reserved"):
                    tejun.launch(workflow(), prepared(root, exclusive_paths=[own, occupied]))
                locks = list((root / "state/locks").glob("*.json"))
                self.assertEqual(len(locks), 1)
                self.assertEqual(json.loads(locks[0].read_text())["run"], "original")
                session.assert_not_called()

    def test_concurrent_session_initialization_starts_only_one_server(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "initialize.py"
            script.write_text(
                "import importlib.util,pathlib,time,types\n"
                f"s=importlib.util.spec_from_file_location('tejun', {str(ROOT / 'tejun.py')!r})\n"
                "t=importlib.util.module_from_spec(s);s.loader.exec_module(t)\n"
                f"root=pathlib.Path({str(root)!r});t.STATE=root/'state'\n"
                "def herdr(binary,*args,**kwargs):\n"
                " if not (root/'ready').exists(): raise t.HerdrNotRunning('missing')\n"
                " return {'workspaces':[{'workspace_id':'w1'}]}\n"
                "def start(*args,**kwargs):\n"
                " with (root/'starts').open('a') as stream: stream.write('start\\n')\n"
                " time.sleep(0.1);(root/'ready').write_text('ready')\n"
                " return types.SimpleNamespace(poll=lambda:None)\n"
                "t.herdr=herdr;t.subprocess.Popen=start\n"
                "assert t.ensure_session('fixture',root)=='w1'\n")
            children = [subprocess.Popen([sys.executable, str(script)],
                                         env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        for _ in range(2)]
            try:
                for child in children:
                    out, err = child.communicate(timeout=5)
                    self.assertEqual(child.returncode, 0, (out, err))
                self.assertEqual((root / "starts").read_text(), "start\n")
            finally:
                for child in children:
                    if child.poll() is None:
                        child.kill()
                        child.communicate(timeout=5)

    def test_sigkill_leaves_unconfirmed_work_and_reservation_not_false_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture = RunFixture(root)
            fixture.status["locks"] = []
            with patch.object(tejun, "STATE", root / "state"):
                tejun.acquire_resources(root, fixture.status, [str(root / "coverage.md")])
            fixture.save()
            ready = root / "ready"
            code = (
                "import importlib.util,pathlib,sys,time\n"
                f"s=importlib.util.spec_from_file_location('tejun', {str(ROOT / 'tejun.py')!r})\n"
                "t=importlib.util.module_from_spec(s);s.loader.exec_module(t)\n"
                "def wait(*args,**kwargs):\n"
                f" pathlib.Path({str(ready)!r}).write_text('ready');time.sleep(30)\n"
                "t.herdr=wait\n"
                f"t.worker(pathlib.Path({str(root)!r}))\n")
            child = subprocess.Popen([sys.executable, "-c", code],
                                     env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 5
                while not ready.exists():
                    if child.poll() is not None or time.monotonic() > deadline:
                        self.fail("worker did not reach fixture wait")
                    time.sleep(0.01)
                child.kill()
                child.communicate(timeout=5)
                final = fixture.final()
                self.assertEqual(final["state"], "working")
                self.assertNotIn("finished_at", final)
                self.assertTrue(Path(final["locks"][0]["path"]).exists())
                self.assertFalse(fixture.output.exists())
            finally:
                if child.poll() is None:
                    child.kill()
                    child.communicate(timeout=5)

    def test_agent_start_failure_retains_reservation_for_inspection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def fail_start(binary, *args, **kwargs):
                if args[:2] == ("tab", "create"):
                    return {"root_pane": {"pane_id": "w1:p9"}, "tab": {"tab_id": "w1:t9"}}
                raise tejun.TejunError("startup could have left an agent")
            with patch.object(tejun, "STATE", root / "state"), \
                 patch.object(tejun, "ensure_session", return_value="w1"), \
                 patch.object(tejun, "herdr", side_effect=fail_start):
                with self.assertRaisesRegex(tejun.TejunError, "startup could have left"):
                    tejun.launch(workflow(), prepared(root, exclusive_paths=[str(root / "coverage.md")]))
            statuses = list((root / "state/runs").glob("*/status.json"))
            status = json.loads(statuses[0].read_text())
            self.assertEqual(status["state"], "failed")
            self.assertTrue(status["agent_start_attempted"])
            self.assertTrue(Path(status["locks"][0]["path"]).exists())
            self.assertIn("agent", status)

    def test_foreign_reservation_is_never_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock = root / "lock.json"
            lock.write_text(json.dumps({"run": "other"}))
            status = {"run": "mine", "locks": [{"path": str(lock)}]}
            tejun.release_resources(status)
            self.assertTrue(lock.exists())
            self.assertIn("ownership changed", status["lock_cleanup_error"])


if __name__ == "__main__":
    unittest.main()
