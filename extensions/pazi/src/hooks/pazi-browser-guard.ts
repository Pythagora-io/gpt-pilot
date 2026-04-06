import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";
import { BROWSER_TOOL_NAMES } from "../browser-permission/constants.js";
import { isBrowserEnabled } from "../context.js";

/**
 * Register before_tool_call hook that blocks browser-related tools
 * when browsing is disabled for the workspace.
 */
export function registerBrowserGuardHook(api: OpenClawPluginApi): void {
  api.on(
    "before_tool_call",
    (event) => {
      if (!BROWSER_TOOL_NAMES.has(event.toolName)) {
        return; // Not a browser tool — allow
      }
      if (isBrowserEnabled()) {
        return; // Browsing enabled — allow
      }
      return {
        block: true,
        blockReason:
          "Web browsing is disabled for this workspace. " +
          "Use the request_browser_permission tool to ask the user to enable it.",
      };
    },
    { priority: 10 },
  );
}
