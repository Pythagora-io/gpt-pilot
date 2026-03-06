import { getProxyContext } from "../context.js";
import { resolveBrowserUseConfig } from "./config.js";

type ApiParams = {
  apiUrl: string;
  proxyToken: string;
  timeoutMs: number;
};

export type BrowserUseApiResult<T> = { ok: true; data: T } | { ok: false; error: string };

export type BrowserUseCreateSessionResponse = {
  sessionId: string;
  liveUrl?: string;
  status?: string;
  [key: string]: unknown;
};

export type BrowserUseSessionStatusResponse = {
  sessionId: string;
  liveUrl?: string;
  status?: string;
  [key: string]: unknown;
};

export type BrowserUseSnapshotResponse = {
  text: string;
  [key: string]: unknown;
};

export type BrowserUseScreenshotResponse = {
  url: string;
  [key: string]: unknown;
};

export type BrowserUseRunTaskResponse = {
  taskId: string;
  liveUrl?: string;
  status?: string;
  [key: string]: unknown;
};

export type BrowserUseTaskStatusResponse = {
  taskId: string;
  status: string;
  liveUrl?: string;
  result?: unknown;
  [key: string]: unknown;
};

export type BrowserUseStopSessionResponse = {
  ok?: boolean;
  status?: string;
  [key: string]: unknown;
};

function resolveApiParams(pluginConfig: Record<string, unknown> | null): ApiParams {
  const context = getProxyContext();
  if (!context) {
    throw new Error("No billing context set — workspace may not be initialized yet");
  }

  const resolved = resolveBrowserUseConfig({
    pluginConfig,
    env: process.env,
  });
  const apiUrl = resolved.browserUseApiUrl?.trim();
  if (!apiUrl) {
    throw new Error("Browser Use API URL not configured");
  }

  let baseUrl: URL;
  try {
    baseUrl = new URL(apiUrl);
  } catch {
    throw new Error(`Invalid Browser Use API URL: ${apiUrl}`);
  }

  return {
    apiUrl: baseUrl.toString(),
    proxyToken: context.proxyToken,
    timeoutMs: resolved.browserUseTimeoutMs,
  };
}

function buildEndpointUrl(baseApiUrl: string, endpointPath: string): URL {
  const url = new URL(baseApiUrl);
  const prefix = url.pathname.endsWith("/") ? url.pathname : `${url.pathname}/`;
  url.pathname = `${prefix}${endpointPath.replace(/^\/+/, "")}`;
  url.search = "";
  url.hash = "";
  return url;
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

async function parseResponse<T>(res: Response): Promise<BrowserUseApiResult<T>> {
  const payload = await readJsonBody(res);
  if (res.ok) {
    return { ok: true, data: payload as T };
  }
  const message = readErrorMessage(payload) ?? res.statusText ?? "Request failed";
  const status = res.status ? ` (${res.status})` : "";
  return { ok: false, error: `Pazi Browser Use API error${status}: ${message}` };
}

function withTimeoutSignal(
  timeoutMs: number,
  signal?: AbortSignal,
): {
  signal: AbortSignal;
  cleanup: () => void;
} {
  const controller = new AbortController();
  const timer = setTimeout(() => {
    controller.abort();
  }, timeoutMs);

  const onAbort = () => {
    controller.abort();
  };

  if (signal) {
    if (signal.aborted) {
      controller.abort();
    } else {
      signal.addEventListener("abort", onAbort, { once: true });
    }
  }

  return {
    signal: controller.signal,
    cleanup: () => {
      clearTimeout(timer);
      if (signal) {
        signal.removeEventListener("abort", onAbort);
      }
    },
  };
}

async function requestJson<T>(params: {
  apiParams: ApiParams;
  endpointPath: string;
  init?: RequestInit;
  signal?: AbortSignal;
}): Promise<BrowserUseApiResult<T>> {
  const url = buildEndpointUrl(params.apiParams.apiUrl, params.endpointPath);
  const headers = new Headers(params.init?.headers);
  headers.set("x-proxy-token", params.apiParams.proxyToken);
  const timeout = withTimeoutSignal(params.apiParams.timeoutMs, params.signal);

  try {
    const res = await fetch(url, {
      ...params.init,
      headers,
      signal: timeout.signal,
    });
    return await parseResponse<T>(res);
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      return {
        ok: false,
        error: `Pazi Browser Use API request timed out after ${String(params.apiParams.timeoutMs)}ms`,
      };
    }
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  } finally {
    timeout.cleanup();
  }
}

export async function createSession(
  params: {
    pluginConfig: Record<string, unknown> | null;
    body?: Record<string, unknown>;
  },
  signal?: AbortSignal,
): Promise<BrowserUseApiResult<BrowserUseCreateSessionResponse>> {
  try {
    const apiParams = resolveApiParams(params.pluginConfig);
    return await requestJson({
      apiParams,
      endpointPath: "session",
      init: {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params.body ?? {}),
      },
      signal,
    });
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

export async function getSessionStatus(
  params: {
    pluginConfig: Record<string, unknown> | null;
    sessionId: string;
  },
  signal?: AbortSignal,
): Promise<BrowserUseApiResult<BrowserUseSessionStatusResponse>> {
  try {
    const apiParams = resolveApiParams(params.pluginConfig);
    return await requestJson({
      apiParams,
      endpointPath: `session/${encodeURIComponent(params.sessionId)}`,
      signal,
    });
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

export async function getSnapshot(
  params: {
    pluginConfig: Record<string, unknown> | null;
    sessionId: string;
  },
  signal?: AbortSignal,
): Promise<BrowserUseApiResult<BrowserUseSnapshotResponse>> {
  try {
    const apiParams = resolveApiParams(params.pluginConfig);
    return await requestJson({
      apiParams,
      endpointPath: `session/${encodeURIComponent(params.sessionId)}/snapshot`,
      signal,
    });
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

export async function getScreenshot(
  params: {
    pluginConfig: Record<string, unknown> | null;
    sessionId: string;
  },
  signal?: AbortSignal,
): Promise<BrowserUseApiResult<BrowserUseScreenshotResponse>> {
  try {
    const apiParams = resolveApiParams(params.pluginConfig);
    return await requestJson({
      apiParams,
      endpointPath: `session/${encodeURIComponent(params.sessionId)}/screenshot`,
      signal,
    });
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

export async function runTask(
  params: {
    pluginConfig: Record<string, unknown> | null;
    body: {
      task: string;
      sessionId?: string;
    };
  },
  signal?: AbortSignal,
): Promise<BrowserUseApiResult<BrowserUseRunTaskResponse>> {
  try {
    const apiParams = resolveApiParams(params.pluginConfig);
    return await requestJson({
      apiParams,
      endpointPath: "task",
      init: {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params.body),
      },
      signal,
    });
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

export async function getTaskStatus(
  params: {
    pluginConfig: Record<string, unknown> | null;
    taskId: string;
  },
  signal?: AbortSignal,
): Promise<BrowserUseApiResult<BrowserUseTaskStatusResponse>> {
  try {
    const apiParams = resolveApiParams(params.pluginConfig);
    return await requestJson({
      apiParams,
      endpointPath: `task/${encodeURIComponent(params.taskId)}`,
      signal,
    });
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

export async function stopSession(
  params: {
    pluginConfig: Record<string, unknown> | null;
    sessionId: string;
  },
  signal?: AbortSignal,
): Promise<BrowserUseApiResult<BrowserUseStopSessionResponse>> {
  try {
    const apiParams = resolveApiParams(params.pluginConfig);
    return await requestJson({
      apiParams,
      endpointPath: `session/${encodeURIComponent(params.sessionId)}`,
      init: { method: "DELETE" },
      signal,
    });
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}
