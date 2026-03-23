/**
 * Sets a sentinel BRAVE_API_KEY environment variable so the agent's web_search
 * tool activates Brave Search support without needing a real API key.
 *
 * The actual API key is stored on the backend and injected by the Brave proxy.
 * The sentinel value just ensures the tool doesn't skip Brave search due to
 * a missing key.
 */

export const BRAVE_PROXY_SENTINEL = "pazi-proxy";

let previousValue: string | undefined;
let installed = false;

/**
 * Set BRAVE_API_KEY to a sentinel value if not already set.
 * Saves the previous value for restoration on uninstall.
 */
export function installBraveEnvDefaults(): void {
  if (installed) {
    return;
  }
  installed = true;
  previousValue = process.env.BRAVE_API_KEY;
  if (!process.env.BRAVE_API_KEY) {
    process.env.BRAVE_API_KEY = BRAVE_PROXY_SENTINEL;
  }
}

/**
 * Restore the original BRAVE_API_KEY value (or remove it if it wasn't set).
 */
export function uninstallBraveEnvDefaults(): void {
  if (!installed) {
    return;
  }
  installed = false;
  if (previousValue === undefined) {
    delete process.env.BRAVE_API_KEY;
  } else {
    process.env.BRAVE_API_KEY = previousValue;
  }
  previousValue = undefined;
}
