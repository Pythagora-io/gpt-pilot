import fs from "node:fs/promises";
import path from "node:path";
import { ErrorCodes, errorShape } from "../../../../src/gateway/protocol/index.js";
import type { GatewayRequestHandler } from "../../../../src/gateway/server-methods/types.js";
import { readFileWithinRoot } from "../../../../src/infra/fs-safe.js";

// --- Types ---

type ResolvedWorkspace = {
  agentId: string;
  workspaceDir: string;
};

type ResolveWorkspace = (agentId: unknown) => ResolvedWorkspace | null;

type MemoryFileKind = "root" | "daily" | "note";

interface MemoryEntry {
  name: string;
  path: string;
  missing: false;
  size: number;
  updatedAtMs: number;
  content: string;
  kind: MemoryFileKind;
}

// --- Memory file detection ---

const ROOT_MEMORY_FILES = ["MEMORY.md", "memory.md"] as const;
const ROOT_MEMORY_NAMES = new Set<string>(ROOT_MEMORY_FILES);
const DATED_MEMORY_RE = /^memory\/\d{4}-\d{2}-\d{2}(?:-[^/]+)?\.md$/;

function normalizeMemoryPath(name: string): string {
  return name.replaceAll("\\", "/");
}

function classifyMemoryFile(name: string): MemoryFileKind {
  const normalizedName = normalizeMemoryPath(name);
  if (ROOT_MEMORY_NAMES.has(normalizedName)) return "root";
  if (DATED_MEMORY_RE.test(normalizedName)) return "daily";
  return "note";
}

// --- Sorting ---
// Order: MEMORY.md → memory.md → daily logs (newest first) → notes (alphabetical)

function sortMemoryEntries(entries: MemoryEntry[]): MemoryEntry[] {
  return [...entries].sort((a, b) => {
    const aRoot = rootRank(a.name);
    const bRoot = rootRank(b.name);
    if (aRoot !== bRoot) return aRoot - bRoot;

    // Both are non-root: daily before notes
    if (a.kind === "daily" && b.kind === "daily") {
      return b.name.localeCompare(a.name); // newest first
    }
    if (a.kind === "daily") return -1;
    if (b.kind === "daily") return 1;

    return a.name.localeCompare(b.name); // notes alphabetical
  });
}

function rootRank(name: string): number {
  if (name === "MEMORY.md") return 0;
  if (name === "memory.md") return 1;
  return 2;
}

// --- Directory scanning ---

async function discoverMemoryFiles(
  workspaceDir: string,
  maxFiles: number = 500,
  maxDepth: number = 5,
): Promise<string[]> {
  const result: string[] = [];

  // Check root memory files by directory entries to avoid alias duplicates
  // on case-insensitive filesystems (for example MEMORY.md vs memory.md).
  let rootEntries: string[] = [];
  try {
    rootEntries = await fs.readdir(workspaceDir);
  } catch {
    // workspace may not exist yet
  }
  const rootEntrySet = new Set(rootEntries);
  for (const rootFile of ROOT_MEMORY_FILES) {
    if (rootEntrySet.has(rootFile)) {
      result.push(rootFile);
    }
  }

  // Scan memory/ directory recursively
  const memoryDir = path.join(workspaceDir, "memory");

  async function walk(dir: string, depth: number): Promise<void> {
    if (depth > maxDepth || result.length >= maxFiles) return;
    let entries;
    try {
      entries = await fs.readdir(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      if (result.length >= maxFiles) break;
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        await walk(fullPath, depth + 1);
      } else if (entry.isFile() && entry.name.endsWith(".md")) {
        result.push(normalizeMemoryPath(path.relative(workspaceDir, fullPath)));
      }
    }
  }

  await walk(memoryDir, 0);
  return result;
}

// --- Handler ---

export function createPaziMemoryGet(resolveWorkspace: ResolveWorkspace): GatewayRequestHandler {
  return async ({ params, respond }) => {
    const agentId =
      params && typeof params === "object" ? (params as { agentId?: unknown }).agentId : undefined;
    const resolved = resolveWorkspace(agentId);
    if (!resolved) {
      respond(false, undefined, errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"));
      return;
    }

    const { workspaceDir } = resolved;
    const filePaths = await discoverMemoryFiles(workspaceDir);
    const entries: MemoryEntry[] = [];

    for (const relPath of filePaths) {
      try {
        const result = await readFileWithinRoot({
          rootDir: workspaceDir,
          relativePath: relPath,
        });
        const fullPath = path.join(workspaceDir, relPath);
        entries.push({
          name: relPath,
          path: fullPath,
          missing: false,
          size: result.stat.size,
          updatedAtMs: Math.floor(result.stat.mtimeMs),
          content: result.buffer.toString("utf-8"),
          kind: classifyMemoryFile(relPath),
        });
      } catch {
        // Skip unreadable files
        continue;
      }
    }

    respond(true, {
      agentId: resolved.agentId,
      workspace: workspaceDir,
      files: sortMemoryEntries(entries),
    });
  };
}
