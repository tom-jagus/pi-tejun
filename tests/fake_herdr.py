#!/usr/bin/env python3
"""Disposable CLI fixture. Never starts an agent or contacts a provider."""

import json
import os
from pathlib import Path
import sys
import time
import uuid

root = Path(os.environ["FAKE_HERDR_DIR"])
args = sys.argv[1:]
assert args[:2] == ["--session", "tejun"], args
args = args[2:]
command = args[:2]
result = {}

if command == ["workspace", "list"]:
    result = {"workspaces": [json.loads(path.read_text())["workspace"]
                             for path in root.glob("workspace-*.json")]}
elif command in (["workspace", "create"], ["tab", "create"]):
    assert "--no-focus" in args and "--env" in args
    suffix = uuid.uuid4().hex[:8]
    if command[0] == "workspace":
        workspace = {"workspace_id": "w" + suffix, "label": args[args.index("--label") + 1]}
    else:
        assert "--label" not in args
        wid = args[args.index("--workspace") + 1]
        workspace = json.loads((root / ("workspace-" + wid + ".json")).read_text())["workspace"]
    wid = workspace["workspace_id"]
    result = {"workspace": workspace, "root_pane": {"pane_id": wid + ":p" + suffix},
              "tab": {"tab_id": wid + ":t" + suffix, "workspace_id": wid, "label": "1"}}
    (root / ("workspace-" + wid + ".json")).write_text(json.dumps(result))
elif command == ["tab", "list"]:
    path = root / ("workspace-" + args[args.index("--workspace") + 1] + ".json")
    result = {"tabs": [json.loads(path.read_text())["tab"]] if path.exists() else []}
elif command == ["agent", "start"]:
    assert "--no-session" in args
    (root / (args[2] + ".json")).write_text(json.dumps({
        "pane": args[args.index("--pane") + 1], "active": True}))
elif command == ["agent", "prompt"]:
    paths = Path(os.environ["TEJUN_STATE_DIR"]).glob("runs/*/request.json")
    request_path = next(path for path in paths if json.loads(path.read_text())["name"] == args[2])
    request = json.loads(request_path.read_text())
    status = json.loads((request_path.parent / "status.json").read_text())
    deadline = time.monotonic() + 10
    while not (root / "finish").exists():
        if time.monotonic() >= deadline:
            raise SystemExit("fixture gate timed out")
        time.sleep(.01)
    results = json.loads((root / "results.json").read_text())
    if request.get("result_check") == "digest":
        context = request["digest_context"]
        report = results.get("digest", "# Digest - Sunday, November 8, 2026\n\nCoverage: " + context["start"] +
                             " to " + context["end"] + "\n\nNo verified updates since the last check.\n")
    else:
        report = results[status["workflow"]]
    Path(status["partial"]).write_text(report, encoding="utf-8")
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
        if record["active"]:
            pane["agent"] = "pi"
        panes.append(pane)
    result = {"panes": panes}
elif command == ["tab", "close"]:
    for path in root.glob("workspace-*.json"):
        if json.loads(path.read_text())["tab"]["tab_id"] == args[2]:
            path.unlink()
else:
    raise SystemExit("Unexpected fake Herdr request: " + repr(args))
print(json.dumps({"result": result}))
