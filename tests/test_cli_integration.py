"""Run the installed CLI and detached worker outside the repo with fake Herdr.

The fake never starts Pi, contacts a provider, or touches a real Herdr session.
"""

import json
import os
from pathlib import Path
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
    output = pathlib.Path(json.loads(re.search(r'at ("(?:[^"\\]|\\.)*")', prompt).group(1)))
    (root / "prompt-ready").write_text("ready")
    deadline = time.monotonic() + 10
    while not (root / "finish").exists():
        if time.monotonic() >= deadline: raise SystemExit("fixture gate timed out")
        time.sleep(0.01)
    output.write_text("# Content production smoke test\n\n"
                      "Pi Tejun wrote this file through the shared workflow launcher.\n")
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
    def test_installed_cli_returns_before_completion_and_worker_publishes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bin_dir, agent, outside, fake = [root / name for name in ("bin", "agent", "outside", "fake")]
            for directory in (bin_dir, agent, outside, fake):
                directory.mkdir()
            (agent / "AGENTS.md").write_text("Fixture instructions\n")
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
            config.write_text(
                'enabled = []\n[pi]\nprovider = "fixture"\nmodel = "exact"\nthinking = "off"\n'
                'extensions = []\ntimeout_seconds = 10\nagent_dir = ' + json.dumps(str(agent)) +
                '\n[paths]\ncontent_production = ' + json.dumps(str(destination)) + '\n')
            env = {**os.environ, "TEJUN_CONFIG": str(config), "TEJUN_STATE_DIR": str(root / "state"),
                   "HERDR_ENV": "1", "FAKE_HERDR_DIR": str(fake), "PYTHONDONTWRITEBYTECODE": "1",
                   "PATH": str(bin_dir)}
            setup = subprocess.run([sys.executable, str(ROOT / "install.py"), "--bin-dir", str(bin_dir)],
                                   cwd=outside, env=env, capture_output=True, text=True, timeout=5)
            self.assertEqual(setup.returncode, 0, setup.stderr)
            status = {}
            try:
                launched = subprocess.run([str(bin_dir / "tejun"), "run", "content-smoke-test"],
                                          cwd=outside, env=env, capture_output=True, text=True, timeout=5)
                self.assertEqual(launched.returncode, 0, launched.stderr)
                self.assertIn("completion is pending", launched.stdout)
                records = list((root / "state/runs").glob("*/status.json"))
                self.assertEqual(len(records), 1)
                record = records[0]
                status = json.loads(record.read_text())
                self.assertIn(status["state"], {"started", "working"})
                self.assertFalse(Path(status["output"]).exists())
                deadline = time.monotonic() + 5
                while not (fake / "prompt-ready").exists():
                    if time.monotonic() > deadline:
                        self.fail("detached worker did not submit the prompt")
                    time.sleep(0.01)
                (fake / "finish").write_text("finish")
                while True:
                    status = json.loads(record.read_text())
                    if "finished_at" in status:
                        break
                    if time.monotonic() > deadline:
                        self.fail("detached worker did not finish")
                    time.sleep(0.01)
                self.assertEqual(status["state"], "success", status)
                self.assertTrue(status["tab_closed"])
                self.assertTrue((fake / "tab-closed").exists())
                self.assertFalse(Path(status["partial"]).exists())
                self.assertEqual(Path(status["output"]).read_text(),
                                 "# Content production smoke test\n\n"
                                 "Pi Tejun wrote this file through the shared workflow launcher.\n")
            finally:
                (fake / "finish").write_text("finish")
                if status.get("worker_pid") and status.get("state") == "working":
                    try:
                        os.kill(status["worker_pid"], signal.SIGTERM)
                    except ProcessLookupError:
                        pass


if __name__ == "__main__":
    unittest.main()
