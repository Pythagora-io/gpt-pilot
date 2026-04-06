import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";

const WEBCHAT_FILE_GUIDANCE = `## Webchat File Support
The webchat dashboard fully supports file downloads and previews. When a user asks you to create, export, or generate a file:

### How it works
1. Use the \`write\` tool to create the file in the workspace.
2. The dashboard automatically detects each Write tool call and renders a file card with download and preview buttons.
3. Each \`write\` call produces one file card. To deliver multiple files, call \`write\` once per file.

### File naming
- Use descriptive file names with proper extensions (e.g. \`quarterly-report.csv\`, \`dashboard.html\`, not \`output.txt\`).
- Place files in the workspace root or a clearly named subdirectory.

### Supported types
- **Text:** HTML, JSON, CSV, TXT, Markdown, XML, YAML, TOML
- **Code:** JS, TS, Python, Go, Rust, Java, C/C++, Shell, SQL, and more
- **Documents:** PDF
- **Images:** PNG, JPG, GIF, SVG, WebP
- **Archives:** ZIP, TAR, GZ
- **Audio/Video:** MP3, WAV, MP4, WebM
- Download works for all types. Inline preview works for text, HTML, images, and PDF.
- For binary files (images, archives, audio/video), download always works; preview availability varies by type.

### After writing a file
- Tell the user the file is ready and they can download or preview it using the card that appeared in the chat.
- Do NOT paste raw file paths or instruct the user to run terminal commands to retrieve the file.
- Do NOT dump file contents into the chat when the user asked for a file — write it instead.

### Prohibitions
- Do NOT tell the user that webchat doesn't support file downloads — it does.
- Do NOT use the \`message\` tool with \`media\` or \`buffer\` params to deliver files — use the \`write\` tool.`;

/**
 * Injects file download/preview guidance into the system prompt for webchat sessions.
 *
 * Without this, the agent's system prompt shows `capabilities=none` for webchat
 * and the agent refuses to create files, telling users that webchat doesn't support
 * file downloads.
 */
export function registerWebchatFileSupportHook(api: OpenClawPluginApi): void {
  api.on(
    "before_prompt_build",
    (_event, ctx) => {
      const channel = (ctx.channelId ?? ctx.messageProvider ?? "").toLowerCase();
      if (channel !== "webchat") {
        return;
      }

      return {
        appendSystemContext: WEBCHAT_FILE_GUIDANCE,
      };
    },
    { priority: 10 },
  );
}
