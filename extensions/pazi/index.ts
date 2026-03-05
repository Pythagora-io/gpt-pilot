import type { Server as HttpServer } from "node:http";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { resolvePaziBillingConfig } from "./src/config.js";
import { getProxyContext } from "./src/context.js";
import { createPipedreamTools } from "./src/pipedream/tools.js";
import { createPaziContextHandler } from "./src/proxy/pazi-context.js";
import { startPaziProxy } from "./src/proxy/pazi-proxy.js";
import { createPaziUploadHandler } from "./src/proxy/pazi-upload.js";

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

    const uploadHandler = createPaziUploadHandler({
      configToken: api.config.gateway?.auth?.token,
      env: process.env,
      logger: api.logger,
    });

    api.registerGatewayMethod("pazi.integration.emit", ({ params, respond, context }) => {
      context.broadcast("integration", params);
      respond(true, { emitted: true });
    });

    const tools = createPipedreamTools({
      pluginConfig,
      config: api.config,
    });
    for (const tool of tools) {
      api.registerTool(tool);
    }

    api.registerHttpRoute({
      path: "/pazi/context",
      auth: "gateway",
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

    api.registerHttpRoute({
      path: "/health",
      handler: (_req, res) => {
        res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
        res.end(JSON.stringify({ status: "ok", timestamp: new Date().toISOString() }));
      },
    });

    api.registerHttpRoute({
      path: "/status",
      handler: (_req, res) => {
        res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
        res.end(
          JSON.stringify({
            status: "running",
            busy: getProxyContext() !== null,
            version: process.env.AGENT_VERSION ?? "unknown",
            environment: process.env.NODE_ENV ?? "development",
          }),
        );
      },
    });

    api.registerHttpRoute({
      path: "/pazi/upload",
      auth: "gateway",
      handler: async (req, res) => {
        if (req.method !== "POST") {
          res.statusCode = 404;
          res.setHeader("Content-Type", "text/plain; charset=utf-8");
          res.end("Not Found");
          return;
        }
        await uploadHandler(req, res);
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
