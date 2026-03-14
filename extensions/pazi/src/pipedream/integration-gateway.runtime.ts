import type { OpenClawConfig } from "openclaw/plugin-sdk";
import { callGateway } from "../../../../src/gateway/call.js";

type EmitIntegrationRequiredParams = {
  config: OpenClawConfig;
  app: string;
  message?: string;
};

export async function emitIntegrationRequired(params: EmitIntegrationRequiredParams) {
  return await callGateway({
    method: "pazi.integration.emit",
    params: {
      action: "required",
      app: params.app,
      message: params.message,
    },
    config: params.config,
  });
}
