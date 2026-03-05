import { resolvePaziBillingConfig } from "../config.js";
import { getProxyContext } from "../context.js";

type ApiParams = {
  apiUrl: string;
  proxyToken: string;
};

export type PipedreamApiResult<T> = { ok: true; data: T } | { ok: false; error: string };

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

function readErrorMessage(payload: unknown): string | undefined {
  if (!payload) {
    return undefined;
  }
  if (typeof payload === "string") {
    return payload;
  }
  if (typeof payload === "object") {
    const record = payload as { error?: unknown; message?: unknown };
    if (typeof record.error === "string") {
      return record.error;
    }
    if (typeof record.message === "string") {
      return record.message;
    }
  }
  return undefined;
}

async function readJsonBody(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text.trim()) {
    return null;
  }
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

async function parseResponse<T>(res: Response): Promise<PipedreamApiResult<T>> {
  const payload = await readJsonBody(res);
  if (res.ok) {
    return { ok: true, data: payload as T };
  }
  const message = readErrorMessage(payload) ?? res.statusText ?? "Request failed";
  const status = res.status ? ` (${res.status})` : "";
  return { ok: false, error: `Pazi API error${status}: ${message}` };
}

async function fetchWithToken(params: ApiParams, url: URL, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  headers.set("x-proxy-token", params.proxyToken);
  return await fetch(url, { ...init, headers });
}

async function requestJson<T>(
  params: ApiParams,
  url: URL,
  init?: RequestInit,
): Promise<PipedreamApiResult<T>> {
  const res = await fetchWithToken(params, url, init);
  return await parseResponse<T>(res);
}

function coerceLimit(limit?: number): number | undefined {
  if (typeof limit !== "number" || !Number.isFinite(limit) || limit <= 0) {
    return undefined;
  }
  return Math.floor(limit);
}

export async function searchApps(
  params: { pluginConfig: Record<string, unknown> | null },
  query: string,
  limit?: number,
): Promise<PipedreamApiResult<unknown>> {
  try {
    const apiParams = resolveApiParams(params.pluginConfig);
    const url = new URL("/integrations/apps", apiParams.apiUrl);
    url.searchParams.set("q", query);
    const resolvedLimit = coerceLimit(limit);
    if (resolvedLimit) {
      url.searchParams.set("limit", String(resolvedLimit));
    }
    return await requestJson(apiParams, url);
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

export async function listActions(
  params: { pluginConfig: Record<string, unknown> | null },
  app: string,
  limit?: number,
): Promise<PipedreamApiResult<unknown>> {
  try {
    const apiParams = resolveApiParams(params.pluginConfig);
    const url = new URL(`/integrations/${encodeURIComponent(app)}/actions`, apiParams.apiUrl);
    const resolvedLimit = coerceLimit(limit);
    if (resolvedLimit) {
      url.searchParams.set("limit", String(resolvedLimit));
    }
    return await requestJson(apiParams, url);
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

export async function getAction(
  params: { pluginConfig: Record<string, unknown> | null },
  actionId: string,
): Promise<PipedreamApiResult<unknown>> {
  try {
    const apiParams = resolveApiParams(params.pluginConfig);
    const url = new URL(`/integrations/actions/${encodeURIComponent(actionId)}`, apiParams.apiUrl);
    return await requestJson(apiParams, url);
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

export async function configureActionProp(
  params: { pluginConfig: Record<string, unknown> | null },
  actionId: string,
  body: {
    propName: string;
    configuredProps?: Record<string, unknown>;
    query?: string;
    page?: number;
    prevContext?: Record<string, unknown>;
    dynamicPropsId?: string;
  },
): Promise<PipedreamApiResult<unknown>> {
  try {
    const apiParams = resolveApiParams(params.pluginConfig);
    const url = new URL(
      `/integrations/actions/${encodeURIComponent(actionId)}/configure-prop`,
      apiParams.apiUrl,
    );
    return await requestJson(apiParams, url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

export async function reloadActionProps(
  params: { pluginConfig: Record<string, unknown> | null },
  actionId: string,
  body: { configuredProps?: Record<string, unknown>; dynamicPropsId?: string },
): Promise<PipedreamApiResult<unknown>> {
  try {
    const apiParams = resolveApiParams(params.pluginConfig);
    const url = new URL(
      `/integrations/actions/${encodeURIComponent(actionId)}/reload-props`,
      apiParams.apiUrl,
    );
    return await requestJson(apiParams, url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

export async function checkIntegration(
  params: { pluginConfig: Record<string, unknown> | null },
  app: string,
): Promise<PipedreamApiResult<unknown>> {
  try {
    const apiParams = resolveApiParams(params.pluginConfig);
    const url = new URL(`/integrations/accounts/${encodeURIComponent(app)}`, apiParams.apiUrl);
    const res = await fetchWithToken(apiParams, url, { method: "GET" });
    if (res.status === 404) {
      return { ok: true, data: { connected: false } };
    }
    return await parseResponse(res);
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

export async function runAction(
  params: { pluginConfig: Record<string, unknown> | null },
  app: string,
  actionId: string,
  configuredProps?: Record<string, unknown>,
): Promise<PipedreamApiResult<unknown>> {
  try {
    const apiParams = resolveApiParams(params.pluginConfig);
    const url = new URL(`/integrations/${encodeURIComponent(app)}/action`, apiParams.apiUrl);
    const body: { actionId: string; configuredProps?: Record<string, unknown> } = { actionId };
    if (configuredProps) {
      body.configuredProps = configuredProps;
    }
    return await requestJson(apiParams, url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}
