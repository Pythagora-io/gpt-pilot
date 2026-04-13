const TASK_RE = /^agent:([^:]+):task:([^:]+)$/;
const MAIN_RE = /^agent:([^:]+):(?!task:)[^:]+$/;

export function buildDashboardConversationUrl(params: {
  dashboardBaseUrl?: string;
  sessionKey?: string;
}): string | null {
  const base = params.dashboardBaseUrl?.trim();
  const sessionKey = params.sessionKey?.trim();
  if (!base || !sessionKey) {
    return null;
  }

  const cleanBase = base.replace(/\/+$/, "");

  const taskMatch = TASK_RE.exec(sessionKey);
  if (taskMatch) {
    return `${cleanBase}/dashboard/agent/${encodeURIComponent(taskMatch[1])}/task/${encodeURIComponent(taskMatch[2])}`;
  }

  const mainMatch = MAIN_RE.exec(sessionKey);
  if (mainMatch) {
    return `${cleanBase}/dashboard/agent/${encodeURIComponent(mainMatch[1])}`;
  }

  return null;
}

/**
 * Build a dashboard URL that deep-links to the browser permission dialog.
 * The frontend reads the `enableBrowser` query param and shows
 * `BrowserPermissionRequestDialog` for the given request ID.
 */
export function buildBrowserPermissionUrl(
  dashboardBaseUrl: string | undefined,
  requestId: string,
): string | null {
  const base = dashboardBaseUrl?.trim();
  if (!base || !requestId) {
    return null;
  }

  const cleanBase = base.replace(/\/+$/, "");
  return `${cleanBase}/dashboard?enableBrowser=${encodeURIComponent(requestId)}`;
}
