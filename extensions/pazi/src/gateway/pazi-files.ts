import fs from "node:fs/promises";
import path from "node:path";
import { ErrorCodes, errorShape } from "../../../../src/gateway/protocol/index.js";
import type { GatewayRequestHandler } from "../../../../src/gateway/server-methods/types.js";
import {
  readFileWithinRoot,
  writeFileWithinRoot,
  SafeOpenError,
} from "../../../../src/infra/fs-safe.js";

const SCAN_SKIP_DIRS = new Set([".git", "node_modules", ".DS_Store", "__pycache__", ".cache"]);
const SCAN_MAX_FILES = 10_000;
const SCAN_MAX_DEPTH = 10;

type ResolvedWorkspace = {
  agentId: string;
  workspaceDir: string;
};

type ResolveWorkspace = (agentId: unknown) => ResolvedWorkspace | null;

async function listFiles(workspaceDir: string) {
  const files: Array<{
    name: string;
    path: string;
    missing: boolean;
    size?: number;
    updatedAtMs?: number;
  }> = [];

  const resolvedWorkspace = path.resolve(workspaceDir);

  try {
    await fs.access(resolvedWorkspace);
  } catch {
    return files;
  }

  const queue: Array<{ dir: string; depth: number }> = [{ dir: resolvedWorkspace, depth: 0 }];

  while (queue.length > 0 && files.length < SCAN_MAX_FILES) {
    const current = queue.shift()!;
    if (current.depth > SCAN_MAX_DEPTH) {
      continue;
    }

    let dirEntries: string[];
    try {
      dirEntries = await fs.readdir(current.dir);
    } catch {
      continue;
    }

    for (const entryName of dirEntries) {
      if (files.length >= SCAN_MAX_FILES) {
        break;
      }
      if (SCAN_SKIP_DIRS.has(entryName)) {
        continue;
      }

      const fullPath = path.join(current.dir, entryName);

      let entryStat: Awaited<ReturnType<typeof fs.lstat>>;
      try {
        entryStat = await fs.lstat(fullPath);
      } catch {
        continue;
      }

      if (entryStat.isDirectory()) {
        queue.push({ dir: fullPath, depth: current.depth + 1 });
        continue;
      }

      if (!entryStat.isFile() || entryStat.isSymbolicLink()) {
        continue;
      }

      files.push({
        name: path.relative(resolvedWorkspace, fullPath),
        path: fullPath,
        missing: false,
        size: entryStat.size,
        updatedAtMs: Math.floor(entryStat.mtimeMs),
      });
    }
  }

  return files;
}

function resolveRequestWorkspace(
  params: unknown,
  resolveWorkspace: ResolveWorkspace,
): ResolvedWorkspace | null {
  const agentId =
    params && typeof params === "object" ? (params as { agentId?: unknown }).agentId : undefined;
  return resolveWorkspace(agentId);
}

export function createPaziFilesList(resolveWorkspace: ResolveWorkspace): GatewayRequestHandler {
  return async ({ params, respond }) => {
    const resolved = resolveRequestWorkspace(params, resolveWorkspace);
    if (!resolved) {
      respond(false, undefined, errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"));
      return;
    }
    const files = await listFiles(resolved.workspaceDir);
    respond(true, {
      agentId: resolved.agentId,
      workspace: resolved.workspaceDir,
      files,
    });
  };
}

export function createPaziFilesGet(resolveWorkspace: ResolveWorkspace): GatewayRequestHandler {
  return async ({ params, respond }) => {
    const resolved = resolveRequestWorkspace(params, resolveWorkspace);
    if (!resolved) {
      respond(false, undefined, errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"));
      return;
    }
    const { agentId, workspaceDir } = resolved;
    const name = typeof params.name === "string" ? params.name.trim() : "";
    if (!name || name.includes("\0")) {
      respond(
        false,
        undefined,
        errorShape(ErrorCodes.INVALID_REQUEST, `invalid file name "${name}"`),
      );
      return;
    }

    try {
      const result = await readFileWithinRoot({
        rootDir: workspaceDir,
        relativePath: name,
      });
      const filePath = path.join(workspaceDir, name);
      respond(true, {
        agentId,
        workspace: workspaceDir,
        file: {
          name,
          path: filePath,
          missing: false,
          size: result.stat.size,
          updatedAtMs: Math.floor(result.stat.mtimeMs),
          content: result.buffer.toString("utf-8"),
        },
      });
    } catch (err) {
      if (err instanceof SafeOpenError) {
        if (err.code === "not-found") {
          respond(true, {
            agentId,
            workspace: workspaceDir,
            file: { name, path: path.join(workspaceDir, name), missing: true },
          });
          return;
        }
        respond(
          false,
          undefined,
          errorShape(ErrorCodes.INVALID_REQUEST, `invalid file: ${err.message}`),
        );
        return;
      }
      respond(false, undefined, errorShape(ErrorCodes.UNAVAILABLE, "read_failed"));
    }
  };
}

export function createPaziFilesSet(resolveWorkspace: ResolveWorkspace): GatewayRequestHandler {
  return async ({ params, respond }) => {
    const resolved = resolveRequestWorkspace(params, resolveWorkspace);
    if (!resolved) {
      respond(false, undefined, errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"));
      return;
    }
    const { agentId, workspaceDir } = resolved;
    const name = typeof params.name === "string" ? params.name.trim() : "";
    if (!name || name.includes("\0")) {
      respond(
        false,
        undefined,
        errorShape(ErrorCodes.INVALID_REQUEST, `invalid file name "${name}"`),
      );
      return;
    }

    const content = String(params.content ?? "");

    try {
      await writeFileWithinRoot({
        rootDir: workspaceDir,
        relativePath: name,
        data: content,
        encoding: "utf8",
        mkdir: true,
      });
    } catch {
      respond(
        false,
        undefined,
        errorShape(ErrorCodes.INVALID_REQUEST, `unsafe workspace file "${name}"`),
      );
      return;
    }

    const filePath = path.join(workspaceDir, name);
    let size: number | undefined;
    let updatedAtMs: number | undefined;
    try {
      const stat = await fs.stat(filePath);
      size = stat.size;
      updatedAtMs = Math.floor(stat.mtimeMs);
    } catch {
      // best effort
    }

    respond(true, {
      ok: true,
      agentId,
      workspace: workspaceDir,
      file: { name, path: filePath, missing: false, size, updatedAtMs, content },
    });
  };
}
