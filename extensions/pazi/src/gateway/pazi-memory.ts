import fs from "node:fs/promises";
import path from "node:path";
import { ErrorCodes, errorShape } from "../../../../src/gateway/protocol/index.js";
import type { GatewayRequestHandler } from "../../../../src/gateway/server-methods/types.js";

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

const ROOT_MEMORY_NAMES = new Set(["MEMORY.md", "memory.md"]);
const DATED_MEMORY_RE = /^memory\/\d{4}-\d{2}-\d{2}(?:-[^/]+)?\.md$/;

function classifyMemoryFile(name: string): MemoryFileKind {
  if (ROOT_MEMORY_NAMES.has(name)) return "root";
  if (DATED_MEMORY_RE.test(name)) return "daily";
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

  // Check root memory files
  for (const rootFile of ROOT_MEMORY_NAMES) {
    try {
      await fs.access(path.join(workspaceDir, rootFile));
      result.push(rootFile);
    } catch {
      // doesn't exist
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
        result.push(path.relative(workspaceDir, fullPath));
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
        const fullPath = path.join(workspaceDir, relPath);
        const [stat, content] = await Promise.all([
          fs.stat(fullPath),
          fs.readFile(fullPath, "utf-8"),
        ]);
        entries.push({
          name: relPath,
          path: fullPath,
          missing: false,
          size: stat.size,
          updatedAtMs: Math.floor(stat.mtimeMs),
          content,
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
