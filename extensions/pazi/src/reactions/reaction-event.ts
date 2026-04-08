/**
 * HTTP handler for POST /pazi/reactions/event
 *
 * Called by the Pazi API when a user adds/removes a reaction in the web chat.
 * Enqueues a system event so the agent is notified.
 */
import type { IncomingMessage, ServerResponse } from "node:http";
import { enqueueSystemEvent } from "openclaw/plugin-sdk/infra-runtime";

interface ReactionEventBody {
  sessionKey: string;
  emoji: string;
  action: "added" | "removed";
}

function readJsonBody(req: IncomingMessage): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on("data", (chunk: Buffer) => chunks.push(chunk));
    req.on("end", () => {
      try {
        const body = JSON.parse(Buffer.concat(chunks).toString("utf-8")) as unknown;
        resolve(body);
      } catch (err) {
        reject(err);
      }
    });
    req.on("error", reject);
  });
}

export function createReactionEventHandler(deps: {
  configToken: string | undefined;
  logger: { warn: (msg: string) => void; info: (msg: string) => void };
}): (req: IncomingMessage, res: ServerResponse) => Promise<void> {
  return async (req, res) => {
    try {
      const body = (await readJsonBody(req)) as Partial<ReactionEventBody>;

      if (!body.sessionKey || !body.emoji || !body.action) {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "missing_fields" }));
        return;
      }

      const actionLabel = body.action === "added" ? "reacted with" : "removed reaction";
      const text = `User ${actionLabel} ${body.emoji} on a message`;

      enqueueSystemEvent(text, {
        sessionKey: body.sessionKey,
        contextKey: `web:reaction:${body.action}:${body.sessionKey}:${body.emoji}:${String(Date.now())}`,
      });

      deps.logger.info(`Reaction event enqueued: ${body.action} ${body.emoji}`);

      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ ok: true }));
    } catch (err) {
      deps.logger.warn(`Reaction event handler error: ${String(err)}`);
      res.writeHead(500, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "internal_error" }));
    }
  };
}
