import type { OpenClawConfig } from "openclaw/plugin-sdk/provider-onboard";

export const HEARTBEAT_SAFE_DEFAULTS = {
  model: "anthropic/claude-haiku-4-5",
  lightContext: true,
  isolatedSession: true,
} as const;

/**
 * PAZ-300: Fill in cost-safe heartbeat defaults for any missing fields.
 * Fields that are already set (including explicit `false`) are preserved.
 * Returns the config unchanged if all fields are already present.
 */
export function applyHeartbeatDefaults(cfg: OpenClawConfig): OpenClawConfig {
  const heartbeat = cfg.agents?.defaults?.heartbeat as Record<string, unknown> | undefined;

  const needsModel = heartbeat?.model === undefined;
  const needsLightContext = heartbeat?.lightContext === undefined;
  const needsIsolatedSession = heartbeat?.isolatedSession === undefined;

  if (!needsModel && !needsLightContext && !needsIsolatedSession) {
    return cfg;
  }

  const patched = {
    ...heartbeat,
    ...(needsModel ? { model: HEARTBEAT_SAFE_DEFAULTS.model } : {}),
    ...(needsLightContext ? { lightContext: HEARTBEAT_SAFE_DEFAULTS.lightContext } : {}),
    ...(needsIsolatedSession ? { isolatedSession: HEARTBEAT_SAFE_DEFAULTS.isolatedSession } : {}),
  };

  return {
    ...cfg,
    agents: {
      ...cfg.agents,
      defaults: {
        ...cfg.agents?.defaults,
        heartbeat: patched,
      },
    },
  };
}
