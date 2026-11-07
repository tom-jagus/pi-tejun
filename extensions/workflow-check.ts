import { rmSync, writeFileSync } from "node:fs";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

// Runs inside the workflow's existing Pi process. No catalogue or auth queries.
export default function (pi: ExtensionAPI) {
  const errorFile = process.env.TEJUN_ERROR_FILE!;
  const provider = process.env.TEJUN_EXPECTED_PROVIDER;
  const model = process.env.TEJUN_EXPECTED_MODEL;

  pi.on("input", (_event, ctx) => {
    if (provider && model && ctx.model?.provider === provider && ctx.model.id === model) {
      return { action: "continue" };
    }
    const selected = ctx.model ? `${ctx.model.provider}/${ctx.model.id}` : "none";
    const reason = `Expected exact model ${provider}/${model}; Pi selected ${selected}. Workflow not started.`;
    try {
      writeFileSync(errorFile, reason + "\n");
    } catch {
      // A diagnostic-write failure must not let a mismatched model run.
    }
    ctx.ui.notify(reason, "error");
    return { action: "handled" };
  });

  pi.on("message_end", (event) => {
    if (event.message.role !== "assistant") return;
    const message = event.message;
    if (message.stopReason === "error") {
      // Do not copy raw provider errors: they may include credential fragments.
      const authError = /auth|api.?key|credential|unauthorized|401|403/i.test(message.errorMessage ?? "");
      writeFileSync(errorFile, authError
        ? "Pi authentication failed or credentials are unavailable. See the retained Pi terminal.\n"
        : "Pi model request failed. See the retained Pi terminal for details.\n");
    } else if (message.stopReason === "aborted" || message.stopReason === "length") {
      writeFileSync(errorFile, `Pi response ended with ${message.stopReason}; work is incomplete.\n`);
    } else {
      // A successful response can follow Pi's own automatic recovery.
      rmSync(errorFile, { force: true });
    }
  });
}
