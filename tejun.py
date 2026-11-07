#!/usr/bin/env python3
"""Launch predefined Pi workflows in fresh, unfocused Herdr terminals."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import tomllib
import uuid

ROOT = Path(__file__).resolve().parent
CONFIG = Path(os.environ.get("TEJUN_CONFIG", "~/.local/share/pi-tejun/config.toml")).expanduser().resolve()
STATE = Path(os.environ.get("TEJUN_STATE_DIR", "~/.local/state/pi-tejun")).expanduser().resolve()
SESSION = "tejun"


class TejunError(Exception):
    pass


class HerdrNotRunning(TejunError):
    pass


def load_toml(path):
    try:
        return tomllib.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise TejunError(f"Cannot read {path}: {error}") from error


def absolute(value):
    if not isinstance(value, str) or not Path(value).expanduser().is_absolute():
        raise TejunError(f"Expected an absolute path, got {value!r}")
    return Path(value).expanduser().resolve()


def relative(root, value, *, allow_root=False):
    path = (root / value).resolve()
    if not path.is_relative_to(root) or (path == root and not allow_root):
        raise TejunError(f"Workflow path must stay inside {root}: {value}")
    return path


def definitions():
    workflows = {}
    for path in sorted((ROOT / "workflows").glob("*.toml")):
        item = load_toml(path)
        if not re.fullmatch(r"[a-z][a-z0-9-]*", item.get("name", "")):
            raise TejunError(f"Invalid workflow name in {path}")
        if item["name"] in workflows:
            raise TejunError(f"Duplicate workflow: {item['name']}")
        workflows[item["name"]] = item
    return workflows


def command(argv, *, env=None, timeout=30):
    try:
        result = subprocess.run(argv, env=env, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise TejunError(f"{argv[0]} failed: {error}") from error
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        error_type = TejunError
        try:
            response = json.loads(detail)
            if response.get("error", {}).get("code") == "server_not_running":
                error_type = HerdrNotRunning
        except (ValueError, AttributeError):
            pass
        raise error_type(f"{argv[0]} exited {result.returncode}: {detail}")
    return result.stdout


def herdr(binary, *args, timeout=30):
    if os.environ.get("HERDR_ENV") != "1":
        raise TejunError("Run Tejun from inside Herdr (HERDR_ENV=1).")
    try:
        return json.loads(command([binary, "--session", SESSION, *args],
                                  timeout=timeout))["result"]
    except (ValueError, KeyError) as error:
        raise TejunError("Herdr returned an unexpected response.") from error


def ensure_session(binary, workspace):
    """Reuse Tejun's session, or start its headless server without attaching."""
    try:
        workspaces = herdr(binary, "workspace", "list")["workspaces"]
    except HerdrNotRunning:
        STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
        log_path = STATE / "herdr-server.log"
        with log_path.open("a") as log:
            process = subprocess.Popen(
                [binary, "--session", SESSION, "server"],
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True, close_fds=True, cwd=workspace)
        deadline = time.monotonic() + 15
        while True:
            try:
                workspaces = herdr(binary, "workspace", "list", timeout=2)["workspaces"]
                break
            except HerdrNotRunning:
                code = process.poll()
                if code is not None:
                    raise TejunError(
                        f"Herdr session '{SESSION}' did not start (exit {code}). See {log_path}.")
                if time.monotonic() >= deadline:
                    raise TejunError(
                        f"Timed out starting Herdr session '{SESSION}'. See {log_path}.")
                time.sleep(0.1)
    if not workspaces:
        created = herdr(binary, "workspace", "create", "--cwd", str(workspace),
                        "--label", SESSION, "--no-focus")
        return created["workspace"]["workspace_id"]
    return workspaces[0]["workspace_id"]


def save_status(run_dir, status):
    temporary = run_dir / "status.tmp"
    temporary.write_text(json.dumps(status, indent=2) + "\n")
    temporary.replace(run_dir / "status.json")


def prepare(workflow, config):
    pi_config = config["pi"]
    workspace = absolute(config["paths"][workflow["workspace"]])
    if not workspace.is_dir():
        raise TejunError(f"Missing workflow directory: {workspace}")
    if ("input" in workflow) == ("result_text" in workflow):
        raise TejunError("A workflow must declare exactly one of input or result_text.")
    source = relative(workspace, workflow["input"]) if "input" in workflow else None
    text = source.read_text() if source else workflow["result_text"]
    if not isinstance(text, str) or not text.strip():
        raise TejunError(f"Workflow input or result_text is empty or invalid: {source or workflow['name']}")
    output_dir = relative(workspace, workflow["output_dir"], allow_root=True)
    agent_dir = absolute(pi_config["agent_dir"])
    for path in [agent_dir / "AGENTS.md", ROOT / "extensions/workflow-check.ts",
                 *map(absolute, pi_config["extensions"])]:
        if not path.is_file():
            raise TejunError(f"Missing Pi/Kijun resource: {path}")
    skills = [agent_dir / "skills" / name / "SKILL.md" for name in workflow["skills"]]
    for path in skills:
        if not path.is_file():
            raise TejunError(f"Missing Pi skill: {path}")
    selection = workflow.get("model", {})
    if not isinstance(selection, dict):
        raise TejunError("Workflow model settings must use a [model] table.")
    provider = selection.get("provider", pi_config.get("provider"))
    model = selection.get("id", pi_config.get("model"))
    thinking = selection.get("thinking", pi_config.get("thinking"))
    if (not isinstance(provider, str) or not provider or not isinstance(model, str) or not model
            or thinking not in {"off", "minimal", "low", "medium", "high", "xhigh", "max"}):
        raise TejunError("Configure an exact Pi provider/model and a valid thinking level.")
    timeout = pi_config.get("timeout_seconds", 300)
    if type(timeout) is not int or not 1 <= timeout <= 3600:
        raise TejunError("pi.timeout_seconds must be an integer between 1 and 3600.")
    pi = shutil.which("pi")
    binary = shutil.which("herdr")
    if not pi or not binary:
        raise TejunError("Both pi and herdr must be on PATH.")
    args = ["--no-session", "--no-approve", "--no-mcp", "--no-extensions",
            "--no-skills", "--no-prompt-templates", "--no-themes", "--offline",
            "--provider", provider, "--model", model, "--thinking", thinking,
            "--tools", ",".join(workflow["tools"])]
    for extension in pi_config["extensions"]:
        args += ["--extension", str(absolute(extension))]
    for skill in skills:
        args += ["--skill", str(skill)]
    args += ["--extension", str(ROOT / "extensions/workflow-check.ts")]
    # Pi resolves the model and authenticates during the actual workflow.
    # The in-process extension prevents fuzzy model substitution before input.
    workspace_id = ensure_session(binary, workspace)
    return {"workspace": str(workspace), "input": str(source) if source else None, "output_dir": str(output_dir),
            "expected": workflow["heading"] + "\n\n" + text.rstrip("\n") + "\n",
            "agent_dir": str(agent_dir), "pi_args": args, "herdr": binary,
            "provider": provider, "model": model,
            "path": str(Path(pi).parent) + os.pathsep + os.environ.get("PATH", ""),
            "workspace_id": workspace_id, "timeout": timeout}


def launch(workflow, prepared):
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:12]
    run_dir = STATE / "runs" / run_id
    run_dir.mkdir(parents=True, mode=0o700)
    output_dir = Path(prepared["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{workflow['name']}-{run_id}.md"
    partial = output.with_suffix(".partial.md")
    status = {"workflow": workflow["name"], "run": run_id, "state": "launching",
              "started_at": datetime.now(timezone.utc).isoformat(),
              "output": str(output), "partial": str(partial)}
    save_status(run_dir, status)
    try:
        tab = herdr(prepared["herdr"], "tab", "create", "--workspace", prepared["workspace_id"],
                    "--cwd", prepared["workspace"], "--label", f"tejun-{workflow['name']}",
                    "--no-focus", "--env", f"PI_CODING_AGENT_DIR={prepared['agent_dir']}",
                    "--env", f"PATH={prepared['path']}",
                    "--env", f"TEJUN_EXPECTED_PROVIDER={prepared['provider']}",
                    "--env", f"TEJUN_EXPECTED_MODEL={prepared['model']}",
                    "--env", f"TEJUN_ERROR_FILE={run_dir / 'pi-error.txt'}")
        status.update(pane=tab["root_pane"]["pane_id"], tab=tab["tab"]["tab_id"])
        save_status(run_dir, status)
        prompt = workflow["prompt"].format(input_path=json.dumps(prepared["input"]),
                                           output_path=json.dumps(str(partial)),
                                           heading=workflow["heading"],
                                           result_text=workflow.get("result_text", "").rstrip("\n"))
        request = {**prepared, "name": "tejun-" + run_id[-12:], "prompt": prompt}
        (run_dir / "request.json").write_text(json.dumps(request, indent=2) + "\n")
        # Wait only for Pi startup, not for the workflow. Startup rejection must
        # reach the caller instead of becoming a later background failure.
        herdr(prepared["herdr"], "agent", "start", request["name"], "--kind", "pi",
              "--pane", status["pane"], "--", *request["pi_args"], timeout=45)
        status["state"] = "started"
        save_status(run_dir, status)
        with (run_dir / "worker.log").open("w") as log:
            subprocess.Popen([sys.executable, str(ROOT / "tejun.py"), "_work", str(run_dir)],
                             stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                             start_new_session=True, close_fds=True, cwd=ROOT)
    except (TejunError, OSError, KeyError, ValueError) as error:
        status.update(state="failed", reason=workflow_error(run_dir, error))
        save_status(run_dir, status)
        raise
    print(f"Launched {workflow['name']} in {status['pane']} (completion is pending).")
    print(f"Result on success: {output}")
    print(f"Status: {run_dir / 'status.json'}")


def workflow_error(run_dir, error):
    try:
        diagnostic = (run_dir / "pi-error.txt").read_text().strip()
        return diagnostic or str(error)
    except OSError:
        return str(error)


def close_finished_tab(binary, status):
    panes = herdr(binary, "pane", "list")["panes"]
    members = [pane for pane in panes if pane.get("tab_id") == status["tab"]]
    if not members:
        return  # The tab was already closed.
    if (len(members) != 1 or members[0]["pane_id"] != status["pane"]
            or members[0].get("agent")):
        raise TejunError(f"Tab {status['tab']} was changed or reused; left open.")
    herdr(binary, "tab", "close", status["tab"])


def worker(run_dir):
    status = json.loads((run_dir / "status.json").read_text())
    request = json.loads((run_dir / "request.json").read_text())
    binary, name = request["herdr"], request["name"]
    try:
        status["state"] = "working"
        save_status(run_dir, status)
        herdr(binary, "agent", "prompt", name, request["prompt"], "--wait", "--timeout",
              str(request["timeout"] * 1000), timeout=request["timeout"] + 10)
        if (run_dir / "pi-error.txt").exists():
            raise TejunError(workflow_error(run_dir, "Pi workflow failed."))
        state = herdr(binary, "agent", "get", name)["agent"]["agent_status"]
        if state not in {"idle", "done"}:
            raise TejunError(f"Agent settled as {state}; left open in {status['pane']}.")
        partial = Path(status["partial"])
        if not partial.is_file() or partial.read_text() != request["expected"]:
            raise TejunError(f"Expected Markdown was not produced; agent left open in {status['pane']}.")
        herdr(binary, "agent", "send-keys", name, "ctrl+d")
        deadline = time.monotonic() + 10
        while True:
            panes = herdr(binary, "pane", "list")["panes"]
            pane = next((p for p in panes if p["pane_id"] == status["pane"]), None)
            if pane is None or not pane.get("agent"):
                break
            if time.monotonic() >= deadline:
                raise TejunError(f"Pi did not exit in {status['pane']}; result remains partial.")
            time.sleep(0.25)
        partial.rename(status["output"])
        status["state"] = "success"
        print(f"Completed {status['workflow']}: {status['output']}")
        try:
            close_finished_tab(binary, status)
            status["tab_closed"] = True
        except (TejunError, OSError, KeyError, ValueError) as error:
            # Cleanup failure must not relabel a validated result as failed.
            status["cleanup_error"] = str(error)
            print(f"Tab cleanup warning: {error}")
    except (TejunError, OSError, KeyError, ValueError) as error:
        status.update(state="incomplete", reason=workflow_error(run_dir, error))
        print(f"Incomplete: {status['reason']}")
    status["finished_at"] = datetime.now(timezone.utc).isoformat()
    save_status(run_dir, status)
    return 0 if status["state"] == "success" else 1


def main():
    parser = argparse.ArgumentParser(
        prog="tejun", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  tejun list\n  tejun run\n  tejun run verify")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("list", help="List workflows, enabled state, and destinations")
    run = sub.add_parser("run", help="Launch one workflow, or all enabled workflows")
    run.add_argument("name", nargs="?")
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return 0
    workflows = definitions()
    config = load_toml(CONFIG) if CONFIG.exists() else None
    enabled = config.get("enabled", []) if config else []
    if not isinstance(enabled, list) or any(not isinstance(name, str) for name in enabled):
        raise TejunError("enabled must be a list of workflow names.")
    if args.command == "list":
        for name, item in workflows.items():
            destination = "not configured"
            if config and item["workspace"] in config.get("paths", {}):
                destination = str(relative(absolute(config["paths"][item["workspace"]]),
                                           item["output_dir"], allow_root=True))
            print(f"{name}\t{'enabled' if name in enabled else 'disabled'}\t{item['description']}")
            print(f"  Output: {destination}")
        return 0
    if config is None:
        raise TejunError(f"Run python3 install.py first, then configure {CONFIG}.")
    names = [args.name] if args.name else enabled
    if not names:
        raise TejunError(f"No workflows enabled in {CONFIG}.")
    unknown = set(names) - workflows.keys()
    if unknown:
        raise TejunError(f"Unknown workflow(s): {', '.join(sorted(unknown))}")
    if len(names) != len(set(names)):
        raise TejunError("The enabled list contains duplicate workflow names.")
    # Validate all selected workflows before launching any of them.
    prepared = [(workflows[name], prepare(workflows[name], config)) for name in names]
    for item, request in prepared:
        launch(item, request)
    return 0


if __name__ == "__main__":
    try:
        if len(sys.argv) == 3 and sys.argv[1] == "_work":
            sys.exit(worker(Path(sys.argv[2])))
        sys.exit(main())
    except (TejunError, OSError, KeyError, TypeError, ValueError) as error:
        print(f"tejun: {error}", file=sys.stderr)
        sys.exit(1)
