import { appendFileSync } from "node:fs";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  const allowed = ["read", "web_search"];
  let ready = false;
  const lifecycle = (key: string, ctx: ExtensionContext) => appendFileSync(
    process.env.TEJUN_CHILDREN_FILE! + ".search.jsonl",
    JSON.stringify({ [key]: ctx.sessionManager.getSessionId(), at: Date.now() }) + "\n",
    { mode: 0o600 });
  pi.on("session_start", (_event, ctx) => lifecycle("child_started", ctx));
  pi.on("session_shutdown", (_event, ctx) => lifecycle("child_finished", ctx));
  pi.on("before_agent_start", () => {
    ready = allowed.every(name => pi.getAllTools().some(tool => tool.name === name));
    pi.setActiveTools(ready ? allowed : []);
    appendFileSync(process.env.TEJUN_CHILDREN_FILE! + ".search.jsonl",
      JSON.stringify({ ready, tools: pi.getActiveTools() }) + "\n", { mode: 0o600 });
    if (!ready) throw new Error("Research child requires read and web_search.");
  });
  pi.on("tool_result", event => {
    if (event.toolName === "web_search")
      appendFileSync(process.env.TEJUN_CHILDREN_FILE! + ".search.jsonl",
        JSON.stringify({ search: event.isError || (event.details as any)?.error
          ? "failed" : "succeeded" }) + "\n", { mode: 0o600 });
  });
  pi.on("tool_call", event => {
    if (!ready || !allowed.includes(event.toolName))
      return { block: true, reason: "Research child permits only read and web_search." };
  });
}
