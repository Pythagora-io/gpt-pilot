import { resolvePaziBillingConfig } from "../config.js";
import { getProxyContext } from "../context.js";

export type UserActionApiResult<T> = { ok: true; data: T } | { ok: false; error: string };

type ApiParams = {
  apiUrl: string;
  proxyToken: string;
};

function resolveApiParams(pluginConfig: Record<string, unknown> | null): ApiParams {
  const context = getProxyContext();
  if (!context) {
    throw new Error("No billing context set — workspace may not be initialized yet");
  }

  const resolved = resolvePaziBillingConfig({ pluginConfig, env: process.env });
  const apiUrl = resolved.apiUrl?.trim();
  if (!apiUrl) {
    throw new Error("PAZI_API_URL not configured");
  }

  let baseUrl: URL;
  try {
    baseUrl = new URL(apiUrl);
  } catch {
    throw new Error(`Invalid PAZI_API_URL: ${apiUrl}`);
  }

  return { apiUrl: baseUrl.toString(), proxyToken: context.proxyToken };
}

async function fetchWithToken(params: ApiParams, url: URL, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  headers.set("x-proxy-token", params.proxyToken);
  return await fetch(url, { ...init, headers });
}

async function parseResponse<T>(res: Response): Promise<UserActionApiResult<T>> {
  const text = await res.text();
  const payload = text.trim() ? (JSON.parse(text) as unknown) : null;
  if (res.ok) {
    return { ok: true, data: payload as T };
  }
  const record = payload as { error?: string; message?: string } | null;
  const errMsg = record?.error ?? record?.message ?? res.statusText ?? "Request failed";
  return { ok: false, error: `Pazi API error (${res.status}): ${errMsg}` };
}

export interface UserActionResponse {
  request: {
    requestId: string;
    kind: "credentials" | "browser_login" | "browser_permission";
    status: "pending" | "completed" | "cancelled" | "expired";
    service: string;
    fields?: string[];
    url?: string;
    result?: {
      values?: Record<string, string>;
      confirmed?: true;
      reason?: string;
    };
  };
}

export async function createUserAction(
  pluginConfig: Record<string, unknown> | null,
  body: {
    kind: "credentials" | "browser_login" | "browser_permission" | "goal_confirmation";
    service: string;
    fields?: string[];
    url?: string;
    message?: string;
    proposal?: Record<string, unknown>;
  },
): Promise<UserActionApiResult<UserActionResponse>> {
  try {
    const params = resolveApiParams(pluginConfig);
    const url = new URL("/user-actions", params.apiUrl);
    const res = await fetchWithToken(params, url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return await parseResponse(res);
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

export async function getUserAction(
  pluginConfig: Record<string, unknown> | null,
  requestId: string,
): Promise<UserActionApiResult<UserActionResponse>> {
  try {
    const params = resolveApiParams(pluginConfig);
    const url = new URL(`/user-actions/${encodeURIComponent(requestId)}`, params.apiUrl);
    const res = await fetchWithToken(params, url);
    return await parseResponse(res);
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}
