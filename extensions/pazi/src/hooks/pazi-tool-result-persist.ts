import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";

/**
 * Strip sensitive `details` from credential-bearing tool results before
 * transcript persistence. Covers ask_for_credentials, ask_for_browser_login,
 * save_credential, and get_credential.
 *
 * list_saved_credentials is intentionally NOT included — it never returns
 * secret values.
 */
const DETAILS_STRIPPED_TOOLS = new Set([
  "ask_for_credentials",
  "ask_for_browser_login",
  "save_credential",
  "get_credential",
]);

export function registerToolResultPersistHook(api: OpenClawPluginApi): void {
  api.on(
    "tool_result_persist",
    (event) => {
      if (!DETAILS_STRIPPED_TOOLS.has(event.toolName ?? "")) return;

      // Tool result messages carry `details` at runtime (AgentToolResult shape)
      // but the AgentMessage union type doesn't surface it statically.
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const msg = event.message as any;
      if (msg.details !== undefined) {
        const { details: _stripped, ...rest } = msg;
        return { message: rest };
      }
    },
    { priority: 10 },
  );
}
