import http from "node:http";
import https from "node:https";
import type { IncomingHttpHeaders } from "node:http";
import { createSubsystemLogger } from "../logging/subsystem.js";

type ProxyContext = { userId: string; proxyToken: string };

type HttpRequest = typeof http.request;

type ProxyError = { error: string; message?: string };

const log = createSubsystemLogger("gateway/pazi-proxy");

let currentContext: ProxyContext | null = null;

export function setProxyContext(ctx: ProxyContext): void {
  currentContext = ctx;
}

export function clearProxyContext(): void {
  currentContext = null;
}

function requestForUrl(url: URL): HttpRequest {
  return url.protocol === "https:" ? https.request : http.request;
}

function pickAnthropicHeaders(incoming: IncomingHttpHeaders): Record<string, string> {
  const forward: Record<string, string> = {};
  const passthrough = ["anthropic-version", "anthropic-beta", "accept", "content-type"] as const;
  for (const key of passthrough) {
    const value = incoming[key];
    if (typeof value === "string") {
      forward[key] = value;
    }
  }
  return forward;
}

function writeJson(res: http.ServerResponse, status: number, body: ProxyError) {
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(body));
}

export async function startPaziProxy(port: number): Promise<void> {
  const paziApiUrl = process.env.PAZI_API_URL;
  if (!paziApiUrl) {
    log.info("pazi proxy disabled (PAZI_API_URL not set)");
    return;
  }

  const server = http.createServer(async (req, res) => {
    if (req.method !== "POST" || !req.url?.startsWith("/v1/messages")) {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Not Found");
      return;
    }

    const context = currentContext;
    if (!context) {
      writeJson(res, 503, { error: "no billing context set" });
      return;
    }

    const chunks: Buffer[] = [];
    for await (const chunk of req) {
      if (typeof chunk === "string") {
        chunks.push(Buffer.from(chunk));
      } else {
        chunks.push(chunk);
      }
    }
    const body = Buffer.concat(chunks);

    const target = new URL("/anthropic/v1/messages", paziApiUrl);
    const doRequest = requestForUrl(target);

    const proxyReq = doRequest(
      target,
      {
        method: "POST",
        headers: {
          ...pickAnthropicHeaders(req.headers),
          "X-Proxy-Token": context.proxyToken,
          "X-User-Id": context.userId,
        },
      },
      (proxyRes) => {
        res.writeHead(proxyRes.statusCode || 500, proxyRes.headers);
        proxyRes.pipe(res);
      },
    );

    proxyReq.on("error", (err: Error) => {
      log.warn(`pazi proxy error: ${String(err)}`);
      if (!res.headersSent) {
        writeJson(res, 502, { error: "proxy_error", message: err.message });
      }
    });

    proxyReq.write(body);
    proxyReq.end();
  });

  server.on("clientError", (err, socket) => {
    log.warn(`pazi proxy client error: ${String(err)}`);
    socket.end("HTTP/1.1 400 Bad Request\r\n\r\n");
  });

  server.listen(port, "127.0.0.1", () => {
    log.info(`pazi proxy listening on 127.0.0.1:${port}`);
  });
}
