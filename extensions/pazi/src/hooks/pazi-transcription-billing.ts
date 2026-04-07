import { exec } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import https from "node:https";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";
import { registerInternalHook, isMessageTranscribedEvent } from "openclaw/plugin-sdk/hook-runtime";
import { getProxyContext } from "../context.js";

type ProxyLogger = {
  info: (message: string) => void;
  warn: (message: string) => void;
};

/**
 * Try to get audio duration using ffprobe.
 * Returns duration in seconds or null if ffprobe is unavailable or fails.
 */
function probeAudioDuration(mediaPath: string): Promise<number | null> {
  return new Promise((resolve) => {
    exec(
      `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${mediaPath}"`,
      { timeout: 5000 },
      (error, stdout) => {
        if (error) {
          resolve(null);
          return;
        }
        const duration = parseFloat(stdout.trim());
        if (Number.isFinite(duration) && duration > 0) {
          resolve(duration);
        } else {
          resolve(null);
        }
      },
    );
  });
}

/**
 * Estimate audio duration from file size.
 * Assumes typical voice codec bitrate (~3000 bytes/sec for Opus).
 */
function estimateDurationFromFileSize(fileSizeBytes: number): number {
  const estimatedSeconds = fileSizeBytes / 3000;
  return Math.min(Math.max(estimatedSeconds, 1), 60);
}

/**
 * Post transcription usage to the Pazi API for credit deduction.
 */
function postTranscriptionUsage(
  apiUrl: string,
  proxyToken: string,
  durationSeconds: number,
  logger: ProxyLogger,
): void {
  const body = JSON.stringify({ durationSeconds });
  const url = new URL("/transcribe/usage", apiUrl);
  const doRequest = url.protocol === "https:" ? https.request : http.request;

  const req = doRequest(
    url,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Proxy-Token": proxyToken,
      },
    },
    (res) => {
      // Consume response to prevent memory leak
      let responseBody = "";
      res.on("data", (chunk: Buffer | string) => {
        responseBody += String(chunk);
      });
      res.on("end", () => {
        if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
          logger.info(
            `pazi transcription billing: credits deducted (${String(durationSeconds)}s, status=${String(res.statusCode)})`,
          );
        } else {
          logger.warn(
            `pazi transcription billing: API returned status ${String(res.statusCode)}: ${responseBody}`,
          );
        }
      });
    },
  );

  req.on("error", (err: Error) => {
    logger.warn(`pazi transcription billing: request failed: ${err.message}`);
  });

  req.write(body);
  req.end();
}

/**
 * Register an internal hook handler for `message:transcribed` events.
 * When the core agent transcribes channel audio (Slack, Telegram, etc.),
 * this hook fires and reports usage to the Pazi API for credit deduction.
 *
 * This is best-effort: failures are logged but never block message processing.
 */
export function registerTranscriptionBillingHook(api: OpenClawPluginApi): void {
  const logger: ProxyLogger = {
    info: (msg) => api.logger.info(msg),
    warn: (msg) => api.logger.warn(msg),
  };

  registerInternalHook("message:transcribed", async (event) => {
    if (!isMessageTranscribedEvent(event)) {
      return;
    }

    const context = getProxyContext();
    if (!context?.proxyToken) {
      // Agent not connected to Pazi billing — skip silently
      return;
    }

    const apiUrl = process.env.PAZI_API_URL?.trim();
    if (!apiUrl) {
      return;
    }

    const mediaPath: string | undefined = (event.context as Record<string, unknown>).mediaPath as
      | string
      | undefined;

    let durationSeconds: number | null = null;

    // Try ffprobe first
    if (mediaPath && typeof mediaPath === "string") {
      durationSeconds = await probeAudioDuration(mediaPath);

      // Fall back to file size estimation
      if (durationSeconds === null) {
        try {
          const stats = fs.statSync(mediaPath);
          durationSeconds = estimateDurationFromFileSize(stats.size);
          logger.info(
            `pazi transcription billing: estimated duration from file size (${String(Math.round(durationSeconds))}s)`,
          );
        } catch {
          logger.warn(
            `pazi transcription billing: could not stat mediaPath "${mediaPath}", skipping`,
          );
          return;
        }
      }
    }

    if (durationSeconds === null || durationSeconds <= 0) {
      // No way to determine duration — skip billing
      logger.warn("pazi transcription billing: could not determine audio duration, skipping");
      return;
    }

    // Clamp to 60s max
    durationSeconds = Math.min(durationSeconds, 60);

    postTranscriptionUsage(apiUrl, context.proxyToken, durationSeconds, logger);
  });
}
