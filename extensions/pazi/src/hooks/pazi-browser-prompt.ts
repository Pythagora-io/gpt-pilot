import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";
import { isBrowserEnabled } from "../context.js";

const BROWSER_DISABLED_GUIDANCE = [
  "## Browser Access",
  "Browser tools (`browser`, `web_search`, `web_fetch`, `browser_use`) are currently DISABLED for this workspace.",
  "If you need to browse the web, use the `request_browser_permission` tool to ask the user to enable it.",
  "The tool will return a dashboard URL — share it with the user so they can enable browsing from any device or channel.",
  "Do NOT attempt to call browser tools directly — they will be blocked.",
].join("\n");

/**
 * Register before_prompt_build hook that appends browser access guidance
 * to the system prompt when browsing is disabled.
 */
export function registerBrowserPromptHook(api: OpenClawPluginApi): void {
  api.on("before_prompt_build", () => {
    if (isBrowserEnabled()) {
      return; // Browsing enabled — no guidance needed
    }
    return {
      appendSystemContext: BROWSER_DISABLED_GUIDANCE,
    };
  });
}
