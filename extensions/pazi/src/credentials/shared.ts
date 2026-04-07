import type {
  ApiKeyCredential,
  AuthProfileCredential,
  AuthProfileStore,
  TokenCredential,
} from "openclaw/plugin-sdk/agent-runtime";

// ── Types ──────────────────────────────────────────────────────

export type SavedCredentialType = "api_key" | "token";

export type SavedCredentialSummary = {
  profileId: string;
  service: string;
  type: SavedCredentialType;
  label: string;
  hasKey: boolean;
};

// ── Profile ID helpers ─────────────────────────────────────────

function slug(raw: string): string {
  return raw
    .trim()
    .toLowerCase()
    .replace(/[\s:]+/g, "-")
    .replace(/[^a-z0-9._@+\-]+/g, "-")
    .replace(/-{2,}/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function normalizeService(raw: unknown): string {
  return typeof raw === "string" ? slug(raw) : "";
}

export function normalizeLabel(raw: unknown): string {
  if (typeof raw !== "string" || !raw.trim()) return "default";
  return slug(raw);
}

export function buildProfileId(service: string, label?: string): string {
  const s = normalizeService(service) || service;
  const l = normalizeLabel(label);
  return `${s}:${l}`;
}

export function parseProfileId(
  profileId: string,
  fallbackService: string,
): { service: string; label: string } {
  const idx = profileId.indexOf(":");
  if (idx === -1) return { service: profileId || fallbackService, label: "default" };
  return {
    service: profileId.slice(0, idx) || fallbackService,
    label: profileId.slice(idx + 1) || "default",
  };
}

// ── Secret normalization ───────────────────────────────────────

/**
 * Strip line breaks and non-Latin1 code points from pasted secrets.
 * Mirrors src/utils/normalize-secret-input.ts without violating the
 * extension import boundary.
 */
export function normalizeSecretValue(value: unknown): string {
  if (typeof value !== "string") return "";
  const collapsed = value.replace(/[\r\n\u2028\u2029]+/g, "");
  let result = "";
  for (const char of collapsed) {
    const cp = char.codePointAt(0);
    if (typeof cp === "number" && cp <= 0xff) {
      result += char;
    }
  }
  return result.trim();
}

// ── Credential building ────────────────────────────────────────

export function buildCredential(params: {
  service: string;
  type: SavedCredentialType;
  key: string;
  metadata?: Record<string, string>;
}): ApiKeyCredential | TokenCredential {
  if (params.type === "api_key") {
    return {
      type: "api_key",
      provider: params.service,
      key: params.key,
      ...(params.metadata ? { metadata: params.metadata } : {}),
    };
  }
  const cred: TokenCredential = {
    type: "token",
    provider: params.service,
    token: params.key,
  };
  if (params.metadata?.email) {
    cred.email = params.metadata.email;
  }
  return cred;
}

// ── Summary helpers (never expose secrets) ─────────────────────

function isUserSavedCredential(
  cred: AuthProfileCredential,
): cred is ApiKeyCredential | TokenCredential {
  return cred.type === "api_key" || cred.type === "token";
}

function credentialHasKey(cred: ApiKeyCredential | TokenCredential): boolean {
  if (cred.type === "api_key") return Boolean(cred.key || cred.keyRef);
  return Boolean(cred.token || cred.tokenRef);
}

export function summarizeCredential(
  profileId: string,
  cred: ApiKeyCredential | TokenCredential,
): SavedCredentialSummary {
  const { service, label } = parseProfileId(profileId, cred.provider);
  return {
    profileId,
    service,
    type: cred.type,
    label,
    hasKey: credentialHasKey(cred),
  };
}

export function listCredentialSummaries(
  store: AuthProfileStore,
  serviceFilter?: string,
): SavedCredentialSummary[] {
  const normalized = serviceFilter ? normalizeService(serviceFilter) : undefined;
  const summaries: SavedCredentialSummary[] = [];
  for (const [id, cred] of Object.entries(store.profiles)) {
    if (!isUserSavedCredential(cred)) continue;
    if (normalized && normalizeService(cred.provider) !== normalized) continue;
    summaries.push(summarizeCredential(id, cred));
  }
  return summaries;
}

/**
 * Find a credential by service + optional label.
 *
 * Lookup order:
 * 1. If label provided: exact match `{service}:{label}`
 * 2. If no label: try `{service}:default`
 * 3. If no default: find all profiles for service — if exactly one, return it; else null
 */
export function findCredential(
  store: AuthProfileStore,
  service: string,
  label?: string,
): { profileId: string; credential: ApiKeyCredential | TokenCredential } | null {
  const svc = normalizeService(service);

  if (label) {
    const id = buildProfileId(svc, label);
    const cred = store.profiles[id];
    if (cred && isUserSavedCredential(cred)) return { profileId: id, credential: cred };
    return null;
  }

  const defaultId = buildProfileId(svc, "default");
  const defaultCred = store.profiles[defaultId];
  if (defaultCred && isUserSavedCredential(defaultCred)) {
    return { profileId: defaultId, credential: defaultCred };
  }

  const matches: Array<{ profileId: string; credential: ApiKeyCredential | TokenCredential }> = [];
  for (const [id, cred] of Object.entries(store.profiles)) {
    if (!isUserSavedCredential(cred)) continue;
    if (normalizeService(cred.provider) === svc) {
      matches.push({ profileId: id, credential: cred });
    }
  }
  if (matches.length === 1) return matches[0]!;
  return null;
}

export function listLabelsForService(store: AuthProfileStore, service: string): string[] {
  const svc = normalizeService(service);
  const labels: string[] = [];
  for (const [id, cred] of Object.entries(store.profiles)) {
    if (!isUserSavedCredential(cred)) continue;
    if (normalizeService(cred.provider) === svc) {
      labels.push(parseProfileId(id, cred.provider).label);
    }
  }
  return labels;
}

export function extractCredentialValue(
  cred: ApiKeyCredential | TokenCredential,
): string | undefined {
  return cred.type === "api_key" ? cred.key : cred.token;
}
