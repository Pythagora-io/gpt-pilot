import type { Server as HttpServer } from "node:http";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { resolvePaziBillingConfig } from "./src/config.js";
import { createPaziContextHandler } from "./src/pazi-context.js";
import { startPaziProxy } from "./src/pazi-proxy.js";

function normalizePluginConfig(
  value: OpenClawPluginApi["pluginConfig"],
): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

async function stopServer(server: HttpServer, logger: OpenClawPluginApi["logger"]) {
  await new Promise<void>((resolve) => {
    server.close((err) => {
      if (err) {
        logger.warn(`pazi proxy shutdown failed: ${String(err)}`);
      }
      resolve();
    });
  });
}

export default {
  id: "pazi",
  name: "Pazi Proxy",
  description: "Routes Anthropic calls through the Pazi API.",
  register(api: OpenClawPluginApi) {
    const pluginConfig = normalizePluginConfig(api.pluginConfig);
    const contextHandler = createPaziContextHandler({
      configToken: api.config.gateway?.auth?.token,
      env: process.env,
      logger: api.logger,
    });

    api.registerHttpRoute({
      path: "/pazi/context",
      handler: async (req, res) => {
        if (req.method !== "POST") {
          res.statusCode = 404;
          res.setHeader("Content-Type", "text/plain; charset=utf-8");
          res.end("Not Found");
          return;
        }
        await contextHandler(req, res);
      },
    });

    let proxyServer: HttpServer | null = null;

    api.registerService({
      id: "pazi-proxy",
      start: async () => {
        const resolved = resolvePaziBillingConfig({
          pluginConfig,
          env: process.env,
        });
        proxyServer = await startPaziProxy({
          apiUrl: resolved.apiUrl,
          port: resolved.proxyPort,
          logger: api.logger,
        });
      },
      stop: async () => {
        if (!proxyServer) {
          return;
        }
        await stopServer(proxyServer, api.logger);
        proxyServer = null;
      },
    });
  },
};
