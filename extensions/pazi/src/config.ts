export type PaziBillingConfig = {
  apiUrl?: string;
  proxyPort: number;
};

const DEFAULT_PROXY_PORT = 8765;

function normalizeString(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function normalizePort(value: unknown): number | undefined {
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

export function resolvePaziBillingConfig(params: {
  pluginConfig?: Record<string, unknown> | null;
  env?: NodeJS.ProcessEnv;
}): PaziBillingConfig {
  const env = params.env ?? process.env;
  const raw = params.pluginConfig ?? {};

  const apiUrl =
    normalizeString(raw.apiUrl) ??
    normalizeString(env.PAZI_API_URL);

  const proxyPort =
    normalizePort(raw.proxyPort) ??
    normalizePort(env.PAZI_PROXY_PORT) ??
    DEFAULT_PROXY_PORT;

  return {
    apiUrl,
    proxyPort,
  };
}

export function resolveGatewayToken(params: {
  configToken?: string;
  env?: NodeJS.ProcessEnv;
}): string | undefined {
  const configToken = normalizeString(params.configToken);
  if (configToken) {
    return configToken;
  }
  const env = params.env ?? process.env;
  return normalizeString(env.OPENCLAW_GATEWAY_TOKEN);
}
