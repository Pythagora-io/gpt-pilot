import type { OpenClawConfig } from "openclaw/plugin-sdk/provider-onboard";

export const PAZI_DEFAULT_IMAGE_MODEL_REF = "pazi/gpt-image-1.5";

/**
 * Set Pazi as the default image generation provider if no provider is configured yet.
 * This makes the `image_generate` tool visible to the agent.
 */
export function applyPaziImageConfig(cfg: OpenClawConfig): OpenClawConfig {
  if (cfg.agents?.defaults?.imageGenerationModel) {
    return cfg;
  }
  return {
    ...cfg,
    agents: {
      ...cfg.agents,
      defaults: {
        ...cfg.agents?.defaults,
        imageGenerationModel: {
          primary: PAZI_DEFAULT_IMAGE_MODEL_REF,
        },
      },
    },
  };
}
