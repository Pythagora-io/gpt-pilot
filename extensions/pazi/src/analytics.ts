import { resolvePaziBillingConfig } from "./config.js";
import { getProxyContext } from "./context.js";

export async function trackChannelConnected(
  pluginConfig: Record<string, unknown> | null,
  channelType: string,
  accountId: string,
): Promise<void> {
  try {
    const context = getProxyContext();
    if (!context) return;

    const resolved = resolvePaziBillingConfig({ pluginConfig, env: process.env });
    const apiUrl = resolved.apiUrl?.trim();
    if (!apiUrl) return;

    const url = new URL("/analytics/channel-connected", apiUrl);
    await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-proxy-token": context.proxyToken,
      },
      body: JSON.stringify({
        channel_type: channelType,
        account_id: accountId,
      }),
    });
  } catch {
    // Silently ignore — analytics must not break channel configuration
  }
}
