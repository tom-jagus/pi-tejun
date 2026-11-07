"""Small, credential-free checks. Real Herdr/Pi verification is separate."""

from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


tejun = module("tejun", ROOT / "tejun.py")
installer = module("installer", ROOT / "install.py")


class LauncherTests(unittest.TestCase):
    def test_herdr_targets_tejun_and_recognizes_missing_server(self):
        with patch.dict(os.environ, {"HERDR_ENV": "1"}), \
             patch.object(tejun.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, '{"result": {"workspaces": []}}', '')
            self.assertEqual(tejun.herdr("herdr", "workspace", "list"), {"workspaces": []})
            self.assertEqual(run.call_args.args[0],
                             ["herdr", "--session", "tejun", "workspace", "list"])
            for code, error_type in (("server_not_running", tejun.HerdrNotRunning),
                                     ("permission_denied", tejun.TejunError)):
                run.return_value = subprocess.CompletedProcess(
                    [], 1, '', json.dumps({"error": {"code": code, "message": "fixture"}}))
                with self.subTest(code=code), self.assertRaises(error_type):
                    tejun.herdr("herdr", "workspace", "list")

    def test_session_reuses_existing_server_without_starting_or_focusing(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(tejun, "STATE", Path(temp)), \
             patch.object(tejun, "herdr", return_value={"workspaces": [{"workspace_id": "w7"}]}) as herdr, \
             patch.object(tejun.subprocess, "Popen") as popen:
            self.assertEqual(tejun.ensure_session("herdr", Path("/tmp")), [{"workspace_id": "w7"}])
            popen.assert_not_called()
            herdr.assert_called_once_with("herdr", "workspace", "list")

    def test_session_starts_detached_without_creating_a_shared_workspace(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            replies = [tejun.HerdrNotRunning("missing"), tejun.HerdrNotRunning("starting"),
                       {"workspaces": []}]
            with patch.object(tejun, "STATE", root / "state"), \
                 patch.object(tejun, "herdr", side_effect=replies) as herdr, \
                 patch.object(tejun.subprocess, "Popen") as popen, \
                 patch.object(tejun.time, "sleep"):
                popen.return_value.poll.return_value = None
                self.assertEqual(tejun.ensure_session("herdr", root), [])
                self.assertEqual(popen.call_args.args[0], ["herdr", "--session", "tejun", "server"])
                self.assertTrue(popen.call_args.kwargs["start_new_session"])
                self.assertEqual(popen.call_args.kwargs["stdin"], subprocess.DEVNULL)
                self.assertEqual(popen.call_args.kwargs["cwd"], root)
                self.assertEqual(herdr.call_args.args, ("herdr", "workspace", "list"))
                self.assertFalse(any(call.args[1:3] == ("workspace", "create")
                                     for call in herdr.call_args_list))
                self.assertTrue((root / "state/herdr-server.log").is_file())

    def test_session_reports_early_exit_and_readiness_timeout(self):
        for exit_code, times, reason in ((1, [0], "exit 1"),
                                        (None, [0, 16], "Timed out")):
            with self.subTest(exit_code=exit_code), tempfile.TemporaryDirectory() as temp, \
                 patch.object(tejun, "STATE", Path(temp)), \
                 patch.object(tejun, "herdr", side_effect=tejun.HerdrNotRunning("missing")), \
                 patch.object(tejun.subprocess, "Popen") as popen, \
                 patch.object(tejun.time, "monotonic", side_effect=times):
                popen.return_value.poll.return_value = exit_code
                with self.assertRaisesRegex(tejun.TejunError, reason) as error:
                    tejun.ensure_session("herdr", Path(temp))
                self.assertIn("herdr-server.log", str(error.exception))

    def test_session_does_not_start_for_unrelated_errors(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(tejun, "STATE", Path(temp)), \
             patch.object(tejun, "herdr", side_effect=tejun.TejunError("permission denied")), \
             patch.object(tejun.subprocess, "Popen") as popen:
            with self.assertRaisesRegex(tejun.TejunError, "permission denied"):
                tejun.ensure_session("herdr", Path("/tmp"))
            popen.assert_not_called()

    def test_runner_and_installer_share_config_default_and_override(self):
        with tempfile.TemporaryDirectory() as temp, redirect_stdout(io.StringIO()):
            home = Path(temp)
            agent = home / ".pi/agent"
            agent.mkdir(parents=True)
            (agent / "settings.json").write_text(json.dumps({
                "defaultProvider": "fixture", "defaultModel": "exact-id",
                "defaultThinkingLevel": "off"}))
            for override in (None, str(home / "custom/config.toml")):
                env = {"HOME": str(home)}
                if override:
                    env["TEJUN_CONFIG"] = override
                expected = Path(override) if override else home / ".config/pi-tejun/config.toml"
                with patch.dict(os.environ, env, clear=True), \
                     patch("sys.argv", ["install.py"]), \
                     patch.object(installer.shutil, "which", return_value=None):
                    installer.main()
                    runner = module("config_probe", ROOT / "tejun.py")
                    self.assertEqual(runner.CONFIG, expected)
                    self.assertEqual(runner.load_toml(expected)["pi"]["model"], "exact-id")
                    self.assertFalse((home / ".local/share/pi-tejun/config.toml").exists())
                    original = expected.read_bytes()
                    installer.main()
                    self.assertEqual(expected.read_bytes(), original)

    def test_install_is_repeatable_and_preserves_collisions(self):
        with tempfile.TemporaryDirectory() as temp, redirect_stdout(io.StringIO()):
            root = Path(temp)
            agent = root / "agent"
            agent.mkdir()
            (agent / "settings.json").write_text(json.dumps({
                "defaultProvider": "fixture", "defaultModel": "exact-id",
                "defaultThinkingLevel": "off"}))
            config = root / "data/config.toml"
            bin_dir = root / "bin"
            with patch.object(installer.shutil, "which", return_value=None):
                installer.install(bin_dir, config, agent)
                original = config.read_text()
                installer.install(bin_dir, config, agent)
                self.assertEqual(config.read_text(), original)
                self.assertEqual((bin_dir / "tejun").resolve(), ROOT / "tejun.py")
                self.assertEqual(tejun.load_toml(config)["pi"]["model"], "exact-id")
                (bin_dir / "tejun").unlink()
                (bin_dir / "tejun").symlink_to(root / "unrelated-missing-command")
                with self.assertRaisesRegex(ValueError, "unrelated command"):
                    installer.install(bin_dir, config, agent)
                self.assertTrue((bin_dir / "tejun").is_symlink())

    def test_listing_and_unknown_name_do_not_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "config.toml"
            config.write_text('invalid TOML = [\n')
            with patch.object(tejun, "CONFIG", config), patch.object(tejun, "herdr") as herdr:
                # Bare invocation must succeed even before configuration works.
                with patch("sys.argv", ["tejun"]), redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(tejun.main(), 0)
                self.assertIn("usage: tejun", output.getvalue())
                self.assertIn("tejun run verify", output.getvalue())
                config.write_text('enabled = []\n')
                with patch("sys.argv", ["tejun", "list"]), redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(tejun.main(), 0)
                self.assertIn("verify\tdisabled", output.getvalue())
                with patch("sys.argv", ["tejun", "run", "missing"]):
                    with self.assertRaisesRegex(tejun.TejunError, "Unknown workflow"):
                        tejun.main()
                herdr.assert_not_called()

    def test_preparation_uses_local_checks_without_starting_pi(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            agent = root / "agent"
            agent.mkdir()
            (agent / "AGENTS.md").write_text("Fixture instructions.\n")
            source = root / "input.md"
            source.write_text("Declared input.\n")
            workflow = {**tejun.definitions()["verify"], "skills": [],
                        "model": {"provider": "workflow-provider", "id": "workflow-id", "thinking": "high"}}
            config = {"paths": {"verification": str(root)}, "pi": {
                "agent_dir": str(agent), "provider": "openai", "model": "exact-id",
                "thinking": "off", "extensions": []}}
            with patch.object(tejun.shutil, "which", side_effect=lambda name: f"/bin/{name}"), \
                 patch.object(tejun, "command") as command, \
                 patch.object(tejun, "herdr", return_value={"workspaces": [{"workspace_id": "w1"}]}):
                prepared = tejun.prepare(workflow, config)
                self.assertEqual(prepared["provider"], "workflow-provider")
                self.assertEqual(prepared["model"], "workflow-id")
                self.assertEqual(prepared["pi_args"][prepared["pi_args"].index("--thinking") + 1], "high")
                self.assertIn(str(ROOT / "extensions/workflow-check.ts"), prepared["pi_args"])
                self.assertNotIn("--list-models", prepared["pi_args"])
                fallback = tejun.prepare({k: v for k, v in workflow.items() if k != "model"}, config)
                self.assertEqual(fallback["provider"], "openai")
                self.assertEqual(fallback["model"], "exact-id")
                source.unlink()
                with self.assertRaisesRegex(tejun.TejunError, "Cannot read workflow input"):
                    tejun.prepare(workflow, config)
                source.write_text("Declared input.\n")
                with patch.object(tejun.shutil, "which", return_value=None):
                    with self.assertRaisesRegex(tejun.TejunError, "must be on PATH"):
                        tejun.prepare(workflow, config)
                command.assert_not_called()

    def test_content_smoke_test_needs_no_input_and_writes_to_workspace_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace = root / "content-production"
            workspace.mkdir()
            agent = root / "agent"
            agent.mkdir()
            (agent / "AGENTS.md").write_text("Fixture instructions.\n")
            workflow = tejun.definitions()["content-smoke-test"]
            config = {"paths": {"content_production": str(workspace)}, "pi": {
                "agent_dir": str(agent), "provider": "fixture", "model": "exact-id",
                "thinking": "off", "extensions": []}}
            with patch.object(tejun.shutil, "which", side_effect=lambda name: f"/bin/{name}"), \
                 patch.object(tejun, "herdr", return_value={"workspaces": [{"workspace_id": "w1"}]}), \
                 patch.object(tejun, "CONFIG", root / "config.toml"):
                prepared = tejun.prepare(workflow, config)
                self.assertIsNone(prepared["input"])
                self.assertEqual(prepared["output_dir"], str(workspace))
                self.assertEqual(prepared["expected"],
                                 "# Content production smoke test\n\n"
                                 "Pi Tejun wrote this file through the shared workflow launcher.\n")
                prompt = workflow["prompt"].format(
                    output_path=json.dumps(str(workspace / "result.partial.md")),
                    heading=workflow["heading"], result_text=workflow["result_text"])
                self.assertIn(prepared["expected"], prompt)
                self.assertEqual(prepared["model"], "exact-id")
                tejun.CONFIG.write_text("[paths]\ncontent_production = " +
                                        json.dumps(str(workspace)) + "\n")
                with patch("sys.argv", ["tejun", "list"]), \
                     redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(tejun.main(), 0)
                self.assertIn(f"Output: {workspace}", output.getvalue())
                for changes in ({"input": "input.md"}, {"result_text": ""},
                                {"output_dir": "../escape"}):
                    with self.subTest(changes=changes), self.assertRaises(tejun.TejunError):
                        tejun.prepare({**workflow, **changes}, config)
                self.assertEqual(list(workspace.iterdir()), [])

    def test_relative_paths_allow_root_only_for_outputs_and_reject_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            self.assertEqual(tejun.relative(root, ".", allow_root=True), root)
            with self.assertRaises(tejun.TejunError):
                tejun.relative(root, ".")
            for value in ("..", "../escape"):
                with self.subTest(value=value), self.assertRaises(tejun.TejunError):
                    tejun.relative(root, value, allow_root=True)
            (root / "outside").symlink_to(root.parent, target_is_directory=True)
            with self.assertRaises(tejun.TejunError):
                tejun.relative(root, "outside/escape", allow_root=True)

    def test_subprocesses_exclude_caller_stdin_and_worker_is_detached(self):
        with patch.object(tejun.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "ok", "")
            self.assertEqual(tejun.command(["fixture"]), "ok")
            self.assertEqual(run.call_args.kwargs["stdin"], subprocess.DEVNULL)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            prepared = {"output_dir": str(root / "reports"), "herdr": "herdr",
                        "workspace_id": "w1", "workspace": str(root),
                        "agent_dir": str(root), "path": "/fixture/bin", "input": str(root / "input.md"),
                        "pi_args": [], "provider": "openai", "model": "exact-id"}
            tab = {"workspace": {"workspace_id": "w1"},
                   "root_pane": {"pane_id": "w1:p99"}, "tab": {"tab_id": "w1:t99"}}
            with patch.object(tejun, "STATE", root / "state"), \
                 patch.object(tejun, "ensure_session", return_value=[]), \
                 patch.object(tejun, "herdr", return_value=tab) as herdr, \
                 patch.object(tejun.subprocess, "Popen") as popen, \
                 redirect_stdout(io.StringIO()) as output:
                tejun.launch({"name": "verify", "heading": "# Expected",
                              "prompt": "Write {output_path}"}, prepared)
                self.assertIn("completion is pending", output.getvalue())
                self.assertTrue(popen.call_args.kwargs["start_new_session"])
                self.assertEqual(popen.call_args.kwargs["stdin"], subprocess.DEVNULL)
                self.assertIn("--no-focus", herdr.call_args_list[0].args)
                self.assertEqual(herdr.call_args_list[1].args[1:3], ("agent", "start"))
                # Rejecting startup must fail in the caller before detachment
                # or a successful launch acknowledgement.
                popen.reset_mock()
                herdr.side_effect = [tab, tejun.TejunError("Pi startup rejected")]
                output.seek(0)
                output.truncate()
                with self.assertRaisesRegex(tejun.TejunError, "Pi startup rejected"):
                    tejun.launch({"name": "verify", "heading": "# Expected",
                                  "prompt": "Write {output_path}"}, prepared)
                popen.assert_not_called()
                self.assertNotIn("Launched", output.getvalue())
                statuses = [json.loads(path.read_text()) for path in
                            (root / "state/runs").glob("*/status.json")]
                self.assertTrue(any(s["state"] == "failed" and
                                    s.get("reason") == "Pi startup rejected" for s in statuses))

    def test_worker_requires_settled_state_and_exact_result_before_exit(self):
        for state, content, succeeds, cleanup_fails, pi_error in [
                ("done", "# Expected\n", True, False, None),
                ("blocked", "# Expected\n", False, False, None),
                ("done", "incorrect result\n", False, False, None),
                ("done", "# Expected\n", True, True, None),
                ("done", "# Expected\n", False, False, "Pi authentication failed.")]:
            with self.subTest(state=state, content=content, cleanup_fails=cleanup_fails, pi_error=pi_error), \
                 tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                partial, output = root / "result.partial.md", root / "result.md"
                partial.write_text(content)
                status = {"workflow": "verify", "state": "launching", "pane": "w1:p99",
                          "tab": "w1:t99", "partial": str(partial), "output": str(output)}
                request = {"herdr": "herdr", "name": "tejun-fixture", "pi_args": [],
                           "prompt": "fixture", "timeout": 10, "expected": "# Expected\n"}
                (root / "status.json").write_text(json.dumps(status))
                (root / "request.json").write_text(json.dumps(request))
                if pi_error:
                    (root / "pi-error.txt").write_text(pi_error)
                calls = []

                def herdr(binary, *args, **kwargs):
                    calls.append(args)
                    if args[:2] == ("agent", "get"):
                        return {"agent": {"agent_status": state}}
                    if args[:2] == ("pane", "list"):
                        return {"panes": [{"pane_id": "w1:p99", "tab_id": "w1:t99"}]}
                    if args[:2] == ("tab", "close") and cleanup_fails:
                        raise tejun.TejunError("cleanup rejected")
                    return {}

                with patch.object(tejun, "herdr", side_effect=herdr), redirect_stdout(io.StringIO()):
                    self.assertEqual(tejun.worker(root), 0 if succeeds else 1)
                final = json.loads((root / "status.json").read_text())
                self.assertEqual(final["state"], "success" if succeeds else "incomplete")
                self.assertEqual(output.exists(), succeeds)
                self.assertEqual(any(c[:2] == ("agent", "send-keys") for c in calls), succeeds)
                self.assertEqual(("tab", "close", "w1:t99") in calls, succeeds)
                if succeeds and not cleanup_fails:
                    self.assertTrue(final["tab_closed"])
                if cleanup_fails:
                    self.assertEqual(final["cleanup_error"], "cleanup rejected")
                if pi_error:
                    self.assertEqual(final["reason"], pi_error)

    def test_tab_cleanup_preserves_reused_tabs_and_reports_errors(self):
        status = {"pane": "w1:p99", "tab": "w1:t99"}
        own = {"pane_id": "w1:p99", "tab_id": "w1:t99"}
        for members in ([own, {"pane_id": "w1:p100", "tab_id": "w1:t99"}],
                        [{**own, "agent": "pi"}],
                        [{"pane_id": "w1:p100", "tab_id": "w1:t99"}]):
            with self.subTest(members=members), \
                 patch.object(tejun, "herdr", return_value={"panes": members}) as herdr:
                with self.assertRaisesRegex(tejun.TejunError, "changed or reused"):
                    tejun.close_finished_tab("herdr", status)
                self.assertEqual(herdr.call_count, 1)
        with patch.object(tejun, "herdr", return_value={"panes": []}) as herdr:
            tejun.close_finished_tab("herdr", status)
            self.assertEqual(herdr.call_count, 1)
        with patch.object(tejun, "herdr", side_effect=[{"panes": [own]},
                          tejun.TejunError("cleanup rejected")]):
            with self.assertRaisesRegex(tejun.TejunError, "cleanup rejected"):
                tejun.close_finished_tab("herdr", status)


if __name__ == "__main__":
    unittest.main()
