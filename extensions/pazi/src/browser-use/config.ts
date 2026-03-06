import { resolvePaziBillingConfig } from "../config.js";

export type BrowserUseConfig = {
  browserUseEnabled: boolean;
  browserUseApiUrl?: string;
  browserUseTimeoutMs: number;
};

const DEFAULT_BROWSER_USE_TIMEOUT_MS = 120_000;

function normalizeString(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function normalizeNumber(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value) && value > 0) {
    return Math.floor(value);
  }
  if (typeof value === "string" && value.trim().length > 0) {
    const parsed = Number.parseInt(value, 10);
    if (Number.isFinite(parsed) && parsed > 0) {
      return parsed;
    }
  }
  return undefined;
}

function normalizeBoolean(value: unknown): boolean | undefined {
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (["1", "true", "yes", "on"].includes(normalized)) {
      return true;
    }
    if (["0", "false", "no", "off"].includes(normalized)) {
      return false;
    }
  }
  return undefined;
}

function withBrowserUsePath(baseUrl: string): string {
  try {
    const url = new URL(baseUrl);
    const normalizedPath = url.pathname.replace(/\/+$/, "");
    if (normalizedPath.endsWith("/browser-use")) {
      url.pathname = normalizedPath;
    } else if (normalizedPath.length === 0 || normalizedPath === "/") {
      url.pathname = "/browser-use";
    } else {
      url.pathname = `${normalizedPath}/browser-use`;
    }
    return url.toString();
  } catch {
    return baseUrl;
  }
}

export function resolveBrowserUseConfig(params: {
  pluginConfig?: Record<string, unknown> | null;
  env?: NodeJS.ProcessEnv;
}): BrowserUseConfig {
  const env = params.env ?? process.env;
  const raw = params.pluginConfig ?? {};

  const browserUseEnabled =
    normalizeBoolean(raw.browserUseEnabled) ?? normalizeBoolean(env.BROWSER_USE_ENABLED) ?? false;

  const browserUseTimeoutMs =
    normalizeNumber(raw.browserUseTimeoutMs) ??
    normalizeNumber(env.BROWSER_USE_TIMEOUT_MS) ??
    DEFAULT_BROWSER_USE_TIMEOUT_MS;

  const billingConfig = resolvePaziBillingConfig({
    pluginConfig: params.pluginConfig,
    env,
  });

  const browserUseApiBase =
    normalizeString(env.BROWSER_USE_API_URL) ?? normalizeString(billingConfig.apiUrl);

  return {
    browserUseEnabled,
    browserUseApiUrl: browserUseApiBase ? withBrowserUsePath(browserUseApiBase) : undefined,
    browserUseTimeoutMs,
  };
}
