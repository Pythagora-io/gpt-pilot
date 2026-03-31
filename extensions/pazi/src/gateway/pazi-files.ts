import fs from "node:fs/promises";
import path from "node:path";
import {
  ErrorCodes,
  errorShape,
  type GatewayRequestHandler,
} from "openclaw/plugin-sdk/gateway-runtime";
import {
  readFileWithinRoot,
  writeFileWithinRoot,
  SafeOpenError,
} from "openclaw/plugin-sdk/infra-runtime";

function isLikelyBinary(buffer: Buffer): boolean {
  const sampleLen = Math.min(buffer.length, 4096);
  for (let i = 0; i < sampleLen; i++) {
    if (buffer[i] === 0) return true;
  }
  return false;
}

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
      const binary = isLikelyBinary(result.buffer);
      respond(true, {
        agentId,
        workspace: workspaceDir,
        file: {
          name,
          path: filePath,
          missing: false,
          size: result.stat.size,
          updatedAtMs: Math.floor(result.stat.mtimeMs),
          content: binary ? result.buffer.toString("base64") : result.buffer.toString("utf-8"),
          encoding: binary ? "base64" : "utf8",
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

export function createPaziFilesDelete(resolveWorkspace: ResolveWorkspace): GatewayRequestHandler {
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

    // Validate the resolved path stays within the workspace root
    const resolvedRoot = path.resolve(workspaceDir);
    const filePath = path.resolve(workspaceDir, name);
    if (!filePath.startsWith(resolvedRoot + path.sep) || filePath === resolvedRoot) {
      respond(false, undefined, errorShape(ErrorCodes.INVALID_REQUEST, `invalid file: "${name}"`));
      return;
    }

    // Verify it's a file (not a directory or symlink)
    try {
      const stat = await fs.lstat(filePath);
      if (!stat.isFile()) {
        respond(false, undefined, errorShape(ErrorCodes.INVALID_REQUEST, `not a file: "${name}"`));
        return;
      }
    } catch {
      respond(
        false,
        undefined,
        errorShape(ErrorCodes.INVALID_REQUEST, `file not found: "${name}"`),
      );
      return;
    }

    try {
      await fs.unlink(filePath);
    } catch (err: unknown) {
      // ENOENT between stat and unlink — treat as success (idempotent)
      if (err instanceof Error && "code" in err && err.code === "ENOENT") {
        respond(true, { ok: true, agentId, workspace: workspaceDir });
        return;
      }
      respond(false, undefined, errorShape(ErrorCodes.UNAVAILABLE, "delete_failed"));
      return;
    }

    respond(true, {
      ok: true,
      agentId,
      workspace: workspaceDir,
    });
  };
}
