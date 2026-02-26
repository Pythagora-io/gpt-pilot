import http from "node:http";
import https from "node:https";
import type { IncomingHttpHeaders } from "node:http";
import { getProxyContext } from "./context.js";

type ProxyLogger = {
  info: (message: string) => void;
  warn: (message: string) => void;
};

type ProxyServer = http.Server;

type HttpRequest = typeof http.request;

type ProxyError = { error: string; message?: string };

type StartProxyParams = {
  apiUrl?: string;
  port: number;
  logger: ProxyLogger;
};

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

export async function startPaziProxy(params: StartProxyParams): Promise<ProxyServer | null> {
  const apiUrl = params.apiUrl?.trim();
  if (!apiUrl) {
    params.logger.info("pazi proxy disabled (PAZI_API_URL not set)");
    return null;
  }

  let baseUrl: URL;
  try {
    baseUrl = new URL(apiUrl);
  } catch {
    params.logger.warn(`pazi proxy disabled (invalid PAZI_API_URL: ${apiUrl})`);
    return null;
  }

  const server = http.createServer(async (req, res) => {
    if (req.method !== "POST" || !req.url?.startsWith("/v1/messages")) {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Not Found");
      return;
    }

    const context = getProxyContext();
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

    const target = new URL("/anthropic/v1/messages", baseUrl);
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
      params.logger.warn(`pazi proxy error: ${String(err)}`);
      if (!res.headersSent) {
        writeJson(res, 502, { error: "proxy_error", message: err.message });
      }
    });

    proxyReq.write(body);
    proxyReq.end();
  });

  server.on("clientError", (err, socket) => {
    params.logger.warn(`pazi proxy client error: ${String(err)}`);
    socket.end("HTTP/1.1 400 Bad Request\r\n\r\n");
  });

  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(params.port, "127.0.0.1", () => {
      server.off("error", reject);
      resolve();
    });
  });

  params.logger.info(`pazi proxy listening on 127.0.0.1:${params.port}`);
  return server;
}
