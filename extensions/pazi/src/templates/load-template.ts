import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Descriptor for a single template file — the relative path within the
 * template directory and the file content read from disk.
 */
export interface TemplateFile {
  /** Relative path within the template dir, e.g. "IDENTITY.md" or "skills/cicd-pipeline/SKILL.md" */
  relativePath: string;
  content: string;
}

/**
 * Manifest stored in each template's `template.json`.
 */
export interface TemplateManifest {
  id: string;
  name: string;
  description: string;
  /** Top-level agent files to copy (e.g. IDENTITY.md, SOUL.md). */
  files: string[];
  /** Skill files relative to the template dir (e.g. "skills/cicd-pipeline/SKILL.md"). */
  skills: string[];
}

export interface LoadedTemplate {
  manifest: TemplateManifest;
  files: TemplateFile[];
  errors: string[];
}

const TEMPLATES_ROOT = new URL("../../templates/agent-templates", import.meta.url);

/**
 * List all available template IDs by scanning subdirectories of the
 * templates root that contain a `template.json`.
 */
export async function listTemplateIds(): Promise<string[]> {
  const rootDir = fileURLToPath(TEMPLATES_ROOT);
  let entries: string[];
  try {
    entries = await fs.readdir(rootDir);
  } catch {
    return [];
  }

  const ids: string[] = [];
  for (const entry of entries) {
    try {
      await fs.access(path.join(rootDir, entry, "template.json"));
      ids.push(entry);
    } catch {
      // not a valid template directory
    }
  }
  return ids;
}

/**
 * Load a template's manifest and all referenced files from disk.
 *
 * Returns `null` if the template does not exist or its manifest is invalid.
 */
export async function loadTemplate(templateId: string): Promise<LoadedTemplate | null> {
  // Prevent path traversal
  if (!/^[a-zA-Z0-9_-]+$/.test(templateId)) {
    return null;
  }

  const templateDir = path.join(fileURLToPath(TEMPLATES_ROOT), templateId);
  const manifestPath = path.join(templateDir, "template.json");

  let rawManifest: string;
  try {
    rawManifest = await fs.readFile(manifestPath, "utf-8");
  } catch {
    return null;
  }

  let manifest: TemplateManifest;
  try {
    manifest = JSON.parse(rawManifest) as TemplateManifest;
  } catch {
    return null;
  }

  if (
    typeof manifest.id !== "string" ||
    manifest.id.trim() === "" ||
    manifest.id !== templateId ||
    typeof manifest.name !== "string" ||
    typeof manifest.description !== "string" ||
    !Array.isArray(manifest.files) ||
    !Array.isArray(manifest.skills) ||
    !manifest.files.every((entry) => typeof entry === "string" && entry.trim() !== "") ||
    !manifest.skills.every((entry) => typeof entry === "string" && entry.trim() !== "")
  ) {
    return null;
  }

  // Read all referenced files
  const allRelativePaths = [...manifest.files, ...manifest.skills].map((entry) => entry.trim());
  const files: TemplateFile[] = [];
  const errors: string[] = [];
  const resolvedTemplateDir = path.resolve(templateDir);

  for (const relPath of allRelativePaths) {
    const resolvedPath = path.resolve(templateDir, relPath);
    // Safety check: resolved path must be under templateDir
    if (
      !resolvedPath.startsWith(resolvedTemplateDir + path.sep) &&
      resolvedPath !== resolvedTemplateDir
    ) {
      errors.push(`${relPath}: path traversal rejected`);
      continue;
    }
    try {
      const content = await fs.readFile(resolvedPath, "utf-8");
      files.push({ relativePath: relPath, content });
    } catch (err) {
      errors.push(
        `${relPath}: ${err instanceof Error ? err.message : "failed to read template file"}`,
      );
    }
  }

  return { manifest, files, errors };
}
