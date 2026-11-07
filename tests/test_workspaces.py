"""Workflow workspace allocation, busy rejection, and cross-process reservation."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from test_isolation import prepared, workflow
from test_tejun import ROOT, tejun


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.status = {}
        self.created = {"workspace": {"workspace_id": "w7"},
                        "tab": {"tab_id": "w7:t8"}, "root_pane": {"pane_id": "w7:p9"}}

    def reserve(self):
        return tejun.reserve_workflow_tab(workflow(), prepared(self.root), self.root, self.status)

    def test_creates_named_workspace_and_uses_its_default_tab(self):
        with patch.object(tejun, "STATE", self.root / "state"), \
             patch.object(tejun, "ensure_session", return_value=[
                 {"workspace_id": "w1", "label": "tejun"}]), \
             patch.object(tejun, "herdr", return_value=self.created) as herdr:
            self.reserve()
        self.assertEqual(herdr.call_count, 1)
        args = herdr.call_args.args
        self.assertEqual(args[:5], ("fixture", "workspace", "create", "--label", "fixture"))
        self.assertIn("--no-focus", args)
        self.assertIn("PI_CODING_AGENT_DIR=" + str(self.root / "agent"), args)
        self.assertIn("TEJUN_EXPECTED_MODEL=exact", args)
        self.assertEqual(self.status, {"workspace_id": "w7", "tab": "w7:t8", "pane": "w7:p9"})
        self.assertEqual(json.loads((self.root / "status.json").read_text()), self.status)

    def test_reuses_empty_workspace_without_naming_the_tab(self):
        with patch.object(tejun, "STATE", self.root / "state"), \
             patch.object(tejun, "ensure_session", return_value=[
                 {"workspace_id": "w7", "label": "fixture"}]), \
             patch.object(tejun, "herdr", side_effect=[{"tabs": []}, self.created]) as herdr:
            self.reserve()
        self.assertEqual(herdr.call_args_list[0].args,
                         ("fixture", "tab", "list", "--workspace", "w7"))
        args = herdr.call_args.args
        self.assertEqual(args[:5], ("fixture", "tab", "create", "--workspace", "w7"))
        self.assertNotIn("--label", args)

    def test_any_existing_tab_blocks_reuse_including_retained_or_unrelated_work(self):
        for tab in ({"tab_id": "w7:t1", "agent_status": "working"},
                    {"tab_id": "w7:t1", "agent_status": "done"},
                    {"tab_id": "w7:t1", "label": "user notes"}):
            with self.subTest(tab=tab), patch.object(tejun, "STATE", self.root / "state"), \
                 patch.object(tejun, "ensure_session", return_value=[
                     {"workspace_id": "w7", "label": "fixture"}]), \
                 patch.object(tejun, "herdr", return_value={"tabs": [tab]}) as herdr:
                with self.assertRaisesRegex(tejun.TejunError, "still has tabs"):
                    self.reserve()
                self.assertEqual(herdr.call_count, 1)
                self.assertEqual(self.status, {})

    def test_duplicate_workspace_labels_are_rejected_without_touching_either(self):
        with patch.object(tejun, "STATE", self.root / "state"), \
             patch.object(tejun, "ensure_session", return_value=[
                 {"workspace_id": "w1", "label": "fixture"},
                 {"workspace_id": "w2", "label": "fixture"}]), \
             patch.object(tejun, "herdr") as herdr:
            with self.assertRaisesRegex(tejun.TejunError, "Multiple workspaces"):
                self.reserve()
            herdr.assert_not_called()

    def test_failed_allocation_releases_the_short_lived_lock(self):
        with patch.object(tejun, "STATE", self.root / "state"), \
             patch.object(tejun, "ensure_session", return_value=[]), \
             patch.object(tejun, "herdr", side_effect=[tejun.TejunError("rejected"), self.created]):
            with self.assertRaisesRegex(tejun.TejunError, "rejected"):
                self.reserve()
            self.reserve()
        self.assertEqual(self.status["workspace_id"], "w7")

    def test_simultaneous_launchers_cannot_both_reserve_the_same_workflow(self):
        script = self.root / "contender.py"
        script.write_text(
            "import importlib.util,pathlib,sys,time\n"
            f"spec=importlib.util.spec_from_file_location('tejun',{str(ROOT / 'tejun.py')!r})\n"
            "t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)\n"
            f"root=pathlib.Path({str(self.root)!r});t.STATE=root/'state'\n"
            "run=root/sys.argv[1];run.mkdir()\n"
            "t.ensure_session=lambda *args: []\n"
            "def create(*args,**kwargs):\n"
            " (root/'ready').write_text('ready')\n"
            " deadline=time.monotonic()+5\n"
            " while not (root/'release').exists():\n"
            "  if time.monotonic()>deadline: raise RuntimeError('fixture gate timeout')\n"
            "  time.sleep(.01)\n"
            " return {'workspace':{'workspace_id':'w1'},'tab':{'tab_id':'w1:t1'},"
            "'root_pane':{'pane_id':'w1:p1'}}\n"
            "t.herdr=create\n"
            "p={'herdr':'fixture','workspace':str(root),'agent_dir':str(root),"
            "'path':'/bin','provider':'fixture','model':'exact'}\n"
            "try:\n"
            " t.reserve_workflow_tab({'name':'fixture'},p,run,{});answer='reserved'\n"
            "except t.TejunError as e: answer=str(e)\n"
            "(run/'answer').write_text(answer)\n")
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        first = subprocess.Popen([sys.executable, str(script), "first"], env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 5
            while not (self.root / "ready").exists():
                if first.poll() is not None or time.monotonic() > deadline:
                    self.fail("first contender did not reach reservation gate")
                time.sleep(.01)
            second = subprocess.run([sys.executable, str(script), "second"], env=env,
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("already starting", (self.root / "second/answer").read_text())
            (self.root / "release").write_text("release")
            out, err = first.communicate(timeout=5)
            self.assertEqual(first.returncode, 0, (out, err))
            self.assertEqual((self.root / "first/answer").read_text(), "reserved")
        finally:
            if first.poll() is None:
                first.kill()
                first.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()
