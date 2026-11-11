#!/usr/bin/env python3
"""Opt-in paid Pi/search probe using Tejun's actual prepared arguments.

Usage: python3 tests/probes/s012-research.py --config /path/to/probe.toml
The config needs pi.subagent_extension and pi.search_extension. No Herdr server
is started: this exercises Pi startup/child execution, not the terminal bridge.
Artifacts are retained in the printed temporary directory.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import tejun

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--config", type=Path, required=True)
parser.add_argument("--parallel", action="store_true", help="Probe three overlapping foreground children")
args = parser.parse_args()
root = Path(tempfile.mkdtemp(prefix="tejun-s012-"))
print(f"Probe artifacts: {root}", flush=True)
config = tejun.load_toml(args.config)
config["paths"] = {"probe": str(root)}
item = {
    "name": "research-probe", "description": "S012 integration probe",
    "workspace": "probe", "output_dir": ".", "heading": "# Probe",
    "research": True, "tools": ["read", "write", "subagent", "web_search"],
    "skills": [], "result_text": "Search child returned.",
    "allowed_effects": "Read/search, then write only the probe partial.",
    "prompt": "unused",
}
prepared = tejun.prepare(item, config)
env = dict(os.environ, PI_CODING_AGENT_DIR=prepared["agent_dir"],
           TEJUN_CHILDREN_FILE=str(root / "children.json"),
           TEJUN_SEARCH_EXTENSION=prepared["search_extension"],
           TEJUN_SUBAGENT_EXTENSION=prepared["subagent_extension"],
           TEJUN_ERROR_FILE=str(root / "pi-error.txt"),
           TEJUN_EXPECTED_PROVIDER=prepared["provider"],
           TEJUN_EXPECTED_MODEL=prepared["model"])
prompt = (
    'This is an authorized integration probe. Call subagent exactly once with '
    'agent="tejun-researcher", async=false, task="Use web_search once to find '
    'the official Python pathlib documentation URL. Return the URL, whether '
    'search succeeded, and your available tools. Do not write or run commands." '
    f'Then write {json.dumps(str(root / "result.partial.md"))} with exactly '
    f'{json.dumps(prepared["expected"])}. In your final response reproduce the '
    'child findings and disclose search failure if any.'
)
if args.parallel:
    prompt = (
        'This is an authorized concurrency probe. Make ONE subagent call with '
        'workflow="tejun-research", async=false, args containing tasks as a list '
        'of THREE strings. The first task is to use web_search to find official '
        'Python pathlib docs, the second official Git documentation, the third '
        'official SQLite docs. Each task requests the URL and available tools, '
        'with no writes, commands, or nested work. The resource handles concurrency. '
        'Await the batch and check every child, then write '
        f'{json.dumps(str(root / "result.partial.md"))} with exactly '
        f'{json.dumps(prepared["expected"])} and summarize their results.'
    )
with (root / "parent.log").open("w") as log:
    try:
        result = subprocess.run(["pi", *prepared["pi_args"], "-p", prompt],
                                cwd=root, env=env, stdout=log,
                                stderr=subprocess.STDOUT, timeout=180)
    except subprocess.TimeoutExpired:
        sys.exit("Probe timed out; inspect retained artifacts. No publication attempted.")
receipt = tejun.load_json(root / "children.json")
assert result.returncode == 0, "Pi startup or execution failed; inspect parent.log"
assert not (root / "pi-error.txt").exists(), "Pi reported failure"
assert receipt["ready"] and receipt["children"], "Plugin/children unavailable"
assert set(receipt["children"].values()) == {"completed"}, "Child settlement not proven"
searches = [json.loads(line) for line in
            (root / "children.json.search.jsonl").read_text().splitlines()]
assert not any(row.get("ready") is False for row in searches), "Child tools unavailable"
assert any(row.get("search") == "succeeded" for row in searches), "No successful child search"
assert (root / "result.partial.md").read_text() == prepared["expected"]
if args.parallel:
    starts = {row["child_started"]: row["at"] for row in searches if "child_started" in row}
    ends = {row["child_finished"]: row["at"] for row in searches if "child_finished" in row}
    assert len(receipt["children"]) == 1 and len(starts) == len(ends) == 3, "Expected one batch of three settled children"
    assert max(starts.values()) < min(ends.values()), "Children did not all overlap"
    print("Three actual child-session lifetimes overlapped; all three settled.")
print("Pi startup, child terminal receipt, and parent result passed. Inspect parent.log")
print("for search success, sources, and tool loadout; child completion is not accuracy.")
