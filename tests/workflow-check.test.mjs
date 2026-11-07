import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import register from "../extensions/workflow-check.ts";

test("workflow checks reject substitution and retain safe failure diagnostics", () => {
  const root = mkdtempSync(join(tmpdir(), "tejun-extension-"));
  const file = join(root, "error.txt");
  const keys = ["TEJUN_ERROR_FILE", "TEJUN_EXPECTED_PROVIDER", "TEJUN_EXPECTED_MODEL"];
  const previous = Object.fromEntries(keys.map((key) => [key, process.env[key]]));
  try {
    process.env.TEJUN_ERROR_FILE = file;
    process.env.TEJUN_EXPECTED_PROVIDER = "fixture";
    process.env.TEJUN_EXPECTED_MODEL = "exact";
    const handlers = new Map();
    const notices = [];
    register({ on: (event, handler) => handlers.set(event, handler) });
    const context = (model) => ({ model, ui: { notify: (...args) => notices.push(args) } });
    const input = handlers.get("input");
    assert.equal(input({}, context({ provider: "fixture", id: "exact" })).action, "continue");
    for (const selected of [undefined, { provider: "other", id: "exact" },
                            { provider: "fixture", id: "fuzzy-substitute" }]) {
      assert.equal(input({}, context(selected)).action, "handled");
      assert.match(readFileSync(file, "utf8"), /Expected exact model/);
    }
    assert.equal(notices.length, 3);
    const messageEnd = handlers.get("message_end");
    for (const [stopReason, errorMessage, expected] of [
      ["error", "401 invalid api_key SECRET_TOKEN", /authentication/],
      ["error", "provider error SECRET_TOKEN", /model request failed/],
      ["aborted", "SECRET_TOKEN", /aborted/],
      ["length", "SECRET_TOKEN", /length/],
    ]) {
      messageEnd({ message: { role: "assistant", stopReason, errorMessage } });
      const diagnostic = readFileSync(file, "utf8");
      assert.match(diagnostic, expected);
      assert.ok(!diagnostic.includes("SECRET_TOKEN"));
    }
    messageEnd({ message: { role: "user", stopReason: "stop" } });
    assert.ok(existsSync(file));
    messageEnd({ message: { role: "assistant", stopReason: "stop" } });
    assert.ok(!existsSync(file), "successful recovery clears an earlier error");
    process.env.TEJUN_ERROR_FILE = join(root, "missing-parent", "error.txt");
    const noFileHandlers = new Map();
    register({ on: (event, handler) => noFileHandlers.set(event, handler) });
    assert.equal(noFileHandlers.get("input")({}, context(undefined)).action, "handled",
                 "diagnostic-write failure must not let a mismatched model run");
  } finally {
    for (const key of keys) {
      if (previous[key] === undefined) delete process.env[key];
      else process.env[key] = previous[key];
    }
    rmSync(root, { recursive: true, force: true });
  }
});
