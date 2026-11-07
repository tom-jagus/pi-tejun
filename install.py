#!/usr/bin/env python3
"""Install the user-level Tejun command without changing Pi or shell settings."""

import argparse
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent


def install(bin_dir, config_path, agent_dir):
    target = ROOT / "tejun.py"
    link = bin_dir / "tejun"
    # Check collisions before creating any files. A dangling unrelated link is
    # still an existing command, and must never be replaced.
    if os.path.lexists(link) and not (link.is_symlink() and link.resolve() == target):
        raise ValueError(f"Refusing to replace unrelated command: {link}")
    other = shutil.which("tejun")
    if other and Path(other).resolve() != target:
        raise ValueError(f"An unrelated tejun already exists on PATH: {other}")
    if not config_path.exists():
        settings_path = agent_dir / "settings.json"
        settings = json.loads(settings_path.read_text())
        defaults = [settings.get(key) for key in
                    ("defaultProvider", "defaultModel", "defaultThinkingLevel")]
        if not all(isinstance(value, str) and value for value in defaults):
            raise ValueError("Save Pi provider/model/thinking defaults first, or create "
                             f"{config_path} from config.example.toml.")
        workspace = config_path.parent / "verification"
        content = (ROOT / "config.example.toml").read_text()
        substitutions = {
            '"/absolute/path/to/.pi/agent"': str(agent_dir),
            '"your-provider"': defaults[0], '"your-exact-model-id"': defaults[1],
            '"low"': defaults[2],
            '"/absolute/path/to/.pi/agent/extensions/herdr-agent-state.ts"':
                str(agent_dir / "extensions/herdr-agent-state.ts"),
            '"/absolute/path/to/pi-tejun/verification"': str(workspace),
        }
        for placeholder, value in substitutions.items():
            content = content.replace(placeholder, json.dumps(value))
        config_path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation preserves an existing local config, even on races.
        with config_path.open("x") as output:
            output.write(content)
        workspace.mkdir(parents=True, exist_ok=True)
        source = workspace / "input.md"
        if not source.exists():
            with source.open("x") as output:
                output.write((ROOT / "workflows/verify-input.md").read_text())
    bin_dir.mkdir(parents=True, exist_ok=True)
    if not os.path.lexists(link):
        link.symlink_to(target)
    print(f"Installed: {link} -> {target}")
    print(f"Configuration: {config_path}")
    if str(bin_dir) not in os.environ.get("PATH", "").split(os.pathsep):
        print(f"Add {bin_dir} to PATH yourself, or use {link} directly.")
    print("No Pi settings or shell startup files were changed.")


def main():
    if sys.version_info < (3, 11):
        raise ValueError("Python 3.11 or newer is required.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin-dir", type=Path, default=Path.home() / ".local/bin")
    args = parser.parse_args()
    config = Path(os.environ.get("TEJUN_CONFIG", "~/.config/pi-tejun/config.toml")).expanduser().resolve()
    agent = Path(os.environ.get("PI_CODING_AGENT_DIR", "~/.pi/agent")).expanduser().resolve()
    install(args.bin_dir.expanduser().resolve(), config, agent)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        print(f"install: {error}", file=sys.stderr)
        sys.exit(1)
