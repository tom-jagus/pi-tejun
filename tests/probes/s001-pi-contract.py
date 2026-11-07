#!/usr/bin/env python3
"""Probe Pi CLI startup without credentials, model requests, or user config writes."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


# This explicitly loaded test extension observes startup and consumes the command.
# It does not call a model, execute tools, or print instruction contents.
AUDIT_EXTENSION = r'''
import { writeFileSync } from "node:fs";

export default function (pi) {
  pi.on("input", (event) => {
    writeFileSync(process.env.TEJUN_PROBE_OUTPUT, JSON.stringify({text: event.text}));
    return { action: "handled" };
  });
  pi.registerCommand("tejun-probe", {
    description: "Observe startup without calling a model",
    handler: async (_args, ctx) => {
      const options = ctx.getSystemPromptOptions();
      writeFileSync(process.env.TEJUN_PROBE_OUTPUT, JSON.stringify({
        cwd: ctx.cwd,
        mode: ctx.mode,
        trusted: ctx.isProjectTrusted(),
        sessionId: ctx.sessionManager.getSessionId(),
        sessionFile: ctx.sessionManager.getSessionFile() ?? null,
        tools: pi.getActiveTools().sort(),
        allTools: pi.getAllTools().map(t => t.name).sort(),
        contextPaths: (options.contextFiles ?? []).map(f => f.path),
        skills: (options.skills ?? []).map(s => ({name: s.name, path: s.filePath})),
        commands: pi.getCommands().map(c => c.name),
        model: ctx.model ? `${ctx.model.provider}/${ctx.model.id}` : null,
        thinking: ctx.thinkingLevel,
        hasAppend: ctx.getSystemPrompt().includes("TEJUN_PROBE_APPEND"),
        hasUserSystem: ctx.getSystemPrompt().includes("TEJUN_PROBE_USER_SYSTEM"),
        hasUserAppend: ctx.getSystemPrompt().includes("TEJUN_PROBE_USER_APPEND"),
        hasProjectSystem: ctx.getSystemPrompt().includes("TEJUN_PROBE_PROJECT_SYSTEM"),
      }));
    },
  });
}
'''

CANARY_EXTENSION = 'throw new Error("AMBIENT_EXTENSION_MUST_NOT_LOAD");\n'


def put(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    pi = shutil.which("pi")
    if pi is None:
        raise SystemExit("Pi CLI is required")
    kijun = Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi/agent"))
    contract = kijun / "AGENTS.md"
    skill = kijun / "skills/unslop/SKILL.md"
    require(contract.is_file() and skill.is_file(), "Activate Kijun before probing")
    version = subprocess.check_output([pi, "--version"], text=True).strip()

    with tempfile.TemporaryDirectory(prefix="pi-tejun-s001-") as temporary:
        root = Path(temporary).resolve()
        agent = root / "agent"
        project = root / "workspace/destination"
        project.mkdir(parents=True)
        (agent / "skills").mkdir(parents=True)
        (agent / "AGENTS.md").symlink_to(contract.resolve())
        (agent / "skills/unslop").symlink_to(skill.parent.resolve())
        put(root / "workspace/AGENTS.md", "Ancestor instruction fixture.\n")
        put(project / "AGENTS.md", "Destination instruction fixture.\n")
        put(agent / "settings.json", json.dumps({
            "defaultProvider": "invalid-fixture-provider",
            "defaultModel": "invalid-fixture-model",
            "defaultThinkingLevel": "high",
        }))
        put(project / ".pi/settings.json", json.dumps({
            "defaultProvider": "invalid-project-provider",
            "sessionDir": str(root / "unwanted-sessions"),
        }))
        put(agent / "extensions/canary.ts", CANARY_EXTENSION)
        put(project / ".pi/extensions/canary.ts", CANARY_EXTENSION)
        for base in (agent, project / ".pi"):
            put(base / "skills/ambient/SKILL.md",
                "---\nname: ambient\ndescription: Must not be discovered.\n---\n")
            put(base / "prompts/ambient.md", "Must not become a command.\n")
            put(base / "mcp.json", json.dumps({"mcpServers": {
                "canary": {"command": "/must-not-be-started"}
            }}))
        put(project / ".pi/SYSTEM.md", "TEJUN_PROBE_PROJECT_SYSTEM\n")
        extension = root / "audit.ts"
        put(extension, AUDIT_EXTENSION)
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("PI_") and not key.endswith("API_KEY")}
        env.update({"PI_CODING_AGENT_DIR": str(agent), "PI_OFFLINE": "1"})
        args = [
            pi, "--offline", "--mode", "json", "--no-session",
            "--no-approve", "--no-extensions", "--extension", str(extension),
            "--no-mcp", "--no-skills", "--skill", str(agent / "skills/unslop"),
            "--no-prompt-templates", "--no-themes",
            "--tools", "read,grep,find,ls",
            "--provider", "openai", "--model", "gpt-4.1", "--thinking", "off",
            "--append-system-prompt", "TEJUN_PROBE_APPEND", "--", "/tejun-probe",
        ]

        def run(label, piped_canary=False):
            output = root / f"{label}.json"
            env["TEJUN_PROBE_OUTPUT"] = str(output)
            command = args
            stdin_options = {"stdin": subprocess.DEVNULL}
            if piped_canary:
                # A disposable launcher receives piped input but deliberately
                # gives Pi an empty stdin. The input hook records Pi's prompt.
                helper = ("import subprocess,sys; "
                          "sys.exit(subprocess.run(sys.argv[1:], "
                          "stdin=subprocess.DEVNULL).returncode)")
                command = [sys.executable, "-c", helper, *args]
                stdin_options = {"input": "UNDECLARED_STDIN_CANARY"}
            result = subprocess.run(command, cwd=project, env=env,
                                    capture_output=True, text=True, timeout=30,
                                    **stdin_options)
            require(result.returncode == 0,
                    f"{label}: Pi exited {result.returncode}: {result.stderr}")
            require(output.is_file(), f"{label}: audit command did not execute")
            # JSONL framing uses LF, not Python's broader splitlines().
            records = [json.loads(line) for line in result.stdout.split("\n") if line]
            require(records and records[0]["type"] == "session", "Missing JSON header")
            require(not any(r["type"] == "agent_start" for r in records),
                    "Probe unexpectedly started a model-backed run")
            require("AMBIENT_EXTENSION_MUST_NOT_LOAD" not in result.stderr,
                    "Ambient extension loaded")
            return json.loads(output.read_text())

        first = run("first")
        second = run("second")
        require(first["cwd"] == str(project), "Wrong execution cwd")
        require(first["mode"] == "json" and not first["trusted"], "Wrong mode or trust")
        require(first["sessionFile"] is None and second["sessionFile"] is None,
                "Session persisted despite --no-session")
        require(first["sessionId"] != second["sessionId"], "Session identity reused")
        require(first["tools"] == ["find", "grep", "ls", "read"], "Wrong active tools")
        require(not any(name.startswith("mcp__") for name in first["allTools"]),
                "MCP tools registered")
        require([s["name"] for s in first["skills"]] == ["unslop"],
                "Explicit skill selection did not exclude ambient skills")
        require("ambient" not in first["commands"], "Ambient prompt loaded")
        require(first["model"] == "openai/gpt-4.1" and first["thinking"] == "off",
                "Explicit model or thinking selection not honored")
        context = first["contextPaths"]
        for expected in (agent / "AGENTS.md", root / "workspace/AGENTS.md",
                         project / "AGENTS.md"):
            require(str(expected) in context, f"Missing context file: {expected}")
        require(first["hasAppend"] and not first["hasProjectSystem"],
                "Appended contract missing or untrusted project SYSTEM loaded")
        require(not (root / "unwanted-sessions").exists(), "Project sessionDir used")
        require(not list(agent.glob("sessions/**/*.jsonl")), "Session files created")

        # Document the remaining ambient instruction inputs instead of assuming
        # the resource flags create a completely independent execution profile.
        put(agent / "SYSTEM.md", "TEJUN_PROBE_USER_SYSTEM\n")
        put(agent / "APPEND_SYSTEM.md", "TEJUN_PROBE_USER_APPEND\n")
        ambient = run("user-system")
        require(ambient["hasUserSystem"] and not ambient["hasUserAppend"],
                "Explicit append did not replace the user APPEND_SYSTEM input")
        append_index = args.index("--append-system-prompt")
        del args[append_index:append_index + 2]
        without_append = run("without-explicit-append")
        require(without_append["hasUserSystem"] and without_append["hasUserAppend"],
                "User APPEND_SYSTEM input missing without an explicit append")
        args[-1] = "TEJUN_FIXED_PROMPT"
        piped = run("piped-stdin", piped_canary=True)
        require(piped["text"] == "TEJUN_FIXED_PROMPT",
                "Piped canary reached Pi despite closed child stdin")
        print(f"PASS: Pi {version}; five startup probes; no model requests")
        print("Verified JSON header, fresh ephemeral sessions, destination context,")
        print("explicit model/thinking/tools/skill, disabled ambient resources and MCP,")
        print("ignored project config, retained user SYSTEM, explicit append precedence,")
        print("and exclusion of piped launcher input from Pi's prompt.")
        print("Temporary fixtures removed on exit. No user settings or credentials changed.")


if __name__ == "__main__":
    main()
