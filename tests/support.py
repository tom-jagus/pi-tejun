"""Shared disposable fixtures. Nothing here launches real Pi or Herdr."""

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


tejun = module("tejun", ROOT / "tejun.py")
installer = module("installer", ROOT / "install.py")


def workflow(**changes):
    # Exercise the supported exact mode without depending on a shipped test workflow.
    return {"name": "fixture", "description": "Disposable exact workflow",
            "workspace": "fixture", "output_dir": ".", "heading": "# Expected",
            "result_text": "Body", "tools": ["read", "write"], "skills": [],
            "allowed_effects": "Write only the reserved fixture report.",
            "prompt": "Write {output_path} with {heading} followed by {result_text}.", **changes}


def prepared(root, **changes):
    return {"workspace": str(root), "input": None, "output_dir": str(root / "reports"),
            "agent_dir": str(root / "agent"), "path": "/fixture/bin", "herdr": "fixture",
            "provider": "fixture", "model": "exact", "pi_args": ["--no-session"],
            "expected": "# Expected\n\nBody\n", "timeout": 1,
            "history_inputs": [], "exclusive_paths": [], **changes}


def configuration(root):
    agent = root / "agent"
    agent.mkdir()
    (agent / "AGENTS.md").write_text("Fixture instructions\n")
    return {"pi": {"agent_dir": str(agent), "extensions": [], "provider": "fixture",
                   "model": "exact", "thinking": "off"}, "paths": {"fixture": str(root)}}


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
