import path from "node:path";
import { listAgentIds, resolveAgentWorkspaceDir } from "../agents/agent-scope.js";
import type { OpenClawConfig } from "../config/config.js";
import { resolveStateDir } from "../config/paths.js";
import { resolvePreferredOpenClawTmpDir } from "../infra/tmp-openclaw-dir.js";

type BuildMediaLocalRootsOptions = {
  preferredTmpDir?: string;
};

let cachedPreferredTmpDir: string | undefined;

function resolveCachedPreferredTmpDir(): string {
  if (!cachedPreferredTmpDir) {
    cachedPreferredTmpDir = resolvePreferredOpenClawTmpDir();
  }
  return cachedPreferredTmpDir;
}

function buildMediaLocalRoots(
  stateDir: string,
  options: BuildMediaLocalRootsOptions = {},
): string[] {
  const resolvedStateDir = path.resolve(stateDir);
  const preferredTmpDir = options.preferredTmpDir ?? resolveCachedPreferredTmpDir();
  return [
    preferredTmpDir,
    path.join(resolvedStateDir, "media"),
    path.join(resolvedStateDir, "workspace"),
    path.join(resolvedStateDir, "sandboxes"),
  ];
}

export function getDefaultMediaLocalRoots(): readonly string[] {
  return buildMediaLocalRoots(resolveStateDir());
}

export function getAgentScopedMediaLocalRoots(
  cfg: OpenClawConfig,
  _agentId?: string,
): readonly string[] {
  const roots = buildMediaLocalRoots(resolveStateDir());
  const seen = new Set(roots.map((r) => path.resolve(r)));

  // Include workspace directories for ALL configured agents so that
  // cross-agent media sharing works (e.g. Agent A generates a file that
  // Agent B needs to deliver).
  for (const id of listAgentIds(cfg)) {
    const dir = resolveAgentWorkspaceDir(cfg, id);
    if (!dir) {
      continue;
    }
    const normalized = path.resolve(dir);
    if (!seen.has(normalized)) {
      seen.add(normalized);
      roots.push(normalized);
    }
  }

  return roots;
}
