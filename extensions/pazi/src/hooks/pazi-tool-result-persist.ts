import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";

/**
 * Strip sensitive `details` from ask_for_credentials tool results before
 * transcript persistence.  The model has already consumed the credential
 * values during the active conversation — they must not be stored in
 * session history or exported transcripts.
 *
 * ask_for_browser_login doesn't carry sensitive details, but we strip
 * for consistency so no tool-result payloads leak into stored history.
 */
export function registerToolResultPersistHook(api: OpenClawPluginApi): void {
  api.on(
    "tool_result_persist",
    (event) => {
      if (event.toolName === "ask_for_credentials" || event.toolName === "ask_for_browser_login") {
        // Tool result messages carry `details` at runtime (AgentToolResult shape)
        // but the AgentMessage union type doesn't surface it statically.
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const msg = event.message as any;
        if (msg.details !== undefined) {
          const { details: _stripped, ...rest } = msg;
          return { message: rest };
        }
      }
    },
    { priority: 10 },
  );
}
