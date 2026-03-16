import { existsSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import type { IncomingMessage, ServerResponse } from "node:http";
import { homedir } from "node:os";
import { join, extname, basename } from "node:path";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { resolveGatewayToken } from "../config.js";

type UploadFile = {
  name: string;
  content: string; // base64
  mimeType: string;
};

type UploadBody = {
  files?: UploadFile[];
};

type UploadHandlerDeps = {
  configToken?: string;
  env?: NodeJS.ProcessEnv;
  logger: OpenClawPluginApi["logger"];
};

function writeJson(res: ServerResponse, status: number, body: unknown) {
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(body));
}

async function readJsonBody(req: IncomingMessage): Promise<UploadBody | null> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) {
    if (typeof chunk === "string") {
      chunks.push(Buffer.from(chunk));
    } else {
      chunks.push(chunk);
    }
  }
  try {
    const parsed = JSON.parse(Buffer.concat(chunks).toString());
    if (parsed && typeof parsed === "object") {
      return parsed as UploadBody;
    }
  } catch {
    return null;
  }
  return null;
}

/** Resolve a unique path, appending -1, -2, etc. on collision. */
function uniquePath(dir: string, name: string): string {
  const ext = extname(name);
  const base = basename(name, ext);
  let candidate = join(dir, name);
  let counter = 0;
  while (existsSync(candidate)) {
    counter++;
    candidate = join(dir, `${base}-${String(counter)}${ext}`);
  }
  return candidate;
}

export function createPaziUploadHandler(deps: UploadHandlerDeps) {
  return async (req: IncomingMessage, res: ServerResponse): Promise<void> => {
    const gatewayToken = resolveGatewayToken({
      configToken: deps.configToken,
      env: deps.env,
    });
    if (!gatewayToken) {
      deps.logger.warn("pazi upload request rejected: gateway token missing");
      writeJson(res, 500, { error: "gateway_token_missing" });
      return;
    }

    const authHeader = req.headers.authorization;
    if (authHeader !== `Bearer ${gatewayToken}`) {
      writeJson(res, 401, { error: "unauthorized" });
      return;
    }

    const body = await readJsonBody(req);
    if (!body) {
      writeJson(res, 400, { error: "invalid JSON" });
      return;
    }

    const { files } = body;
    if (!Array.isArray(files) || files.length === 0) {
      writeJson(res, 400, { error: "no files provided" });
      return;
    }

    const uploadDir = join(homedir(), "Desktop", "agent");
    await mkdir(uploadDir, { recursive: true });

    const paths: string[] = [];
    for (const file of files) {
      if (!file.name || !file.content) {
        continue;
      }
      const filePath = uniquePath(uploadDir, file.name);
      await writeFile(filePath, Buffer.from(file.content, "base64"));
      paths.push(filePath);
    }

    deps.logger.info(`pazi upload: wrote ${String(paths.length)} file(s) to ${uploadDir}`);
    writeJson(res, 200, { paths });
  };
}
